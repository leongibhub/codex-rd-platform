"""Durable host handoffs with expiring, hashed leases."""
from datetime import datetime, timedelta
import hashlib
import secrets


class WorkCommands:
    def work_create(self,c,d):
        p=self.project(c,d.get('project_id'))['id']
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
        self.put(c,'work_orders',row,new=True); self.event(c,p,'work.created',row['id'],{'role':role,'why':row['why']})
        return self.public_work(row)

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
        agent=self.agent(c,d.get('agent_id'),{w['required_role']})
        seconds=self.integer(d.get('lease_seconds',300),'lease_seconds',1,3600)
        if w['status']!='READY': raise ValueError('work is not ready')
        if w.get('assigned_agent_id') and w['assigned_agent_id']!=agent['id']: raise ValueError('work assigned to another agent')
        if c.execute("SELECT 1 FROM lc_work_orders WHERE status='CLAIMED' AND json_extract(data,'$.agent_id')=?",(agent['id'],)).fetchone(): raise ValueError('agent already has an active lease')
        for dep in w['dependencies']:
            if self.get(c,'work_orders',dep)['status']!='DONE': raise ValueError('dependency not done')
        self.refs(c,p['id'],w['input_refs'],nonempty=False)
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
        w.update(status=status,output_refs=outputs,summary=summary,finished_at=self.now(),lease_digest=None,lease_until=None)
        self.put(c,'work_orders',w); self.event(c,w['project_id'],'work.finished',w['id'],{'status':status,'agent_id':w['agent_id'],'summary':summary})
        if status=='WAITING_USER':
            p=self.project(c,w['project_id']); p['state']='WAITING_USER'; self.put(c,'projects',p)
        return self.public_work(w)

    def work_control(self,c,d):
        w=self.get(c,'work_orders',d.get('work_order_id'))
        action=self.enum(d.get('action'),{'retry','reject','modify','reassign','skip','rollback'},'work action')
        reason=self.text(d.get('reason'),'reason')
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
            compensation=self.work_create(c,dict(project_id=w['project_id'],gate_id=w['gate_id'],activity='rollback '+w['activity'],required_role=w['required_role'],why=reason,input_refs=w['input_refs'],output_contract=w['output_contract'],dependencies=[]))
            w['compensation_work_id']=compensation['id']; w['status']='ROLLBACK_PENDING'
        w.update(version=w['version']+1,lease_digest=None,lease_until=None,agent_id=None)
        self.put(c,'work_orders',w)
        affected={w['id']}; changed=True
        while changed:
            changed=False
            for child in self.rows(c,'work_orders',w['project_id']):
                if child['id'] not in affected and affected.intersection(child['dependencies']):
                    affected.add(child['id']); changed=True
                    child.update(status='REVIEW_REQUIRED',version=child['version']+1,lease_digest=None,lease_until=None,agent_id=None); self.put(c,'work_orders',child)
        self.event(c,w['project_id'],'work.'+action,w['id'],{'reason':reason,'affected':sorted(affected),'external_process_cancelled':False})
        return self.public_work(w)
