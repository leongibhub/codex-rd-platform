"""Risk-led test definitions, execution facts and independent defect closure."""
from .store import Store

TEST_TYPES={'FUNCTIONAL','NEGATIVE','BOUNDARY','PERFORMANCE','STRESS','STABILITY','COMPATIBILITY','SECURITY','RECOVERY','DATA_CONSISTENCY'}


class TestingCommands:
    def requirement_refs(self,c,p,values):
        if not isinstance(values,list) or not values: raise ValueError('requirement references required')
        refs=self.refs(c,p,[{'type':'NFR' if v.startswith('NFR-') else 'REQ','id':v} if isinstance(v,str) else v for v in values])
        if any(r['type'] not in {'REQ','NFR'} for r in refs): raise ValueError('only requirement references allowed')
        return refs

    def test_model_create(self,c,d):
        from .lifecycle_models import TestModelCommands
        return TestModelCommands.test_model_create(self,c,d)

    def test_model_revise(self,c,d):
        from .lifecycle_models import TestModelCommands
        return TestModelCommands.test_model_revise(self,c,d)

    def test_model_adopt(self,c,d):
        from .lifecycle_models import TestModelCommands
        return TestModelCommands.test_model_adopt(self,c,d)

    def case_data(self,c,d):
        p=self.project(c,d.get('project_id'))['id']; model=self.get(c,'test_models',d.get('test_model_id'))
        if model['project_id']!=p: raise ValueError('test model belongs to another project')
        if model.get('status')!='CURRENT' or model.get('state')=='OBSOLETE' or not model.get('source') or not c.execute('SELECT 1 FROM lc_artifacts WHERE id=? AND json_extract(data,\'$.artifact_type\')=\'TEST_MODEL\' AND json_extract(data,\'$.version\')=?', (model['id'], model['version'])).fetchone(): raise ValueError('test model lacks current artifact provenance')
        self.refs(c,p,model['requirement_refs'])
        refs=self.requirement_refs(c,p,d.get('requirement_refs')); points=self.strings(d.get('test_point_refs'),'test_point_refs')
        selected=[v for v in model['test_points'] if v['point_id'] in points]
        if len(selected)!=len(points): raise ValueError('test point not found')
        reqids={r['id'] for r in refs}
        for point in selected:
            pointrefs=self.requirement_refs(c,p,point['requirement_refs'])
            if not reqids.intersection(r['id'] for r in pointrefs): raise ValueError('test point and case requirements do not intersect')
        if not reqids<={r['id'] for r in model['requirement_refs']}: raise ValueError('case requirements outside model')
        typ=self.enum(d.get('test_type'),TEST_TYPES,'test type')
        if any(point['type']!=typ for point in selected): raise ValueError('case type differs from test point')
        steps=d.get('steps')
        if not isinstance(steps,list) or not steps: raise ValueError('ordered steps required')
        for index,step in enumerate(steps,1):
            if not isinstance(step,dict) or type(step.get('order')) is not int or step['order']!=index: raise ValueError('steps must have sequential order')
            self.text(step.get('action'),'step action'); self.text(step.get('expected_observation'),'expected observation')
        preconditions=self.strings(d.get('preconditions'),'preconditions',False)
        data=d.get('test_data')
        if not isinstance(data,dict): raise ValueError('test_data must be object')
        automation=d.get('automation',{'status':'MANUAL'})
        if not isinstance(automation,dict): raise ValueError('automation must be object')
        self.enum(automation.get('status'),{'AUTOMATED','MANUAL','NOT_FEASIBLE','PENDING'},'automation status')
        if automation['status']=='AUTOMATED':
            for field in ('method','tool','entrypoint'): self.text(automation.get(field),field)
        if automation['status']=='NOT_FEASIBLE': self.text(automation.get('reason'),'automation reason')
        return dict(project_id=p,test_model_id=model['id'],test_model_version=model['version'],test_point_refs=points,requirement_refs=refs,test_type=typ,module=self.text(d.get('module'),'module'),priority=self.enum(d.get('priority'),{'P0','P1','P2','P3'},'case priority'),risk=self.enum(d.get('risk'),{'LOW','MEDIUM','HIGH'},'case risk'),preconditions=preconditions,test_data=data,steps=steps,expected_result=self.text(d.get('expected_result'),'expected_result'),automation=automation,state=self.enum(d.get('state'),{'DRAFT','BASELINED','APPROVED','OBSOLETE'},'case state'),status=automation['status'],created_at=self.now())

    def test_case_create(self,c,d):
        row=self.case_data(c,d); ident=self.text(d.get('case_id'),'case_id')
        if not ident.startswith('TC-'): raise ValueError('case id must start TC-')
        row.update(id=ident,case_id=ident,version=1)
        self.put(c,'test_cases',row,new=True); c.execute('INSERT INTO lc_test_case_versions VALUES (?,?,?)',(ident,1,Store.dumps(row)))
        for req in row['requirement_refs']: self.trace_link(c,{'project_id':row['project_id'],'from':req,'to':{'type':'TEST_CASE','id':ident},'relation':'verified_by'})
        self.event(c,row['project_id'],'test_case.created',ident,{'version':1})
        return row

    def test_case_revise(self,c,d):
        old=self.get(c,'test_cases',d.get('case_id'))
        if self.integer(d.get('expected_version'),'expected_version')!=old['version']: raise ValueError('case revision conflict')
        reason=self.text(d.get('reason'),'reason')
        row=self.case_data(c,dict(old,**d)); row.update(id=old['id'],case_id=old['id'],version=old['version']+1)
        if row['project_id']!=old['project_id']: raise ValueError('case cannot change project')
        self.invalidate(c,old['project_id'],{'type':'TEST_CASE','id':old['id'],'version':old['version']},reason,d.get('change_id'))
        self.put(c,'test_cases',row); c.execute('INSERT INTO lc_test_case_versions VALUES (?,?,?)',(row['id'],row['version'],Store.dumps(row)))
        for req in row['requirement_refs']: self.trace_link(c,{'project_id':row['project_id'],'from':req,'to':{'type':'TEST_CASE','id':row['id']},'relation':'verified_by'})
        self.event(c,row['project_id'],'test_case.revised',row['id'],{'version':row['version'],'reason':reason})
        return row

    def test_execution_start(self,c,d):
        case=self.get(c,'test_cases',d.get('case_id')); p=case['project_id']
        if self.integer(d.get('case_version'),'case_version')!=case['version'] or case['status']=='REVIEW_REQUIRED' or case['state']=='OBSOLETE': raise ValueError('case version is stale or needs review')
        model=self.get(c,'test_models',case['test_model_id'])
        if model['project_id']!=p or model.get('status')!='CURRENT' or model.get('state')=='OBSOLETE' or not model.get('source') or model['version']!=case.get('test_model_version') or not c.execute('SELECT 1 FROM lc_artifacts WHERE id=? AND json_extract(data,\'$.artifact_type\')=\'TEST_MODEL\' AND json_extract(data,\'$.version\')=?', (model['id'], model['version'])).fetchone(): raise ValueError('case test model is stale or lacks artifact provenance')
        self.refs(c,p,case['requirement_refs'])
        agent=self.agent(c,d.get('executor_id'),{'tester'})
        env=self.refs(c,p,[d.get('environment_ref')])[0]
        if env['type']!='EVIDENCE': raise ValueError('environment evidence reference required')
        self.evidence_refs(c,p,[env],kinds={'test_environment'})
        runid=d.get('run_id')
        if runid:
            r=c.execute('SELECT r.*,t.project_id FROM runs r JOIN tasks t ON r.task_id=t.id WHERE r.id=?',(runid,)).fetchone()
            if not r or r['project_id']!=p or r['agent_id']!=agent['id'] or r['status']!='ACTIVE' or r['phase'] not in {'unit','integration'}: raise ValueError('run must be current tester run in project')
        row=dict(id=self.ident('execution'),project_id=p,version=1,case_id=case['id'],case_version=case['version'],requirement_refs=case['requirement_refs'],environment_ref=env,executor_id=agent['id'],run_id=runid,status='ACTIVE',result=None,created_at=self.now())
        if c.execute("SELECT 1 FROM lc_test_executions WHERE status='ACTIVE' AND json_extract(data,'$.case_id')=? AND json_extract(data,'$.case_version')=?",(case['id'],case['version'])).fetchone(): raise ValueError('case version already executing')
        self.put(c,'test_executions',row,new=True); self.trace_link(c,{'project_id':p,'from':{'type':'TEST_CASE','id':case['id']},'to':{'type':'TEST_EXECUTION','id':row['id']},'relation':'executed_by'})
        self.event(c,p,'test_execution.started',row['id'],{'case_id':case['id'],'executor_id':agent['id']})
        return row

    def test_execution_finish(self,c,d):
        row=self.get(c,'test_executions',d.get('execution_id')); p=row['project_id']
        if row['status']!='ACTIVE': raise ValueError('execution already finished')
        if row.get('run_id'):
            run=c.execute('SELECT r.status,r.revision,r.attempt,t.revision AS current_revision,t.attempt AS current_attempt FROM runs r JOIN tasks t ON r.task_id=t.id WHERE r.id=?',(row['run_id'],)).fetchone()
            if not run or run['status']!='ACTIVE' or run['revision']!=run['current_revision'] or run['attempt']!=run['current_attempt']: raise ValueError('quality run is no longer active/current')
        case=self.get(c,'test_cases',row['case_id'])
        if case['version']!=row['case_version'] or case['status']=='REVIEW_REQUIRED': raise ValueError('execution refers to stale case')
        self.refs(c,p,row['requirement_refs'])
        result=self.enum(d.get('result'),{'PASS','FAIL','BLOCKED','NOT_EXECUTED'},'test result'); actual=self.text(d.get('actual_result'),'actual_result')
        refs=self.refs(c,p,d.get('evidence_refs'),nonempty=result in {'PASS','FAIL'})
        if result in {'PASS','FAIL'}:
            evidence=self.evidence_refs(c,p,refs,kinds={'test_execution'},roles={'tester'})
            for e in evidence:
                if e['recorded_by']!=row['executor_id'] or e['metadata'].get('execution_id')!=row['id'] or e['metadata'].get('result')!=result: raise ValueError('execution evidence identity or result mismatch')
                if {'type':'TEST_CASE','id':row['case_id'],'version':row['case_version']} not in e['metadata']['artifact_refs']: raise ValueError('evidence must lock executed case version')
                if e['observed_at']<row['created_at']: raise ValueError('execution evidence predates execution')
        metrics=d.get('metrics',{})
        if not isinstance(metrics,dict): raise ValueError('metrics must be object')
        if case['test_type'] in {'PERFORMANCE','STRESS','STABILITY'} and result in {'PASS','FAIL'}:
            self.integer(metrics.get('sample_count'),'sample_count'); self.text(metrics.get('load_model'),'load_model'); self.text(metrics.get('raw_result_locator'),'raw_result_locator')
            duration=metrics.get('duration_seconds')
            if isinstance(duration,bool) or not isinstance(duration,(int,float)) or duration<=0: raise ValueError('actual duration required')
        row.update(status='FINISHED',result=result,actual_result=actual,evidence_refs=refs,metrics=metrics,finished_at=self.now()); self.put(c,'test_executions',row)
        if result=='FAIL':
            bug=dict(id=self.ident('BUG'),project_id=p,version=1,source_execution=row['id'],category='UNCLASSIFIED',severity='UNCLASSIFIED',status='OPEN',owner_role=None,requirement_refs=row['requirement_refs'],regression_case_refs=[],created_at=self.now())
            self.put(c,'defects',bug,new=True); self.trace_link(c,{'project_id':p,'from':{'type':'TEST_EXECUTION','id':row['id']},'to':{'type':'BUG','id':bug['id']},'relation':'found'})
            row['defect_id']=bug['id']; self.put(c,'test_executions',row); self.event(c,p,'defect.opened',bug['id'],{'source_execution':row['id']})
        self.event(c,p,'test_execution.finished',row['id'],{'result':result})
        return row

    def defect_classify(self,c,d):
        bug=self.get(c,'defects',d.get('defect_id'))
        if bug['status']!='OPEN': raise ValueError('only open defect may be classified')
        self.agent(c,d.get('classified_by'),{'tester','reviewer'})
        category=self.enum(d.get('category'),{'PRODUCT','TEST_SCRIPT','ENVIRONMENT','CONFIGURATION','REQUIREMENT','PERFORMANCE'},'defect category')
        owner=self.enum(d.get('owner_role'),{'developer','tester','architect','requirement_analyst'},'defect owner')
        permitted={'PRODUCT':{'developer'},'TEST_SCRIPT':{'tester','developer'},'ENVIRONMENT':{'developer'},'CONFIGURATION':{'developer'},'REQUIREMENT':{'requirement_analyst'},'PERFORMANCE':{'developer','architect'}}
        if owner not in permitted[category]: raise ValueError('owner role does not match defect category')
        refs=self.refs(c,bug['project_id'],d.get('evidence_refs'))
        self.evidence_refs(c,bug['project_id'],refs)
        bug.update(category=category,severity=self.enum(d.get('severity'),{'BLOCKER','CRITICAL','MAJOR','MINOR','TRIVIAL'},'defect severity'),owner_role=owner,rationale=self.text(d.get('rationale'),'rationale'),classification_evidence_refs=refs,classified_by=d['classified_by'])
        self.put(c,'defects',bug); self.event(c,bug['project_id'],'defect.classified',bug['id'],{'category':category,'owner_role':owner})
        return bug

    def defect_fix(self,c,d):
        bug=self.get(c,'defects',d.get('defect_id')); p=bug['project_id']
        if bug['status']!='OPEN' or bug['category']=='UNCLASSIFIED': raise ValueError('classified open defect required')
        fixer=self.agent(c,d.get('fixed_by'),{bug['owner_role']})
        task=self.ref(c,p,{'type':'TASK','id':d.get('fix_task_id')})
        completion=self.fix_completion(c,bug,task,fixer['id'],d.get('completion_task_id'))
        if bug['category']=='REQUIREMENT': self.ref(c,p,{'type':'CR','id':d.get('change_id')})
        refs=self.refs(c,p,d.get('evidence_refs')); self.evidence_refs(c,p,refs)
        reqids={r['id'] for r in bug['requirement_refs']}
        regression=[{'type':'TEST_CASE','id':case['id'],'version':case['version']} for case in self.rows(c,'test_cases',p) if reqids.intersection(r['id'] for r in case['requirement_refs'])]
        bug.update(status='FIXED',fix_task_id=task['id'],fix_task_ref=task,fix_completion=completion,fixed_by=fixer['id'],fix_evidence_refs=refs,fixed_at=self.now(),regression_case_refs=regression)
        self.put(c,'defects',bug); self.trace_link(c,{'project_id':p,'from':{'type':'BUG','id':bug['id']},'to':task,'relation':'fixed_by'})
        self.event(c,p,'defect.fixed',bug['id'],{'regression_case_refs':regression})
        return bug

    def fix_completion(self,c,bug,task_ref,fixer,completion_task_id):
        self.ref(c,bug['project_id'],task_ref)
        artifact=self.get(c,'artifacts',task_ref['id'])
        if artifact['state'] not in {'BASELINED','APPROVED'}: raise ValueError('fix task must be BASELINED or APPROVED')
        body=artifact['content_ref'].get('inline_json')
        if body is None and 'path' in artifact['content_ref']:
            from pathlib import Path
            try: body=Store.loads((Path(self.project(c,bug['project_id'])['repository_root'])/artifact['content_ref']['path']).read_text(encoding='utf-8'))
            except (ValueError,OSError): raise ValueError('fix task requires structured JSON content') from None
        if not isinstance(body,dict) or body.get('defect_id')!=bug['id']: raise ValueError('fix task must identify the defect it fixes')
        requirements=self.requirement_refs(c,bug['project_id'],body.get('requirement_refs'))
        if {r['id'] for r in requirements}!={r['id'] for r in bug['requirement_refs']}: raise ValueError('fix task requirement scope mismatch')
        quality_id=self.text(completion_task_id,'completion_task_id')
        if body.get('quality_task_id')!=quality_id: raise ValueError('fix task must bind quality task')
        quality=c.execute('SELECT * FROM tasks WHERE id=?',(quality_id,)).fetchone()
        if not quality or quality['project_id']!=bug['project_id'] or quality['status']!='DONE': raise ValueError('actual completed quality task required')
        if quality['created_at']<bug['created_at']: raise ValueError('quality task predates defect')
        inputs=Store.loads(quality['inputs'])
        if inputs.get('fix_defect_id')!=bug['id'] or inputs.get('lifecycle_task_ref')!=task_ref: raise ValueError('quality task does not bind this defect and artifact version')
        if not {r['id'] for r in requirements}<=set(Store.loads(quality['requirements'])): raise ValueError('quality requirements do not cover fix')
        runs=[dict(r) for r in c.execute("SELECT * FROM runs WHERE task_id=? AND revision=? AND attempt=? AND status='PASS' ORDER BY created_at",(quality_id,quality['revision'],quality['attempt']))]
        phases={r['phase']:r for r in runs}
        if set(phases)!={'implementation','unit','integration','review'} or phases['implementation']['agent_id']!=fixer: raise ValueError('complete current fix quality chain required')
        developer=phases['implementation']['agent_id']; reviewer=phases['review']['agent_id']
        if developer==reviewer or any(phases[phase]['agent_id'] in {developer,reviewer} for phase in ('unit','integration')): raise ValueError('independent fix quality identities required')
        self.agent(c,reviewer,{'reviewer'})
        for phase in ('unit','integration'): self.agent(c,phases[phase]['agent_id'],{'tester'})
        result=dict(task_id=quality_id,revision=quality['revision'],attempt=quality['attempt'])
        if bug.get('fix_completion') and result!=bug['fix_completion']: raise ValueError('fix quality completion has changed')
        return result

    def defect_resolve(self,c,d):
        bug=self.get(c,'defects',d.get('defect_id')); p=bug['project_id']
        if bug['status']!='FIXED': raise ValueError('fixed defect required')
        self.fix_completion(c,bug,bug['fix_task_ref'],bug['fixed_by'],bug['fix_completion']['task_id'])
        actor=self.agent(c,d.get('resolved_by'),{'tester'})
        if actor['id']==bug['fixed_by']: raise ValueError('fixer cannot retest own fix')
        refs=self.refs(c,p,d.get('execution_refs')); executions=[]
        for ref in refs:
            if ref['type']!='TEST_EXECUTION': raise ValueError('execution references required')
            e=self.get(c,'test_executions',ref['id'])
            if e.get('result')!='PASS' or e['executor_id']!=actor['id'] or e['created_at']<=bug['fixed_at']: raise ValueError('fresh independent passing retest required')
            self.evidence_refs(c,p,e['evidence_refs'],kinds={'test_execution'},roles={'tester'}); executions.append(e)
        for case in self.refs(c,p,bug['regression_case_refs']):
            matching=[e for e in executions if e['case_id']==case['id'] and e['case_version']==case['version']]
            if not matching: raise ValueError('regression set is incomplete')
            latest=[e for e in self.rows(c,'test_executions',p) if e['case_id']==case['id'] and e['case_version']==case['version']]
            if latest[-1]['id'] not in {e['id'] for e in matching}: raise ValueError('newer execution supersedes regression evidence')
        bug.update(status='RESOLVED',resolved_by=actor['id'],retest_execution_refs=refs,resolved_at=self.now()); self.put(c,'defects',bug)
        self.event(c,p,'defect.resolved',bug['id'],{'executions':refs})
        return bug

    def defect_close(self,c,d):
        bug=self.get(c,'defects',d.get('defect_id')); p=bug['project_id']
        if bug['status']!='RESOLVED': raise ValueError('resolved defect required')
        self.fix_completion(c,bug,bug['fix_task_ref'],bug['fixed_by'],bug['fix_completion']['task_id'])
        actor=self.agent(c,d.get('closed_by'),{'reviewer'})
        if actor['id'] in {bug['fixed_by'],bug['resolved_by']}: raise ValueError('independent reviewer required')
        refs=self.refs(c,p,d.get('evidence_refs')); evidence=self.evidence_refs(c,p,refs,kinds={'review'},roles={'reviewer'})
        for e in evidence:
            if e['recorded_by']!=actor['id'] or e['metadata'].get('subject_id')!=bug['id'] or e['metadata'].get('result')!='PASS' or e['observed_at']<bug['resolved_at']: raise ValueError('fresh defect review evidence required')
        for ref in bug['regression_case_refs']:
            self.ref(c,p,ref)
            runs=[r for r in self.rows(c,'test_executions',p) if r['case_id']==ref['id'] and r['case_version']==ref['version']]
            if not runs or runs[-1].get('result')!='PASS': raise ValueError('regression no longer passing')
        bug.update(status='CLOSED',closed_by=actor['id'],closure_evidence_refs=refs,closed_at=self.now()); self.put(c,'defects',bug)
        self.event(c,p,'defect.closed',bug['id'],{'closed_by':actor['id']})
        return bug
