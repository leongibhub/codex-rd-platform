"""Durable host handoffs with expiring, hashed leases."""
from datetime import datetime, timedelta
import hashlib
import secrets

from .store import Store


class WorkCommands:
    def unsafe_attempt_fenced(self, c, project_id, work_id):
        """Read the immutable event stream inside the claim transaction."""
        fenced = False
        for event in c.execute('SELECT type,data FROM lc_events WHERE project_id=? AND entity_id=? ORDER BY sequence', (project_id, work_id)):
            if event['type'] in {'work.invalidated', 'work.lease_expired'}:
                if Store.loads(event['data']).get('external_process_cancelled') is not True:
                    fenced = True
            elif event['type'] == 'work.claimed':
                fenced = False
        return fenced

    def work_create(self,c,d,*,internal_repair=False):
        p=self.project(c,d.get('project_id'))['id']
        repair_fields={'repair_defect_id','repair_stage','fix_defect_id','source_execution'}
        if repair_fields.intersection(d) and not internal_repair:
            raise ValueError('repair metadata is internal only')
        if internal_repair:
            self.validate_repair_work(c,p,d)
        # A bootstrap project is a policy domain, not a worker-service
        # convention.  Persist the marker on every work order so a raw CLI
        # work.create cannot create an ungoverned side path.
        from .orchestration_policy import apply_create_policy
        strict_policy=apply_create_policy(self,c,p,d)
        gate=self.get(c,'gates',p+':'+self.text(d.get('gate_id'),'gate_id'))
        role=self.enum(d.get('required_role'),{'developer','tester','reviewer','requirement_analyst','product_manager','architect','researcher','release_manager','documentation_manager'},'required role')
        refs=self.refs(c,p,d.get('input_refs'),nonempty=False)
        deps=self.strings(d.get('dependencies'),'dependencies',False)
        for dep in deps:
            if self.get(c,'work_orders',dep)['project_id']!=p: raise ValueError('dependency belongs to another project')
        contract=d.get('output_contract')
        if not isinstance(contract,dict) or set(contract)-{'required_types','min_outputs'}: raise ValueError('output_contract supports required_types and min_outputs')
        required=self.strings(contract.get('required_types',[]),'required_types',False)
        from .lifecycle_base import ARTIFACT_TYPES
        for kind in required: self.enum(kind,ARTIFACT_TYPES|{'TEST_CASE','TEST_EXECUTION','BUG','REL','EVIDENCE'},'output type')
        minimum=self.integer(contract.get('min_outputs',1),'min_outputs',0,1000)
        row=dict(id=self.ident('work'),project_id=p,gate_id=gate['gate_id'],activity=self.text(d.get('activity'),'activity'),required_role=role,why=self.text(d.get('why'),'why'),input_refs=refs,output_contract={'required_types':required,'min_outputs':minimum},dependencies=deps,status='READY',attempt=0,version=1,agent_id=None,lease_digest=None,lease_until=None,heartbeat_at=None,created_at=self.now())
        if strict_policy:
            row['strict_policy']=strict_policy
        # Repair identifiers are host control metadata.  They are deliberately
        # copied into the durable work record rather than inferred from prose.
        for field in ('repair_defect_id','repair_stage','fix_defect_id','source_execution'):
            if field in d:
                row[field]=self.text(d[field],field)
        self.put(c,'work_orders',row,new=True); self.event(c,p,'work.created',row['id'],{'role':role,'why':row['why']})
        return self.public_work(row)

    def work_create_repair(self,c,d):
        """Internal-only canonical repair creation; not a Runtime command."""
        return self.work_create(c,d,internal_repair=True)

    def validate_repair_work(self,c,p,d,*,existing_work_id=None):
        """Reject forged repair-stage metadata before it can affect admission."""
        defect=self.get(c,'defects',d.get('repair_defect_id'))
        source=self.get(c,'test_executions',d.get('source_execution'))
        if defect['project_id']!=p or source['project_id']!=p or defect.get('source_execution')!=source['id'] or source.get('result')!='FAIL':
            raise ValueError('canonical repair source failure required')
        stage=self.enum(d.get('repair_stage'),{'triage','fix','retest','review'},'repair stage')
        expected={
            'triage':('G7','tester','EVIDENCE'),
            # Defect ownership can be developer, tester, architect or
            # requirement analyst.  The common immutable completion proof is
            # the exact evidence recorded by defect.fix, not a CODE_CHANGE.
            'fix':('G7',defect.get('owner_role'),'EVIDENCE'),
            'retest':('G7','tester','TEST_EXECUTION'),
            'review':('G7','reviewer','EVIDENCE'),
        }[stage]
        if d.get('gate_id')!=expected[0] or d.get('required_role')!=expected[1]:
            raise ValueError('repair stage gate or role is not canonical')
        contract=d.get('output_contract',{})
        if contract.get('required_types')!=[expected[2]] or contract.get('min_outputs')!=1:
            raise ValueError('repair stage output contract is not canonical')
        existing=[w for w in self.rows(c,'work_orders',p) if w.get('repair_defect_id')==defect['id']]
        by_stage={w.get('repair_stage'):w for w in existing}
        if existing_work_id is not None:
            if by_stage.get(stage,{}).get('id')!=existing_work_id or sum(w.get('repair_stage')==stage for w in existing)!=1:
                raise ValueError('repair work identity is not canonical')
        dependencies=d.get('dependencies')
        if stage=='triage':
            others=[w for w in existing if w['id']!=existing_work_id]
            if others or dependencies!=[]: raise ValueError('canonical triage must be first repair work')
        elif stage=='fix':
            if (existing_work_id is None and stage in by_stage) or dependencies!=[]: raise ValueError('canonical fix dependencies invalid')
        elif stage=='retest':
            if 'fix' not in by_stage or (existing_work_id is None and stage in by_stage) or dependencies!=[by_stage['fix']['id']]: raise ValueError('canonical retest dependency invalid')
        else:
            if 'retest' not in by_stage or (existing_work_id is None and stage in by_stage) or dependencies!=[by_stage['retest']['id']]: raise ValueError('canonical review dependency invalid')

    @staticmethod
    def public_work(row): return {k:v for k,v in row.items() if k!='lease_digest'}

    def work_reap(self,c,d):
        p=self.project(c,d.get('project_id'))['id']; expired=[]
        now=self.now()
        for w in self.rows(c,'work_orders',p):
            if w['status']=='CLAIMED' and w['lease_until']<=now:
                w.update(status='READY',agent_id=None,lease_digest=None,lease_until=None,version=w['version']+1)
                self.put(c,'work_orders',w); expired.append(w['id']); self.event(c,p,'work.lease_expired',w['id'],{'external_process_cancelled':False})
        return {'expired':expired}

    def work_claim(self,c,d):
        w=self.get(c,'work_orders',d.get('work_order_id')); p=self.project(c,w['project_id'])
        if p['state'] in {'PAUSED','CLOSED','FAILED'}: raise ValueError('lifecycle does not permit work claims')
        self.work_reap(c,{'project_id':p['id']}); w=self.get(c,'work_orders',w['id'])
        if 'expected_version' in d and self.integer(d['expected_version'], 'expected_version') != w['version']:
            raise ValueError('work version changed')
        safe_to_retry=d.get('safe_to_retry',False)
        if type(safe_to_retry) is not bool: raise ValueError('safe_to_retry must be boolean')
        if self.unsafe_attempt_fenced(c,p['id'],w['id']) and not safe_to_retry:
            raise ValueError('unknown external outcome requires explicit safe_to_retry')
        agent=self.agent(c,d.get('agent_id'),{w['required_role']})
        seconds=self.integer(d.get('lease_seconds',300),'lease_seconds',1,3600)
        if w['status']!='READY': raise ValueError('work is not ready')
        if w.get('assigned_agent_id') and w['assigned_agent_id']!=agent['id']: raise ValueError('work assigned to another agent')
        if c.execute("SELECT 1 FROM lc_work_orders WHERE status='CLAIMED' AND json_extract(data,'$.agent_id')=?",(agent['id'],)).fetchone(): raise ValueError('agent already has an active lease')
        for dep in w['dependencies']:
            if self.get(c,'work_orders',dep)['status']!='DONE': raise ValueError('dependency not done')
        self.refs(c,p['id'],w['input_refs'],nonempty=False)
        from .orchestration_policy import validate_claim
        adopted_dependencies=validate_claim(self,c,w)
        if adopted_dependencies:
            w['dependency_input_refs']=adopted_dependencies
        token=secrets.token_urlsafe(32)
        now=self.now()
        w.update(status='CLAIMED',attempt=w['attempt']+1,agent_id=agent['id'],lease_digest=hashlib.sha256(token.encode()).hexdigest(),lease_seconds=seconds,lease_until=(datetime.fromisoformat(now)+timedelta(seconds=seconds)).isoformat(),heartbeat_at=now)
        self.put(c,'work_orders',w); self.event(c,p['id'],'work.claimed',w['id'],{'agent_id':agent['id'],'attempt':w['attempt'],'version':w['version']})
        return dict(self.public_work(w),lease_token=token)

    def lease(self,c,d):
        w=self.get(c,'work_orders',d.get('work_order_id'))
        token=self.text(d.get('lease_token'),'lease_token')
        if w['status']!='CLAIMED' or w['agent_id']!=d.get('agent_id') or w['lease_until']<=self.now() or not secrets.compare_digest(w['lease_digest'] or '',hashlib.sha256(token.encode()).hexdigest()): raise ValueError('stale or invalid work lease')
        if self.project(c,w['project_id'])['state']=='PAUSED': raise ValueError('lifecycle is paused')
        self.refs(c,w['project_id'],w['input_refs'],nonempty=False)
        from .orchestration_policy import validate_claim
        adopted_dependencies=validate_claim(self,c,w)
        if adopted_dependencies and w.get('dependency_input_refs')!=adopted_dependencies:
            raise ValueError('strict dependency adoption changed')
        return w

    def recover_claim(self,c,d,cached):
        """Recover a lost handoff response by rotating, never storing, its secret."""
        w=self.get(c,'work_orders',d.get('work_order_id'))
        self.agent(c,d.get('agent_id'),{w['required_role']})
        if w['version']!=cached['version'] or w['attempt']!=cached['attempt'] or w['agent_id']!=d['agent_id']:
            raise ValueError('claim request is no longer current')
        if w['status']!='CLAIMED': return self.public_work(w)
        if self.project(c,w['project_id'])['state'] in {'PAUSED','CLOSED','FAILED'}: raise ValueError('lifecycle cannot recover claim')
        self.refs(c,w['project_id'],w['input_refs'],nonempty=False)
        for dependency in w['dependencies']:
            if self.get(c,'work_orders',dependency)['status']!='DONE': raise ValueError('claim dependency no longer done')
        from .orchestration_policy import validate_claim
        adopted_dependencies=validate_claim(self,c,w)
        if adopted_dependencies and w.get('dependency_input_refs')!=adopted_dependencies:
            raise ValueError('strict dependency adoption changed')
        token=secrets.token_urlsafe(32); now=self.now()
        w.update(lease_digest=hashlib.sha256(token.encode()).hexdigest(),lease_until=(datetime.fromisoformat(now)+timedelta(seconds=w['lease_seconds'])).isoformat(),heartbeat_at=now,lease_generation=w.get('lease_generation',0)+1)
        self.put(c,'work_orders',w)
        self.event(c,w['project_id'],'work.lease_reissued',w['id'],{'agent_id':w['agent_id'],'attempt':w['attempt'],'generation':w['lease_generation']})
        return dict(self.public_work(w),lease_token=token)

    def work_heartbeat(self,c,d):
        w=self.lease(c,d); now=self.now()
        w.update(heartbeat_at=now,lease_until=(datetime.fromisoformat(now)+timedelta(seconds=w['lease_seconds'])).isoformat())
        self.put(c,'work_orders',w); self.event(c,w['project_id'],'work.heartbeat',w['id'],{'agent_id':w['agent_id']})
        return self.public_work(w)

    def work_finish(self,c,d):
        w=self.lease(c,d)
        status=self.enum(d.get('status'),{'DONE','FAILED','WAITING_USER','BLOCKED'},'work status')
        outputs=self.refs(c,w['project_id'],d.get('output_refs'),nonempty=False)
        summary=self.text(d.get('summary'),'summary')
        if status=='DONE':
            if len(outputs)<w['output_contract']['min_outputs'] or set(w['output_contract']['required_types'])-{r['type'] for r in outputs}: raise ValueError('output contract not satisfied')
            for ref in outputs:
                if ref['type']=='EVIDENCE': self.evidence_refs(c,w['project_id'],[ref])
            for dep in w['dependencies']:
                if self.get(c,'work_orders',dep)['status']!='DONE': raise ValueError('dependency no longer done')
            from .orchestration_policy import validate_finish
            validate_finish(self,c,w,status,outputs)
        w.update(status=status,output_refs=outputs,summary=summary,finished_at=self.now(),lease_digest=None,lease_until=None)
        self.put(c,'work_orders',w); self.event(c,w['project_id'],'work.finished',w['id'],{'status':status,'agent_id':w['agent_id'],'summary':summary})
        if status=='WAITING_USER':
            p=self.project(c,w['project_id']); p['state']='WAITING_USER'; self.put(c,'projects',p)
        return self.public_work(w)

    def work_control(self,c,d):
        w=self.get(c,'work_orders',d.get('work_order_id'))
        action=self.enum(d.get('action'),{'retry','reject','modify','reassign','skip','rollback'},'work action')
        reason=self.text(d.get('reason'),'reason')
        if action=='rollback' and (w['status']=='CLAIMED' or self.unsafe_attempt_fenced(c,w['project_id'],w['id'])):
            raise ValueError('reconcile original external outcome before compensation')
        if w['status']=='CLAIMED':
            self.event(c,w['project_id'],'work.invalidated',w['id'],{'reason':reason,'action':action,'external_process_cancelled':False})
        if w.get('repair_stage')=='triage':
            bug=self.get(c,'defects',w.get('repair_defect_id'))
            if bug.get('category')!='UNCLASSIFIED' and action not in {'reject','skip'}:
                # A classification has superseded this triage lease.  Do not
                # let another generic control turn it back into READY or make
                # a compensation side path; the bounded repair chain owns the
                # next executable handoffs.
                raise ValueError('classified defect triage is superseded and cannot be made executable')
        if action=='retry':
            if w['status'] not in {'FAILED','BLOCKED','WAITING_USER','REVIEW_REQUIRED'} or w['attempt']>=3: raise ValueError('work cannot retry')
            self.refs(c,w['project_id'],w['input_refs'],nonempty=False); w['status']='READY'
        elif action in {'reject','skip'}: w['status']='REJECTED' if action=='reject' else 'SKIPPED'
        elif action=='reassign':
            agent=self.agent(c,d.get('agent_id'),{w['required_role']})
            w.update(status='READY',assigned_agent_id=agent['id'])
        elif action=='modify':
            w['input_refs']=self.refs(c,w['project_id'],d.get('input_refs'),nonempty=False); w['status']='READY'
        else:
            from .orchestration_policy import recovery_dependencies
            compensation=self.work_create(c,dict(project_id=w['project_id'],gate_id=w['gate_id'],activity='rollback '+w['activity'],required_role=w['required_role'],why=reason,input_refs=w['input_refs'],output_contract=w['output_contract'],dependencies=recovery_dependencies(self,c,w['project_id'],w['gate_id'])))
            w['compensation_work_id']=compensation['id']; w['status']='ROLLBACK_PENDING'
        w.update(version=w['version']+1,lease_digest=None,lease_until=None,agent_id=None)
        self.put(c,'work_orders',w)
        affected={w['id']}; changed=True
        while changed:
            changed=False
            for child in self.rows(c,'work_orders',w['project_id']):
                if child['id'] not in affected and affected.intersection(child['dependencies']):
                    affected.add(child['id']); changed=True
                    if child['status']=='CLAIMED':
                        self.event(c,w['project_id'],'work.invalidated',child['id'],{'reason':reason,'action':action,'external_process_cancelled':False})
                    child.update(status='REVIEW_REQUIRED',version=child['version']+1,lease_digest=None,lease_until=None,agent_id=None); self.put(c,'work_orders',child)
        self.event(c,w['project_id'],'work.'+action,w['id'],{'reason':reason,'affected':sorted(affected),'external_process_cancelled':False})
        return self.public_work(w)
