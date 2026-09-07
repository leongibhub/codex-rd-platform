"""Evidence policies, explicit Gate decisions and release fact recording."""
from .store import Store

POLICY = {
 'G0': ('project_charter','business_case','objectives','scope','stakeholders','initial_plan','initial_risks'),
 'G1': ('market_research','competitor_analysis','technology_research','feasibility','research_summary'),
 'G2': ('product_vision','personas','journeys','feature_priorities','prd_acceptance'),
 'G3': ('functional_requirements','nonfunctional_requirements','interface_data_security','acceptance_criteria','requirement_review','rtm'),
 'G4': ('hld','system_architecture','component_design','api_data_design','deployment_security_failure','adrs','architecture_review'),
 'G5': ('implementation_plan','task_breakdown','dependency_map','task_requirement_trace','test_strategy'),
 'G6': ('implementation','unit_tests','documentation','commit_trace','local_verification'),
 'G7': ('test_plan','executable_cases','test_environment','test_results','defect_summary','regression','test_conclusion'),
 'G8': ('code_review','architecture_conformance','security_regression_risks','classified_findings'),
 'G9': ('requirement_coverage','rtm','unresolved_defects_risks','human_acceptance'),
 'G10': ('release_readiness','release_notes','deployment_instructions','rollback_plan','known_issues','delivery_manifest'),
 'G11': ('delivery_acceptance','objective_achievement','unresolved_items','maintenance_handover','lessons_learned','closure_report','archive_index','documentation_completeness'),
}
TEST_CRITERIA={'unit_tests','local_verification','test_results','regression','test_conclusion'}
REVIEW_CRITERIA={'requirement_review','architecture_review','code_review','architecture_conformance','security_regression_risks','classified_findings'}


class GovernanceCommands:
    def project_gates(self,c,project_id):
        """Read-only effective Gate state; preserve recorded decision history."""
        gates=self.rows(c,'gates',project_id)
        stale_from=None; stale_assessments=set()
        for gate in gates:
            gate['recorded_gate_status']=gate['gate_status']; gate['freshness']='CURRENT'
            if gate['gate_status']=='PASS':
                assessment=self.get(c,'gate_assessments',gate['current_assessment_id'])
                if stale_from is not None or assessment['input_digest']!=self.digest(self.policy_inputs(c,project_id,gate['gate_id'])) or self.evaluate(c,project_id,gate['gate_id'],check_prerequisites=False)[1]:
                    if stale_from is None: stale_from=gate['gate_id']
                    stale_assessments.add(gate['current_assessment_id'])
                    gate.update(gate_status=None,evaluation_state='NOT_EVALUATED',freshness='STALE',freshness_reason='STALE_GATE_EVIDENCE:'+stale_from)
        return {'gates':gates,'stale_from':stale_from,'stale_assessment_ids':stale_assessments}

    @staticmethod
    def supersede_assessment(c,assessment_id):
        if assessment_id:
            # Assessment fact JSON stays immutable; freshness is an indexed status.
            c.execute("UPDATE lc_gate_assessments SET status='SUPERSEDED' WHERE id=?",(assessment_id,))

    def refresh_stage(self,c,p):
        project=self.project(c,p); gates=self.rows(c,'gates',p)
        first=next((g for g in gates if g['gate_status']!='PASS'),None)
        if first:
            for g in gates:
                if g['ordinal']>first['ordinal'] and g['gate_status']=='PASS':
                    self.supersede_assessment(c,g.get('current_assessment_id'))
                    g.update(evaluation_state='NOT_EVALUATED',gate_status=None,current_assessment_id=None,decided_at=None)
                    self.put(c,'gates',g)
        project['current_gate']=first['gate_id'] if first else 'G11'
        if first is None: project['state']='CLOSED'
        elif project['state']=='CLOSED': project['state']='ACTIVE'
        self.put(c,'projects',project)

    def policy_inputs(self,c,p,gate):
        # Decision evidence is added after assessment; it is not an input to the assessment.
        inputs={}
        inputs['evidence']=[e for e in self.rows(c,'evidence',p) if e['kind']!='gate_decision' and (e['metadata'].get('gate_id')==gate or gate in e['metadata'].get('gate_ids',[]))]
        subject_ids={r['id'] for e in inputs['evidence'] for r in e['metadata'].get('artifact_refs',[])}
        inputs['artifacts']=[r for r in self.rows(c,'artifacts',p) if r['id'] in subject_ids]
        if int(gate[1:])>=7:
            for name in ('trace_links','test_cases','test_executions','defects'): inputs[name]=self.rows(c,name,p)
        if gate=='G10':
            inputs['releases']=[{k:v for k,v in r.items() if k in {'id','version','artifact_refs','requirement_refs','rollback_ref','known_issue_refs'}} for r in self.rows(c,'releases',p)]
        inputs['prerequisite_gates']=[{'gate_id':g['gate_id'],'gate_status':g['gate_status'],'current_assessment_id':g['current_assessment_id']} for g in self.rows(c,'gates',p) if g['ordinal']<int(gate[1:])]
        return inputs

    def evaluate(self,c,p,gate,*,check_prerequisites=True):
        missing=[]; checks=[]; refs=[]; evidence=self.policy_inputs(c,p,gate)['evidence']; eligible=[]
        for e in evidence:
            try:
                self.evidence_refs(c,p,[{'type':'EVIDENCE','id':e['id']}])
                if e['kind']=='human_approval':
                    if e['metadata'].get('verified_binding_digest')!=self.digest(self.approval_binding(c,p,e['metadata'])): raise ValueError('human approval binding is no longer current')
                linked=e['metadata'].get('artifact_refs',[])
                for ref in linked:
                    if ref['type'] in {'REQ','NFR','DES','DOC','TASK','CODE_CHANGE','BG','MR','PRD','ADR','CR','RISK'}:
                        artifact=self.get(c,'artifacts',ref['id'])
                        if artifact['state'] not in {'BASELINED','APPROVED'} or not self.content_current(c,p,artifact['content_ref']): raise ValueError('artifact not baselined or content changed')
                if e['kind']!='human_approval' and not linked: raise ValueError('criterion evidence requires versioned subject')
                eligible.append(e)
            except (ValueError,KeyError): continue
        for criterion in POLICY[gate]:
            matches=[]
            for e in eligible:
                if criterion not in e['metadata'].get('criteria',[]): continue
                if criterion in TEST_CRITERIA:
                    if e['kind']!='test_execution' or e['recorded_role']!='tester': continue
                    try:
                        execution=self.get(c,'test_executions',e['metadata'].get('execution_id'))
                        if execution['project_id']!=p or execution.get('result')!='PASS': continue
                    except (KeyError,ValueError): continue
                elif criterion in REVIEW_CRITERIA:
                    if e['kind']!='review' or e['recorded_role']!='reviewer' or e['metadata'].get('result')!='PASS': continue
                elif criterion=='human_acceptance':
                    if e['kind']!='human_approval' or e['recorded_role']!='human' or e['metadata'].get('decision')!='APPROVE': continue
                elif e['kind'] not in {'document','review','test_environment'}: continue
                matches.append(e)
            ok=bool(matches)
            checks.append({'criterion':criterion,'satisfied':ok,'evidence_refs':[{'type':'EVIDENCE','id':e['id'],'version':1} for e in matches]})
            if not ok: missing.append('MISSING_EVIDENCE:'+criterion)
            for e in matches:
                refs.append({'type':'EVIDENCE','id':e['id'],'version':1}); refs.extend(e['metadata'].get('artifact_refs',[]))
        prior=[g for g in self.rows(c,'gates',p) if g['ordinal']<int(gate[1:]) and g['gate_status']!='PASS']
        if prior: missing.append('PREREQUISITE_GATE_NOT_PASS:'+prior[0]['gate_id'])
        if check_prerequisites:
            for previous in self.rows(c,'gates',p):
                if previous['ordinal']>=int(gate[1:]) or previous['gate_status']!='PASS': continue
                prior_assessment=self.get(c,'gate_assessments',previous['current_assessment_id'])
                if prior_assessment['input_digest']!=self.digest(self.policy_inputs(c,p,previous['gate_id'])) or self.evaluate(c,p,previous['gate_id'],check_prerequisites=False)[1]:
                    missing.append('STALE_PREREQUISITE_GATE:'+previous['gate_id'])
        if int(gate[1:])>=3:
            trace=self.trace_summary(c,p)
            if not trace: missing.append('MISSING_REQUIREMENT')
            if int(gate[1:])>=7 and any(r['status']!='COMPLETE' for r in trace): missing.append('INCOMPLETE_TRACEABILITY')
        if int(gate[1:])>=7:
            bugs=self.rows(c,'defects',p)
            if any(b['status']!='CLOSED' and b['severity'] in {'BLOCKER','CRITICAL','UNCLASSIFIED'} for b in bugs): missing.append('OPEN_BLOCKER_DEFECT')
            for case in self.rows(c,'test_cases',p):
                executions=[e for e in self.rows(c,'test_executions',p) if e['case_id']==case['id'] and e['case_version']==case['version']]
                if case['state']!='OBSOLETE' and (case['status']=='REVIEW_REQUIRED' or not executions or executions[-1].get('result')!='PASS'): missing.append('TEST_NOT_PASS:'+case['id'])
        if gate in {'G9','G10','G11'}:
            approvals=[e for e in eligible if e['kind']=='human_approval' and e['recorded_role']=='human' and e['metadata'].get('gate_id')==gate and e['metadata'].get('decision')=='APPROVE']
            if not approvals: missing.append('WAITING_HUMAN_APPROVAL')
            for e in approvals: refs.append({'type':'EVIDENCE','id':e['id'],'version':1}); refs.extend(e['metadata'].get('artifact_refs',[]))
        if gate=='G10' and not self.rows(c,'releases',p): missing.append('MISSING_RELEASE_MANIFEST')
        if gate=='G11' and not any(r['status']=='RELEASED' and r['deployments'] for r in self.rows(c,'releases',p)): missing.append('NO_RELEASED_DEPLOYMENT')
        return checks,missing,list({Store.dumps(r):r for r in refs}.values())

    def gate_assess(self,c,d):
        p=self.project(c,d.get('project_id'))['id']; gate=self.enum(d.get('gate_id'),set(POLICY),'gate_id')
        checks,missing,refs=self.evaluate(c,p,gate)
        row=dict(id=self.ident('assessment'),project_id=p,gate_id=gate,policy_version='lifecycle-v1',input_digest=self.digest(self.policy_inputs(c,p,gate)),input_refs=refs,candidate='BLOCKED' if missing else 'PASS',checks=checks,missing=missing,status='CURRENT',created_at=self.now())
        self.put(c,'gate_assessments',row,new=True)
        g=self.get(c,'gates',p+':'+gate)
        self.supersede_assessment(c,g.get('current_assessment_id'))
        g.update(evaluation_state='IN_REVIEW',current_assessment_id=row['id'],gate_status=None,decided_at=None); self.put(c,'gates',g)
        self.refresh_stage(c,p)
        self.event(c,p,'gate.assessed',row['id'],{'gate_id':gate,'candidate':row['candidate'],'missing':missing})
        return row

    def gate_decide(self,c,d):
        a=self.get(c,'gate_assessments',d.get('assessment_id')); p=a['project_id']; gate=a['gate_id']
        g=self.get(c,'gates',p+':'+gate)
        if g['current_assessment_id']!=a['id'] or self.digest(self.policy_inputs(c,p,gate))!=a['input_digest']: raise ValueError('assessment is stale; reassess')
        if any(dec['assessment_id']==a['id'] for dec in self.rows(c,'gate_decisions',p)): raise ValueError('assessment already decided')
        status=self.enum(d.get('status'),{'PASS','FAIL','BLOCKED'},'gate status')
        actor=self.agent(c,d.get('decided_by'),{'reviewer','release_manager'} if gate=='G10' else {'reviewer'})
        checks,missing,_=self.evaluate(c,p,gate)
        if status=='PASS' and (a['candidate']!='PASS' or missing): raise ValueError('Gate PASS criteria not met')
        refs=self.refs(c,p,d.get('decision_evidence_refs'),nonempty=status=='PASS')
        if refs:
            evidence=self.evidence_refs(c,p,refs,kinds={'gate_decision'},roles={actor['role']})
            for e in evidence:
                if e['recorded_by']!=actor['id'] or e['metadata'].get('assessment_id')!=a['id'] or e['metadata'].get('status')!=status: raise ValueError('decision evidence does not match actor, assessment or status')
        if status!='PASS':
            self.text(d.get('reason'),'decision reason'); self.text(d.get('resolution'),'resolution condition')
        decision=dict(id=self.ident('decision'),project_id=p,assessment_id=a['id'],gate_id=gate,status=status,evidence_refs=refs,decided_by=actor['id'],reason=d.get('reason'),resolution=d.get('resolution'),created_at=self.now())
        self.put(c,'gate_decisions',decision,new=True)
        g.update(evaluation_state='DECIDED',gate_status=status,decided_at=self.now()); self.put(c,'gates',g); self.refresh_stage(c,p)
        if status=='FAIL':
            from .orchestration_policy import recovery_dependencies
            self.work_create(c,dict(project_id=p,gate_id=gate,activity='remediate gate '+gate,required_role='documentation_manager',why=d['reason'],input_refs=a['input_refs'],output_contract={'min_outputs':1,'required_types':['EVIDENCE']},dependencies=recovery_dependencies(self,c,p,gate)))
        self.event(c,p,'gate.decided',decision['id'],{'gate_id':gate,'status':status,'decided_by':actor['id']})
        return decision

    def release_create(self,c,d):
        p=self.project(c,d.get('project_id'))['id']; ident=self.text(d.get('release_id'),'release_id')
        if not ident.startswith('REL-'): raise ValueError('release id must start REL-')
        artifacts=self.refs(c,p,d.get('artifact_refs')); requirements=self.requirement_refs(c,p,d.get('requirement_refs')); issues=self.refs(c,p,d.get('known_issue_refs'),nonempty=False)
        if any(r['type'] not in {'BUG','RISK'} for r in issues): raise ValueError('known issues must be BUG or RISK')
        rollback=self.ref(c,p,d.get('rollback_ref'))
        if rollback['type'] not in {'DOC','ARTIFACT_VERSION'}: raise ValueError('rollback plan artifact required')
        row=dict(id=ident,project_id=p,version=1,release_version=self.text(d.get('version'),'release version'),status='DRAFT',artifact_refs=artifacts,requirement_refs=requirements,known_issue_refs=issues,rollback_ref=rollback,created_at=self.now(),deployments=[],rollbacks=[])
        self.put(c,'releases',row,new=True); c.execute('INSERT INTO lc_release_versions VALUES (?,?,?)',(ident,1,Store.dumps(row)))
        for ref in requirements+[r for r in artifacts if r['type'] in {'CODE_CHANGE','TEST_EXECUTION','BUG'}]: self.trace_link(c,{'project_id':p,'from':ref,'to':{'type':'REL','id':ident},'relation':'included_in'})
        self.event(c,p,'release.created',ident,{'version':row['release_version']})
        return row

    def release_ready(self,c,d):
        rel=self.get(c,'releases',d.get('release_id')); p=rel['project_id']
        if rel['status']!='DRAFT': raise ValueError('draft release required')
        a=self.get(c,'gate_assessments',d.get('assessment_id')); gate=self.get(c,'gates',p+':G10')
        if a['project_id']!=p or a['gate_id']!='G10' or gate['gate_status']!='PASS' or gate['current_assessment_id']!=a['id']: raise ValueError('current G10 PASS decision required')
        if self.digest(self.policy_inputs(c,p,'G10'))!=a['input_digest']: raise ValueError('G10 assessment is stale')
        self.refs(c,p,rel['artifact_refs']+rel['requirement_refs']+[rel['rollback_ref']])
        evidence=self.evidence_refs(c,p,d.get('decision_evidence_refs'),kinds={'gate_decision'})
        for e in evidence:
            if e['metadata'].get('assessment_id')!=a['id'] or e['metadata'].get('status')!='PASS': raise ValueError('matching G10 PASS decision evidence required')
        _,missing,_=self.evaluate(c,p,'G10')
        if missing: raise ValueError('release policy no longer satisfied')
        rel.update(status='READY',ready_at=self.now(),assessment_id=a['id']); self.put(c,'releases',rel)
        self.event(c,p,'release.ready',rel['id'],{'assessment_id':a['id']})
        return rel

    def release_record_deployment(self,c,d):
        rel=self.get(c,'releases',d.get('release_id')); p=rel['project_id']
        if rel['status']!='READY': raise ValueError('READY release required')
        gate=self.get(c,'gates',p+':G10')
        if gate['gate_status']!='PASS' or gate['current_assessment_id']!=rel['assessment_id'] or self.evaluate(c,p,'G10')[1]: raise ValueError('release Gate no longer permits deployment')
        result=self.enum(d.get('result'),{'PASS','FAIL'},'deployment result'); operator=self.text(d.get('operator'),'operator')
        if c.execute('SELECT 1 FROM agents WHERE id=?',(operator,)).fetchone(): raise ValueError('deployment operator must be explicit human operator identity')
        env=self.ref(c,p,d.get('environment_ref')); self.evidence_refs(c,p,[env],kinds={'deployment_environment'})
        refs=self.refs(c,p,d.get('evidence_refs')); evidence=self.evidence_refs(c,p,refs,kinds={'deployment'},roles={'release_manager'})
        for e in evidence:
            if e['metadata'].get('subject_id')!=rel['id'] or e['metadata'].get('result')!=result or e['observed_at']<rel['ready_at']: raise ValueError('fresh matching deployment evidence required')
        self.refs(c,p,rel['artifact_refs']+rel['requirement_refs']+[rel['rollback_ref']])
        record=dict(environment_ref=env,result=result,evidence_refs=refs,operator=operator,recorded_at=self.now())
        rel['deployments'].append(record); rel['status']='RELEASED' if result=='PASS' else 'DEPLOYMENT_FAILED'
        self.put(c,'releases',rel); self.event(c,p,'release.deployment_recorded',rel['id'],record)
        return rel

    def release_rollback(self,c,d):
        rel=self.get(c,'releases',d.get('release_id')); p=rel['project_id']
        if rel['status'] not in {'RELEASED','DEPLOYMENT_FAILED','CHANGE_PENDING','ROLLBACK_FAILED'} or not rel['deployments']: raise ValueError('deployment fact required before rollback')
        operator=self.text(d.get('operator'),'operator'); reason=self.text(d.get('reason'),'reason')
        if c.execute('SELECT 1 FROM agents WHERE id=?',(operator,)).fetchone(): raise ValueError('rollback operator must be explicit human operator identity')
        result=self.enum(d.get('result'),{'PASS','FAIL'},'rollback result'); refs=self.refs(c,p,d.get('evidence_refs'))
        evidence=self.evidence_refs(c,p,refs,kinds={'rollback'},roles={'release_manager'})
        for e in evidence:
            if e['metadata'].get('subject_id')!=rel['id'] or e['metadata'].get('result')!=result or e['observed_at']<rel['deployments'][-1]['recorded_at']: raise ValueError('fresh matching rollback evidence required')
        record=dict(result=result,evidence_refs=refs,operator=operator,reason=reason,recorded_at=self.now()); rel['rollbacks'].append(record)
        rel['status']='ROLLED_BACK' if result=='PASS' else 'ROLLBACK_FAILED'; self.put(c,'releases',rel); self.event(c,p,'release.rollback_recorded',rel['id'],record)
        closure=self.get(c,'gates',p+':G11')
        self.supersede_assessment(c,closure.get('current_assessment_id'))
        closure.update(evaluation_state='NOT_EVALUATED',gate_status=None,current_assessment_id=None,decided_at=None)
        self.put(c,'gates',closure); self.refresh_stage(c,p)
        return rel
