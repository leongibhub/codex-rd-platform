"""Versioned lifecycle commands composed inside Runtime's transaction."""
from datetime import datetime
from pathlib import Path

from .store import Store
from .lifecycle_base import LifecycleBase, ARTIFACT_TYPES, STATES, EVIDENCE_STATES
from .lifecycle_testing import TestingCommands
from .lifecycle_models import TestModelCommands
from .lifecycle_governance import GovernanceCommands
from .lifecycle_work import WorkCommands


class LifecycleService(TestingCommands, TestModelCommands, GovernanceCommands, WorkCommands, LifecycleBase):
    COMMANDS = frozenset(('lifecycle.initialize lifecycle.control artifact.create artifact.revise '
        'evidence.register trace.link trace.invalidate test_model.create test_model.revise test_model.adopt test_case.create test_case.revise '
        'test_execution.start test_execution.finish test_execution.abort defect.classify defect.fix defect.resolve defect.close '
        'gate.assess gate.decide release.create release.ready release.record_deployment release.rollback '
        'work.create work.claim work.heartbeat work.finish work.control work.reap').split())

    def execute(self, c, command, data):
        self.safe_json({k:v for k,v in data.items() if k!='lease_token'})
        return getattr(self, command.replace('.', '_'))(c,data)

    def lifecycle_initialize(self, c, d):
        project = self.text(d.get('project_id'),'project_id')
        if not c.execute('SELECT 1 FROM projects WHERE id=?',(project,)).fetchone(): raise KeyError('project not found')
        self.enum(d.get('mode'), {'active'}, 'lifecycle mode')
        root = Path(self.text(d.get('repository_root'),'repository_root')).resolve()
        if not root.is_dir(): raise ValueError('repository_root must exist')
        if c.execute('SELECT 1 FROM lc_projects WHERE id=?',(project,)).fetchone():
            old = self.project(c,project)
            if old['repository_root'] != str(root): raise ValueError('lifecycle already initialized with another root')
            return old
        row = dict(id=project,project_id=project,repository_root=str(root),mode='active',current_gate='G0',state='ACTIVE',policy_version='lifecycle-v1',created_at=self.now())
        self.put(c,'projects',row,new=True)
        for n in range(12):
            self.put(c,'gates',dict(id=project+':G'+str(n),project_id=project,gate_id='G'+str(n),ordinal=n,evaluation_state='NOT_EVALUATED',gate_status=None,current_assessment_id=None,decided_at=None),new=True)
        self.event(c,project,'lifecycle.initialized',project,{'repository_root':str(root)})
        return row

    def lifecycle_control(self, c, d):
        p = self.project(c,d.get('project_id'))
        action = self.enum(d.get('action'),{'pause','resume','rollback'},'lifecycle action')
        reason = self.text(d.get('reason'),'reason')
        if action == 'rollback':
            target=self.get(c,'gates',p['id']+':'+self.text(d.get('target_gate'),'target_gate'))
            if target['ordinal']>=int(p['current_gate'][1:]): raise ValueError('rollback target must be an earlier Gate')
            change=self.ref(c,p['id'],{'type':'CR','id':d.get('change_id')})
            refs=self.refs(c,p['id'],d.get('affected_refs'))
            for ref in refs: self.invalidate(c,p['id'],ref,reason,change['id'],fail_if_claimed=True)
            for gate in self.rows(c,'gates',p['id']):
                if gate['ordinal']>=target['ordinal']:
                    self.supersede_assessment(c,gate.get('current_assessment_id'))
                    gate.update(evaluation_state='NOT_EVALUATED',gate_status=None,current_assessment_id=None,decided_at=None); self.put(c,'gates',gate)
            from .orchestration_policy import recovery_dependencies
            work=self.work_create(c,dict(project_id=p['id'],gate_id=target['gate_id'],activity='compensate lifecycle rollback',required_role='documentation_manager',why=reason,input_refs=refs,output_contract={'required_types':['EVIDENCE'],'min_outputs':1},dependencies=recovery_dependencies(self,c,p['id'],target['gate_id'])))
            self.refresh_stage(c,p['id']); p=self.project(c,p['id']); p['compensation_work_id']=work['id']
        elif action == 'pause':
            if p['state'] == 'PAUSED': raise ValueError('already paused')
            p['resume_state'] = p['state']; p['state'] = 'PAUSED'
            for w in self.rows(c,'work_orders',p['id']):
                if w['status'] == 'CLAIMED':
                    w.update(status='READY',lease_digest=None,lease_until=None,agent_id=None,version=w['version']+1)
                    self.put(c,'work_orders',w)
                    self.event(c,p['id'],'work.invalidated',w['id'],{'reason':reason,'external_process_cancelled':False})
        else:
            if p['state'] not in {'PAUSED', 'WAITING_USER'}: raise ValueError('only paused or waiting-user lifecycle may resume')
            p['state'] = p.pop('resume_state','ACTIVE') if p['state'] == 'PAUSED' else 'ACTIVE'
        self.put(c,'projects',p); self.event(c,p['id'],'lifecycle.'+action,p['id'],{'reason':reason})
        return p

    def artifact_create(self, c, d):
        p = self.project(c,d.get('project_id'))['id']
        kind = self.enum(d.get('artifact_type'),ARTIFACT_TYPES,'artifact type')
        if kind == 'TEST_MODEL': raise ValueError('use test_model.create for versioned test models')
        ident = self.text(d.get('artifact_id'),'artifact_id')
        prefix = {'CODE_CHANGE':'CODE','TEST_MODEL':'TM'}.get(kind,kind)
        if not ident.startswith(prefix+'-'): raise ValueError('artifact id prefix must match type')
        source = self.source(c,d.get('source'))
        row = dict(id=ident,artifact_id=ident,project_id=p,artifact_type=kind,title=self.text(d.get('title'),'title'),version=1,
                   state=self.enum(d.get('state'),STATES,'document state'),content_ref=self.content(c,p,d.get('content_ref')),source=source,created_by=source['actor'],created_at=self.now())
        self.put(c,'artifacts',row,new=True)
        c.execute('INSERT INTO lc_artifact_versions VALUES (?,?,?)',(ident,1,Store.dumps(row)))
        self.event(c,p,'artifact.created',ident,{'version':1,'type':kind})
        return row

    def artifact_revise(self, c, d):
        old = self.get(c,'artifacts',d.get('artifact_id'))
        if old['artifact_type'] == 'TEST_MODEL': raise ValueError('use test_model.revise for versioned test models')
        if self.integer(d.get('expected_version'),'expected_version') != old['version']: raise ValueError('artifact revision conflict')
        reason = self.text(d.get('reason'),'reason')
        material = d.get('material',True)
        if type(material) is not bool: raise ValueError('material must be boolean')
        change = d.get('change_id')
        if material and not change: raise ValueError('material revision requires CR')
        if change: self.ref(c,old['project_id'],{'type':'CR','id':change})
        row = dict(old,version=old['version']+1,state=self.enum(d.get('state'),STATES,'document state'),content_ref=self.content(c,old['project_id'],d.get('content_ref')),reason=reason,change_id=change,created_at=self.now())
        if 'source' in d: row['source']=self.source(c,d['source']); row['created_by']=row['source']['actor']
        self.put(c,'artifacts',row)
        c.execute('INSERT INTO lc_artifact_versions VALUES (?,?,?)',(row['id'],row['version'],Store.dumps(row)))
        affected = self.invalidate(c,old['project_id'],{'type':old['artifact_type'],'id':old['id'],'version':old['version']},reason,change)
        self.event(c,old['project_id'],'artifact.revised',old['id'],{'version':row['version'],'reason':reason,'affected':affected})
        return row

    def evidence_register(self, c, d):
        if d.get('kind') == 'human_approval': raise ValueError('human approval requires trusted operator channel')
        return self._register_evidence(c,d)

    def _register_evidence(self,c,d,*,operator=None):
        p = self.project(c,d.get('project_id'))['id']
        kind = self.text(d.get('kind'),'evidence kind')
        status = self.enum(d.get('status'),EVIDENCE_STATES,'evidence status')
        if operator is None:
            source=self.source(c,d.get('source')); actor=source['actor']; role=self.agent(c,actor)['role']
            if status == 'VERIFIED' and source['kind'] not in {'host','tool'}: raise ValueError('untrusted provenance cannot be verified')
        else:
            source={'kind':'human','actor':operator}; actor=operator; role='human'
        observed=self.text(d.get('observed_at'),'observed_at')
        try:
            observed_dt=datetime.fromisoformat(observed)
            if observed_dt.tzinfo is None or observed_dt > datetime.fromisoformat(self.now()): raise ValueError()
        except ValueError as e: raise ValueError('observed_at must be a non-future timezone timestamp') from e
        metadata=d.get('metadata',{})
        if not isinstance(metadata,dict): raise ValueError('metadata must be object')
        self.safe_json(metadata)
        if 'artifact_refs' in metadata: metadata=dict(metadata,artifact_refs=self.refs(c,p,metadata['artifact_refs']))
        if status == 'VERIFIED' and kind in {'test_execution','review','deployment','rollback'}:
            if not metadata.get('artifact_refs'): raise ValueError('execution/review evidence must lock subject versions')
            self.text(metadata.get('execution_id') if kind == 'test_execution' else metadata.get('subject_id'),'evidence subject')
        ident=d.get('evidence_id',self.ident('EVD'))
        self.text(ident,'evidence_id')
        if not ident.startswith('EVD-'): raise ValueError('evidence id must start EVD-')
        supersedes=d.get('supersedes_id')
        if supersedes: self.ref(c,p,{'type':'EVIDENCE','id':supersedes})
        row=dict(id=ident,project_id=p,kind=kind,status=status,version=1,source=source,recorded_by=actor,recorded_role=role,locator=self.content(c,p,d.get('locator')),observed_at=observed,recorded_at=self.now(),metadata=metadata,supersedes_id=supersedes)
        self.put(c,'evidence',row,new=True); self.event(c,p,'evidence.registered',ident,{'kind':kind,'status':status})
        return row

    def approval_binding(self,c,p,meta):
        gate=self.enum(meta.get('gate_id'),{'G'+str(n) for n in range(12)},'human approval gate')
        refs=self.refs(c,p,meta.get('artifact_refs'))
        inputs=self.policy_inputs(c,p,gate)
        inputs['evidence']=[e for e in inputs['evidence'] if e['kind']!='human_approval']
        subject_ids={r['id'] for e in inputs['evidence'] for r in e['metadata'].get('artifact_refs',[])}
        inputs['artifacts']=[r for r in self.rows(c,'artifacts',p) if r['id'] in subject_ids]
        subject_digests=[]
        for ref in refs:
            if ref['type'] in ARTIFACT_TYPES|{'ARTIFACT_VERSION'} and ref['type']!='TEST_MODEL':
                subject_digests.append({'ref':ref,'sha256':self.get(c,'artifacts',ref['id'])['content_ref']['sha256']})
            else: subject_digests.append({'ref':ref})
        return dict(project_id=p,gate_id=gate,decision=meta.get('decision'),statement=meta.get('statement'),artifact_refs=refs,subject_digests=subject_digests,policy_version='lifecycle-v1',policy_input_digest=self.digest(inputs))

    def human_approval(self,c,d,*,operator,provider=None):
        if provider is None or not callable(getattr(provider,'verify',None)):
            raise ValueError('human approval provider NOT_AVAILABLE')
        self.text(operator,'operator'); self.safe_json(d)
        if c.execute('SELECT 1 FROM agents WHERE id=?',(operator,)).fetchone(): raise ValueError('agent identity cannot be human approver')
        if d.get('kind') != 'human_approval' or d.get('status') != 'VERIFIED': raise ValueError('verified human approval required')
        meta=d.get('metadata',{})
        self.enum(meta.get('decision'),{'APPROVE','REJECT'},'human decision')
        self.enum(meta.get('gate_id'),{'G'+str(n) for n in range(12)},'human approval gate')
        self.text(meta.get('statement'),'explicit operator statement')
        binding=self.approval_binding(c,d.get('project_id'),meta)
        # Give the external verifier a detached copy; input mutation cannot alter
        # the platform's binding. The provider owns real human authentication.
        verified=provider.verify(binding=Store.loads(Store.dumps(binding)),approval_request=Store.loads(Store.dumps(d)))
        if not isinstance(verified,dict) or verified.get('authenticated') is not True or verified.get('operator')!=operator or verified.get('binding_digest')!=self.digest(binding):
            raise ValueError('human approval authentication or scope binding failed')
        self.text(verified.get('provider_id'),'approval provider identity')
        self.text(verified.get('verification_id'),'approval verification identity')
        if any(e['metadata'].get('provider_id')==verified['provider_id'] and e['metadata'].get('verification_id')==verified['verification_id'] for e in self.rows(c,'evidence',d['project_id'])):
            raise ValueError('approval verification has already been consumed')
        metadata=dict(meta,verified_binding=binding,verified_binding_digest=self.digest(binding),provider_id=verified['provider_id'],verification_id=verified['verification_id'])
        return self._register_evidence(c,dict(d,metadata=metadata),operator=verified['operator'])

    def trace_link(self,c,d):
        p=self.project(c,d.get('project_id'))['id']
        a=self.ref(c,p,d.get('from')); b=self.ref(c,p,d.get('to'))
        relation=d.get('relation'); ak,bk=a['type'],b['type']
        allowed=(relation=='refines' and ak in {'BG','MR','PRD'} and bk in {'REQ','NFR'} or
                 relation=='realized_by' and ak in {'REQ','NFR'} and bk=='DES' or
                 relation=='planned_by' and ak=='DES' and bk=='TASK' or
                 relation=='implemented_by' and ak=='TASK' and bk=='CODE_CHANGE' or
                 relation=='verified_by' and ak in {'REQ','NFR'} and bk=='TEST_CASE' or
                 relation=='executed_by' and ak=='TEST_CASE' and bk=='TEST_EXECUTION' or
                 relation=='found' and ak=='TEST_EXECUTION' and bk=='BUG' or
                 relation=='fixed_by' and ak=='BUG' and bk=='TASK' or
                 relation=='included_in' and ak in {'REQ','NFR','CODE_CHANGE','TEST_EXECUTION','BUG'} and bk=='REL' or
                 relation=='evidenced_by' and bk=='EVIDENCE' or relation=='documented_by' and bk=='ARTIFACT_VERSION')
        if not allowed or a==b: raise ValueError('invalid typed trace relationship')
        for row in self.rows(c,'trace_links',p):
            if row['status']=='VALID' and row['from']==a and row['to']==b and row['relation']==relation: return row
        row=dict(id=self.ident('link'),project_id=p,**{'from':a,'to':b},relation=relation,status='VALID',change_id=None,created_at=self.now())
        self.put(c,'trace_links',row,new=True); self.event(c,p,'trace.linked',row['id'],{'from':a,'to':b,'relation':relation})
        return row

    def trace_invalidate(self,c,d):
        row=self.get(c,'trace_links',d.get('link_id')); reason=self.text(d.get('reason'),'reason')
        self.ref(c,row['project_id'],{'type':'CR','id':d.get('change_id')})
        self.invalidate(c,row['project_id'],row['from'],reason,d['change_id'])
        row=self.get(c,'trace_links',row['id']); row.update(status='INVALIDATED',change_id=d['change_id'])
        self.put(c,'trace_links',row); self.event(c,row['project_id'],'trace.invalidated',row['id'],{'reason':reason})
        return row

    def invalidate(self,c,p,start,reason,change,*,fail_if_claimed=False):
        affected={start['id']}; frontier=[start['id']]
        links=self.rows(c,'trace_links',p)
        while frontier:
            ident=frontier.pop()
            for link in links:
                if link['status']=='VALID' and link['from']['id']==ident:
                    link.update(status='STALE',change_id=change); self.put(c,'trace_links',link)
                    nxt=link['to']['id']
                    if nxt not in affected: affected.add(nxt); frontier.append(nxt)
        for case in self.rows(c,'test_cases',p):
            if case['id'] in affected or any(r['id'] in affected for r in case['requirement_refs']):
                case['status']='REVIEW_REQUIRED'; affected.add(case['id']); self.put(c,'test_cases',case)
        for w in self.rows(c,'work_orders',p):
            if any(r['id'] in affected for r in w['input_refs']):
                if w['status']=='CLAIMED':
                    if fail_if_claimed:
                        raise ValueError('reconcile original external outcome before compensation')
                    self.event(c,p,'work.invalidated',w['id'],{'reason':reason,'change_id':change,'external_process_cancelled':False})
                w.update(status='REVIEW_REQUIRED',lease_digest=None,lease_until=None,agent_id=None,version=w['version']+1); self.put(c,'work_orders',w)
        for rel in self.rows(c,'releases',p):
            if any(r['id'] in affected for r in rel['artifact_refs']+rel['requirement_refs']+rel['known_issue_refs']+[rel['rollback_ref']]):
                rel['status']='CHANGE_PENDING'; self.put(c,'releases',rel)
        for a in self.rows(c,'gate_assessments',p):
            if any(r['id'] in affected for r in a['input_refs']):
                gate=self.get(c,'gates',p+':'+a['gate_id'])
                if gate['current_assessment_id']==a['id']:
                    self.supersede_assessment(c,a['id'])
                    gate.update(evaluation_state='NOT_EVALUATED',gate_status=None,current_assessment_id=None,decided_at=None); self.put(c,'gates',gate)
        self.refresh_stage(c,p)
        return sorted(affected)

    def trace_summary(self,c,p):
        links=[]
        for link in self.rows(c,'trace_links',p):
            if link['status']!='VALID': continue
            try: self.ref(c,p,link['from']); self.ref(c,p,link['to'])
            except (ValueError,KeyError): continue
            links.append(link)
        results=[]
        for req in self.rows(c,'artifacts',p):
            if req['artifact_type'] not in {'REQ','NFR'} or req['state']=='OBSOLETE': continue
            seen={req['id']}; changed=True; types=set(); executions=[]
            while changed:
                changed=False
                for l in links:
                    if l['from']['id'] in seen and l['to']['id'] not in seen:
                        seen.add(l['to']['id']); types.add(l['to']['type']); changed=True
                        if l['to']['type']=='TEST_EXECUTION': executions.append(self.get(c,'test_executions',l['to']['id']))
            missing=sorted({'DES','TASK','CODE_CHANGE','TEST_CASE'}-types)
            cases=[case for case in self.rows(c,'test_cases',p) if case['id'] in seen]
            for case in cases:
                runs=[e for e in executions if e['case_id']==case['id'] and e['case_version']==case['version']]
                if case['status']=='REVIEW_REQUIRED' or not runs or runs[-1].get('result')!='PASS': missing.append('PASS_EXECUTION:'+case['id'])
            if not executions: missing.append('PASS_EXECUTION')
            for bug in self.rows(c,'defects',p):
                if bug['status']!='CLOSED' and bug['severity'] in {'BLOCKER','CRITICAL'} and any(r['id']==req['id'] for r in bug['requirement_refs']): missing.append('OPEN_BLOCKER_DEFECT:'+bug['id'])
            results.append(dict(requirement_id=req['id'],version=req['version'],status='COMPLETE' if not missing else ('PARTIAL' if types else 'GAP'),missing=missing))
        return results

    def snapshot(self,c,project_id,*,after_sequence=0,limit=200):
        self.integer(after_sequence,'after_sequence',0); self.integer(limit,'limit',1,500)
        p=self.project(c,project_id)
        names=('gates','work_orders','artifacts','trace_links','test_models','test_cases','test_executions','defects','gate_assessments','gate_decisions','evidence','releases')
        collections={name:self.rows(c,name,project_id,limit=limit) for name in names}
        collections['work_orders']=[self.public_work(w) for w in collections['work_orders']]
        counts={name:c.execute(f'SELECT COUNT(*) FROM lc_{name} WHERE project_id=?',(project_id,)).fetchone()[0] for name in names}
        events=[dict(r) for r in c.execute('SELECT * FROM lc_events WHERE project_id=? AND sequence>? ORDER BY sequence LIMIT ?',(project_id,after_sequence,limit+1))]
        more=len(events)>limit; events=events[:limit]
        for e in events: e['data']=Store.loads(e['data'])
        trace=self.trace_summary(c,project_id)
        tests={r[0]:r[1] for r in c.execute("SELECT COALESCE(json_extract(data,'$.result'),status),COUNT(*) FROM lc_test_executions WHERE project_id=? GROUP BY COALESCE(json_extract(data,'$.result'),status)",(project_id,))}
        open_defects=c.execute("SELECT COUNT(*) FROM lc_defects WHERE project_id=? AND status!='CLOSED'",(project_id,)).fetchone()[0]
        # Never promote a cached decision after external file/evidence drift.
        # This is a read-only validity projection; recorded decisions stay intact.
        projection=self.project_gates(c,project_id)
        all_gates=projection['gates']; stale_from=projection['stale_from']; stale_assessments=projection['stale_assessment_ids']
        collections['gates']=all_gates[:limit]
        for a in collections['gate_assessments']:
            if a['id'] in stale_assessments: a['status']='SUPERSEDED'; a['freshness']='STALE'
        if stale_from is not None:
            p=dict(p,current_gate=stale_from,state='PAUSED' if p['state']=='PAUSED' else 'BLOCKED')
        p=dict(p,progress={'decided':sum(g['evaluation_state']=='DECIDED' for g in all_gates),'total':12})
        reasons=[]
        gate=next(g for g in all_gates if g['gate_id']==p['current_gate'])
        if gate['current_assessment_id']: reasons=self.get(c,'gate_assessments',gate['current_assessment_id'])['missing']
        if stale_from is not None: reasons=['STALE_GATE_EVIDENCE:'+stale_from]+reasons
        return self.redact_projection(dict(schema_version='lifecycle-v1',project_id=project_id,lifecycle=p,summary=dict(artifacts=counts['artifacts'],trace_gaps=sum(t['status']!='COMPLETE' for t in trace),tests=tests,open_defects=open_defects),
                    **collections,gate_evaluations=collections['gate_assessments'],traceability=trace[:limit],next_actions=reasons,events=events,next_sequence=events[-1]['sequence'] if events else after_sequence,has_more=more,
                    collection_counts=counts,collections_truncated={n:counts[n]>limit for n in names}))
