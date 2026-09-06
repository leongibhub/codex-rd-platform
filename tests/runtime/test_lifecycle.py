import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path

from rd_platform.runtime import Runtime


class SyntheticApprovalVerifier:
    """Mechanism fixture only; this class does not authenticate any real human."""
    def verify(self, *, binding, approval_request):
        from rd_platform.lifecycle_base import LifecycleBase
        return dict(authenticated=True,operator='unit-test-fixture-human',provider_id='synthetic-test-only',verification_id='synthetic-approval-'+binding['gate_id'],binding_digest=LifecycleBase.digest(binding))


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.r = Runtime(self.root / 'state.db')
        self.p = self.r.execute('project.create', {'name': 'lifecycle', 'idea': 'verified delivery'})['id']
        for ident, role in [('dev', 'developer'), ('test', 'tester'), ('review', 'reviewer'), ('release', 'release_manager')]:
            self.r.execute('agent.register', {'id': ident, 'role': role})
        self.r.execute('lifecycle.initialize', {'project_id': self.p, 'repository_root': str(self.root), 'mode': 'active'})

    def tearDown(self):
        self.temp.cleanup()

    def artifact(self, ident='REQ-001', kind='REQ', **extra):
        data = dict(project_id=self.p, artifact_id=ident, artifact_type=kind, title=ident, state='BASELINED',
                    content_ref={'inline_json': {'acceptance': 'observable'}}, source={'kind': 'host', 'actor': 'dev'})
        data.update(extra)
        return self.r.execute('artifact.create', data)

    def test_initialize_preserves_v2_and_creates_twelve_undecided_gates(self):
        self.assertEqual('ACTIVE', self.r.snapshot(self.p)['projects'][0]['stage'])
        s = self.r.lifecycle_snapshot(self.p)
        self.assertEqual(12, len(s['gates']))
        self.assertTrue(all(g['gate_status'] is None for g in s['gates']))
        self.assertEqual('G0', s['lifecycle']['current_gate'])

    def test_empty_gate_cannot_pass(self):
        a = self.r.execute('gate.assess', {'project_id': self.p, 'gate_id': 'G0'})
        self.assertEqual('BLOCKED', a['candidate'])
        with self.assertRaises(ValueError):
            self.r.execute('gate.decide', dict(assessment_id=a['id'], status='PASS', decision_evidence_refs=[], decided_by='review'))

    def test_version_append_and_material_change_contract(self):
        self.artifact()
        with self.assertRaises(ValueError):
            self.r.execute('artifact.revise', dict(artifact_id='REQ-001', expected_version=1, state='BASELINED', content_ref={'inline_json': {'x': 2}}, reason='scope changed', material=True))
        self.artifact('CR-001', 'CR')
        a = self.r.execute('artifact.revise', dict(artifact_id='REQ-001', expected_version=1, state='BASELINED', content_ref={'inline_json': {'x': 2}}, reason='scope changed', change_id='CR-001', material=True))
        self.assertEqual(2, a['version'])
        with self.r.store.transaction(write=False) as c:
            self.assertEqual(2, c.execute('SELECT COUNT(*) FROM lc_artifact_versions WHERE artifact_id=?', ('REQ-001',)).fetchone()[0])

    def test_inline_and_path_validation_and_human_spoof(self):
        with self.assertRaises(ValueError):
            self.artifact(content_ref={'path': '../outside', 'sha256': '0' * 64})
        with self.assertRaises(ValueError):
            self.artifact(content_ref={'inline_json': {'token': 'secret'}})
        with self.assertRaises(ValueError):
            self.r.execute('evidence.register', dict(project_id=self.p, kind='human_approval', status='VERIFIED'))

    def test_snapshot_bounds_and_idempotency(self):
        for limit in [True, 0, 501]:
            with self.assertRaises(ValueError): self.r.lifecycle_snapshot(self.p, limit=limit)
        d = dict(project_id=self.p, gate_id='G0')
        a = self.r.execute('gate.assess', d, request_id='a')
        self.assertEqual(a, self.r.execute('gate.assess', d, request_id='a'))

    @staticmethod
    def ref(kind, ident, version=1): return {'type':kind,'id':ident,'version':version}

    def evidence(self, kind='document', actor='review', metadata=None, **extra):
        d=dict(project_id=self.p,kind=kind,status='VERIFIED',source={'kind':'host','actor':actor},locator={'inline_json':{'fixture':'unit test synthetic evidence, never project approval'}},observed_at=datetime.now(timezone.utc).isoformat(),metadata=metadata or {})
        d.update(extra)
        e=self.r.execute('evidence.register',d)
        return self.ref('EVIDENCE',e['id'])

    def model_case(self, ident='TC-001'):
        if not self.r.lifecycle_snapshot(self.p)['artifacts']: self.artifact()
        if not self.r.lifecycle_snapshot(self.p)['test_models']:
            self.r.execute('test_model.create',dict(project_id=self.p,artifact_id='TM-001',source={'kind':'host','actor':'test'},requirement_refs=['REQ-001'],function_tree={'name':'business','children':['validation']},
                risks=[dict(risk_id='RISK-001',description='invalid data',likelihood='HIGH',impact='HIGH',priority='P0',requirement_refs=['REQ-001'])],objects=[dict(object_id='OBJ-001',description='CLI input')],types=['FUNCTIONAL'],
                test_points=[dict(point_id='TP-001',object_id='OBJ-001',type='FUNCTIONAL',rationale='cover risk',risk_refs=['RISK-001'],requirement_refs=['REQ-001'],coverage_rule='all valid and invalid partitions')]))
        return self.r.execute('test_case.create',dict(project_id=self.p,case_id=ident,test_model_id='TM-001',test_point_refs=['TP-001'],requirement_refs=['REQ-001'],test_type='FUNCTIONAL',module='cli',priority='P0',risk='HIGH',preconditions=[],test_data={},steps=[dict(order=1,action='run CLI',expected_observation='valid response')],expected_result='valid response',automation={'status':'MANUAL'},state='BASELINED'))

    def execution(self, case='TC-001', result='PASS'):
        env=self.evidence('test_environment',actor='test')
        e=self.r.execute('test_execution.start',dict(case_id=case,case_version=1,executor_id='test',environment_ref=env))
        evidence=self.evidence('test_execution',actor='test',metadata=dict(execution_id=e['id'],result=result,artifact_refs=[self.ref('TEST_CASE',case)]))
        return self.r.execute('test_execution.finish',dict(execution_id=e['id'],result=result,actual_result='synthetic execution contract fixture',evidence_refs=[evidence]))

    def work(self, **extra):
        data=dict(project_id=self.p,gate_id='G0',activity='implement',required_role='developer',why='business',input_refs=[],output_contract={'required_types':['REQ'],'min_outputs':1},dependencies=[])
        data.update(extra)
        return self.r.execute('work.create',data)

    def test_work_lease_output_contract_pause_and_resume(self):
        w=self.work(); claim=self.r.execute('work.claim',dict(work_order_id=w['id'],agent_id='dev',lease_seconds=60))
        payload=dict(work_order_id=w['id'],agent_id='dev',lease_token=claim['lease_token'])
        self.r.execute('work.heartbeat',payload)
        with self.assertRaises(ValueError): self.r.execute('work.finish',dict(payload,status='DONE',output_refs=[],summary='no outputs'))
        self.r.execute('lifecycle.control',dict(project_id=self.p,action='pause',reason='human pause'))
        with self.assertRaises(ValueError): self.r.execute('work.heartbeat',payload)
        self.r.execute('lifecycle.control',dict(project_id=self.p,action='resume',reason='continue'))
        claim2=self.r.execute('work.claim',dict(work_order_id=w['id'],agent_id='dev',lease_seconds=60))
        with self.assertRaises(ValueError): self.r.execute('work.finish',dict(payload,status='DONE',output_refs=[],summary='late'))
        self.artifact()
        result=self.r.execute('work.finish',dict(payload,lease_token=claim2['lease_token'],status='DONE',output_refs=[self.ref('REQ','REQ-001')],summary='defined requirement'))
        self.assertEqual('DONE',result['status'])
        self.assertNotIn('lease_digest',self.r.lifecycle_snapshot(self.p)['work_orders'][0])

    def test_work_expiry_wrong_role_and_single_claim(self):
        w=self.work()
        with self.assertRaises(ValueError): self.r.execute('work.claim',dict(work_order_id=w['id'],agent_id='test',lease_seconds=60))
        claim=self.r.execute('work.claim',dict(work_order_id=w['id'],agent_id='dev',lease_seconds=1))
        other=self.work()
        with self.assertRaises(ValueError): self.r.execute('work.claim',dict(work_order_id=other['id'],agent_id='dev',lease_seconds=1))
        with patch('rd_platform.lifecycle_base.LifecycleBase.now',return_value='2099-01-01T00:00:00+00:00'):
            self.assertEqual([w['id']],self.r.execute('work.reap',{'project_id':self.p})['expired'])
        with self.assertRaises(ValueError): self.r.execute('work.heartbeat',dict(work_order_id=w['id'],agent_id='dev',lease_token=claim['lease_token']))

    def test_claim_secrets_are_not_persisted_in_request_cache(self):
        w=self.work(); payload=dict(work_order_id=w['id'],agent_id='dev',lease_seconds=60)
        claim=self.r.execute('work.claim',payload,request_id='claim')
        replay=self.r.execute('work.claim',payload,request_id='claim')
        self.assertEqual(claim['id'],replay['id']); self.assertNotEqual(claim['lease_token'],replay['lease_token'])
        self.r.execute('work.heartbeat',dict(work_order_id=w['id'],agent_id='dev',lease_token=replay['lease_token']),request_id='beat')
        with self.r.store.transaction(write=False) as c:
            self.assertNotIn(claim['lease_token'],str([tuple(r) for r in c.execute('SELECT * FROM requests')]))

    def test_typed_links_and_cross_project_rejected(self):
        self.artifact(); self.artifact('DES-001','DES')
        link=dict(project_id=self.p,**{'from':self.ref('REQ','REQ-001'),'to':self.ref('DES','DES-001')},relation='realized_by')
        a=self.r.execute('trace.link',link); self.assertEqual(a,self.r.execute('trace.link',link))
        with self.assertRaises(ValueError): self.r.execute('trace.link',dict(link,relation='implemented_by'))
        p=self.r.execute('project.create',dict(name='other',idea='other'))['id']
        self.r.execute('lifecycle.initialize',dict(project_id=p,repository_root=str(self.root),mode='active'))
        with self.assertRaises(ValueError): self.r.execute('trace.link',dict(link,project_id=p))

    def test_revision_invalidates_downstream_not_unrelated(self):
        self.model_case(); self.artifact('DES-001','DES'); self.artifact('REQ-002','REQ'); self.artifact('DES-002','DES')
        for n in [1,2]: self.r.execute('trace.link',dict(project_id=self.p,**{'from':self.ref('REQ',f'REQ-00{n}'),'to':self.ref('DES',f'DES-00{n}')},relation='realized_by'))
        self.r.execute('artifact.revise',dict(artifact_id='REQ-001',expected_version=1,state='BASELINED',content_ref={'inline_json':{'changed':True}},reason='format',material=False))
        s=self.r.lifecycle_snapshot(self.p)
        self.assertEqual('REVIEW_REQUIRED',s['test_cases'][0]['status'])
        self.assertEqual('VALID',next(l for l in s['trace_links'] if l['from']['id']=='REQ-002')['status'])

    def test_case_model_and_execution_requirements(self):
        case=self.model_case(); self.assertEqual('MANUAL',case['status'])
        env=self.evidence('test_environment',actor='test')
        with self.assertRaises(ValueError): self.r.execute('test_execution.start',dict(case_id=case['id'],case_version=1,executor_id='dev',environment_ref=env))
        run=self.r.execute('test_execution.start',dict(case_id=case['id'],case_version=1,executor_id='test',environment_ref=env))
        with self.assertRaises(ValueError): self.r.execute('test_execution.finish',dict(execution_id=run['id'],result='PASS',actual_result='claimed',evidence_refs=[]))
        wrong=self.evidence('test_execution',actor='test',metadata=dict(execution_id='different',result='PASS',artifact_refs=[self.ref('TEST_CASE',case['id'])]))
        with self.assertRaises(ValueError): self.r.execute('test_execution.finish',dict(execution_id=run['id'],result='PASS',actual_result='claimed',evidence_refs=[wrong]))
        self.r.execute('test_execution.finish',dict(execution_id=run['id'],result='NOT_EXECUTED',actual_result='missing tool',evidence_refs=[]))

    def test_failure_fix_retest_regression_independent_close(self):
        self.model_case(); self.model_case('TC-002'); failed=self.execution(result='FAIL'); bug=failed['defect_id']
        source=failed['evidence_refs']
        self.r.execute('defect.classify',dict(defect_id=bug,category='PRODUCT',severity='CRITICAL',owner_role='developer',rationale='business implementation',classified_by='test',evidence_refs=source))
        task=self.completed_fix_task(bug); fix=self.evidence(actor='dev')
        self.r.execute('defect.fix',dict(defect_id=bug,fix_task_id='TASK-001',completion_task_id=task['id'],fixed_by='dev',evidence_refs=[fix]))
        retest=self.execution()
        with self.assertRaises(ValueError): self.r.execute('defect.resolve',dict(defect_id=bug,resolved_by='test',execution_refs=[self.ref('TEST_EXECUTION',retest['id'])]))
        regression=self.execution('TC-002')
        self.r.execute('defect.resolve',dict(defect_id=bug,resolved_by='test',execution_refs=[self.ref('TEST_EXECUTION',e['id']) for e in [retest,regression]]))
        review=self.evidence('review',metadata=dict(subject_id=bug,result='PASS',artifact_refs=[self.ref('BUG',bug)]))
        with self.assertRaises(ValueError): self.r.execute('defect.close',dict(defect_id=bug,closed_by='dev',evidence_refs=[review]))
        closed=self.r.execute('defect.close',dict(defect_id=bug,closed_by='review',evidence_refs=[review]))
        self.assertEqual('CLOSED',closed['status']); self.assertEqual('FAIL',self.r.lifecycle_snapshot(self.p)['test_executions'][0]['result'])

    def gate_material(self,gate):
        from rd_platform.lifecycle_governance import POLICY
        self.artifact('DOC-'+gate,'DOC')
        return self.evidence(metadata=dict(gate_id=gate,criteria=list(POLICY[gate]),artifact_refs=[self.ref('DOC','DOC-'+gate)]))

    def test_gate_assessment_decision_and_version_freshness(self):
        self.gate_material('G0')
        a=self.r.execute('gate.assess',dict(project_id=self.p,gate_id='G0')); self.assertEqual('PASS',a['candidate'])
        decision=self.evidence('gate_decision',metadata=dict(assessment_id=a['id'],status='PASS'))
        self.r.execute('gate.decide',dict(assessment_id=a['id'],status='PASS',decided_by='review',decision_evidence_refs=[decision]))
        self.assertEqual('G1',self.r.lifecycle_snapshot(self.p)['lifecycle']['current_gate'])
        self.r.execute('artifact.revise',dict(artifact_id='DOC-G0',expected_version=1,state='BASELINED',content_ref={'inline_json':{'changed':True}},reason='format',material=False))
        self.assertEqual('G0',self.r.lifecycle_snapshot(self.p)['lifecycle']['current_gate'])
        self.assertIsNone(self.r.lifecycle_snapshot(self.p)['gates'][0]['gate_status'])
        self.assertEqual(1,len(self.r.lifecycle_snapshot(self.p)['gate_decisions']))

    def test_gate_refuses_stale_assessment_and_unrelated_change_is_allowed(self):
        self.gate_material('G0'); a=self.r.execute('gate.assess',dict(project_id=self.p,gate_id='G0'))
        self.artifact('REQ-999','REQ')
        decision=self.evidence('gate_decision',metadata=dict(assessment_id=a['id'],status='PASS'))
        self.r.execute('gate.decide',dict(assessment_id=a['id'],status='PASS',decided_by='review',decision_evidence_refs=[decision]))
        a=self.r.execute('gate.assess',dict(project_id=self.p,gate_id='G0'))
        self.r.execute('artifact.revise',dict(artifact_id='DOC-G0',expected_version=1,state='BASELINED',content_ref={'inline_json':{'new':1}},reason='format',material=False))
        with self.assertRaises(ValueError): self.r.execute('gate.decide',dict(assessment_id=a['id'],status='PASS',decided_by='review',decision_evidence_refs=[decision]))

    def test_release_missing_g10_and_operator_forgery_are_blocked(self):
        self.artifact(); self.artifact('DOC-ROLLBACK','DOC')
        rel=self.r.execute('release.create',dict(project_id=self.p,release_id='REL-001',version='1.0',artifact_refs=[self.ref('DOC','DOC-ROLLBACK')],requirement_refs=[self.ref('REQ','REQ-001')],known_issue_refs=[],rollback_ref=self.ref('DOC','DOC-ROLLBACK')))
        a=self.r.execute('gate.assess',dict(project_id=self.p,gate_id='G10'))
        with self.assertRaises(ValueError): self.r.execute('release.ready',dict(release_id=rel['id'],assessment_id=a['id'],decision_evidence_refs=[]))
        self.assertIn('WAITING_HUMAN_APPROVAL',a['missing'])
        with self.assertRaises(ValueError): self.r.register_human_approval(dict(project_id=self.p,kind='human_approval',status='VERIFIED'),operator='dev')

    def test_finite_json_migration_integrity_and_event_pagination(self):
        with self.assertRaises(ValueError): self.artifact(content_ref={'inline_json':{'bad':float('nan')}})
        for n in range(4): self.artifact(f'REQ-{n}','REQ')
        first=self.r.lifecycle_snapshot(self.p,limit=2); second=self.r.lifecycle_snapshot(self.p,after_sequence=first['next_sequence'],limit=2)
        self.assertTrue(first['has_more']); self.assertLess(first['events'][-1]['sequence'],second['events'][0]['sequence'])
        self.assertTrue(first['collections_truncated']['artifacts'])
        with self.r.store.transaction() as c: c.execute("UPDATE lc_migrations SET sha256='invalid'")
        with self.assertRaises(ValueError): Runtime(self.root/'state.db')

    def approval_data(self):
        return dict(project_id=self.p,kind='human_approval',status='VERIFIED',locator={'inline_json':{'synthetic_fixture':True}},observed_at=datetime.now(timezone.utc).isoformat(),metadata=dict(gate_id='G9',decision='APPROVE',statement='Synthetic fixture only',artifact_refs=[self.ref('REQ','REQ-001')]))

    def completed_fix_task(self,bug):
        task=self.r.execute('task.create',dict(project_id=self.p,title='repair '+bug,why='actual fix quality',role='developer',requirements=['REQ-001'],dependencies=[],inputs={'fix_defect_id':bug,'lifecycle_task_ref':self.ref('TASK','TASK-001')}))
        self.artifact('TASK-001','TASK',content_ref={'inline_json':dict(defect_id=bug,requirement_refs=['REQ-001'],quality_task_id=task['id'])})
        for phase,actor in [('implementation','dev'),('unit','test'),('integration','test'),('review','review')]:
            run=self.r.execute('run.start',dict(task_id=task['id'],agent_id=actor,phase=phase))
            self.r.execute('run.finish',dict(run_id=run['id'],status='PASS',summary='synthetic isolated quality fixture',evidence={'synthetic_fixture':True,'result':'PASS'}))
        return task

    def test_review_approval_without_verified_provider_rejected(self):
        self.artifact()
        with self.assertRaisesRegex(ValueError,'NOT_AVAILABLE'):
            self.r.register_human_approval(self.approval_data(),operator='made-up-human')

    def test_review_approval_provider_binding_and_replay_validation(self):
        self.artifact(); data=self.approval_data()
        class WrongBinding:
            def verify(self,**kwargs):
                return dict(authenticated=True,operator='unit-test-fixture-human',provider_id='synthetic',verification_id='bad',binding_digest='wrong')
        with self.assertRaises(ValueError):
            Runtime(self.root/'state.db',approval_provider=WrongBinding()).register_human_approval(data,operator='unit-test-fixture-human')
        verified_runtime=Runtime(self.root/'state.db',approval_provider=SyntheticApprovalVerifier())
        approval=verified_runtime.register_human_approval(data,operator='unit-test-fixture-human')
        self.assertEqual('human',approval['recorded_role'])
        self.assertEqual('synthetic-test-only',approval['metadata']['provider_id'])
        with self.assertRaises(ValueError): verified_runtime.register_human_approval(data,operator='unit-test-fixture-human')
        self.assertEqual(1,len(self.r.lifecycle_snapshot(self.p)['evidence']))

    def test_review_fix_without_actual_completed_task_rejected(self):
        self.model_case(); failed=self.execution(result='FAIL'); bug=failed['defect_id']
        self.r.execute('defect.classify',dict(defect_id=bug,category='PRODUCT',severity='CRITICAL',owner_role='developer',rationale='implementation',classified_by='test',evidence_refs=failed['evidence_refs']))
        self.artifact('TASK-001','TASK',state='DRAFT')
        with self.assertRaises(ValueError):
            self.r.execute('defect.fix',dict(defect_id=bug,fix_task_id='TASK-001',fixed_by='dev',evidence_refs=[self.evidence(actor='dev')]))

    def test_review_baselined_task_still_requires_completed_quality(self):
        self.model_case(); failed=self.execution(result='FAIL'); bug=failed['defect_id']
        self.r.execute('defect.classify',dict(defect_id=bug,category='PRODUCT',severity='CRITICAL',owner_role='developer',rationale='implementation',classified_by='test',evidence_refs=failed['evidence_refs']))
        task=self.r.execute('task.create',dict(project_id=self.p,title='unfinished fix',why='fix',role='developer',requirements=['REQ-001'],dependencies=[],inputs={'fix_defect_id':bug,'lifecycle_task_ref':self.ref('TASK','TASK-001')}))
        self.artifact('TASK-001','TASK',content_ref={'inline_json':dict(defect_id=bug,requirement_refs=['REQ-001'],quality_task_id=task['id'])})
        with self.assertRaisesRegex(ValueError,'completed quality task'):
            self.r.execute('defect.fix',dict(defect_id=bug,fix_task_id='TASK-001',completion_task_id=task['id'],fixed_by='dev',evidence_refs=[self.evidence(actor='dev')]))

    def test_review_bearer_in_text_is_not_persisted(self):
        with self.assertRaises(ValueError):
            self.evidence(locator={'inline_json':{'stdout':'Authorization: Bearer synthetic-secret-123'}})
        self.assertNotIn('synthetic-secret-123',str(self.r.lifecycle_snapshot(self.p)))

    def test_review_lost_claim_response_can_rotate_immediately(self):
        w=self.work(); data=dict(work_order_id=w['id'],agent_id='dev',lease_seconds=3600)
        first=self.r.execute('work.claim',data,request_id='lost-response')
        replay=self.r.execute('work.claim',data,request_id='lost-response')
        self.assertIn('lease_token',replay)
        self.assertNotEqual(first['lease_token'],replay['lease_token'])
        with self.assertRaises(ValueError): self.r.execute('work.heartbeat',dict(data,lease_token=first['lease_token']))
        self.r.execute('work.heartbeat',dict(data,lease_token=replay['lease_token']))

    def test_review_prior_gate_path_drift_blocks_following_gate(self):
        import hashlib
        path=self.root/'gate-doc.txt'; path.write_text('baseline')
        self.artifact('DOC-G0','DOC',content_ref={'path':'gate-doc.txt','sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        from rd_platform.lifecycle_governance import POLICY
        self.evidence(metadata=dict(gate_id='G0',criteria=list(POLICY['G0']),artifact_refs=[self.ref('DOC','DOC-G0')]))
        assessment=self.r.execute('gate.assess',dict(project_id=self.p,gate_id='G0'))
        decision=self.evidence('gate_decision',metadata=dict(assessment_id=assessment['id'],status='PASS'))
        self.r.execute('gate.decide',dict(assessment_id=assessment['id'],status='PASS',decided_by='review',decision_evidence_refs=[decision]))
        self.gate_material('G1'); path.write_text('drifted')
        s=self.r.lifecycle_snapshot(self.p)
        self.assertIsNone(s['gates'][0]['gate_status'])
        self.assertEqual('PASS',s['gates'][0]['recorded_gate_status'])
        self.assertEqual('STALE',s['gates'][0]['freshness'])
        with self.r.store.transaction(write=False) as c:
            from rd_platform.lifecycle import LifecycleService
            self.assertEqual('PASS',LifecycleService().get(c,'gates',self.p+':G0')['gate_status'])
        next_gate=self.r.execute('gate.assess',dict(project_id=self.p,gate_id='G1'))
        self.assertEqual('BLOCKED',next_gate['candidate'])

    def test_review_rollback_compensation_and_assessment_history(self):
        self.gate_material('G0'); a=self.r.execute('gate.assess',dict(project_id=self.p,gate_id='G0'))
        decision=self.evidence('gate_decision',metadata=dict(assessment_id=a['id'],status='PASS'))
        self.r.execute('gate.decide',dict(assessment_id=a['id'],status='PASS',decided_by='review',decision_evidence_refs=[decision]))
        self.artifact('CR-ROLLBACK','CR')
        with self.assertRaises(ValueError):
            self.r.execute('lifecycle.control',dict(project_id=self.p,action='rollback',target_gate='G11',change_id='CR-ROLLBACK',affected_refs=[self.ref('DOC','DOC-G0')],reason='cannot move forward'))
        result=self.r.execute('lifecycle.control',dict(project_id=self.p,action='rollback',target_gate='G0',change_id='CR-ROLLBACK',affected_refs=[self.ref('DOC','DOC-G0')],reason='restore affected delivery'))
        self.assertTrue(result['compensation_work_id'])
        s=self.r.lifecycle_snapshot(self.p)
        self.assertEqual('SUPERSEDED',next(row for row in s['gate_assessments'] if row['id']==a['id'])['status'])
        self.assertEqual('READY',s['work_orders'][0]['status'])
        self.assertEqual(1,len(s['artifacts'])-1) # original DOC remains plus CR

    def test_full_gate_release_and_rollback_contract_using_synthetic_fixtures(self):
        # This exercises policy mechanics in an isolated temporary DB. These records
        # are synthetic fixtures, never approval/deployment evidence for this repo.
        from rd_platform.lifecycle_governance import POLICY, TEST_CRITERIA, REVIEW_CRITERIA
        self.r=Runtime(self.root/'state.db',approval_provider=SyntheticApprovalVerifier())
        self.model_case(); execution=self.execution()
        for ident,kind in [('DES-001','DES'),('TASK-001','TASK'),('CODE-001','CODE_CHANGE')]: self.artifact(ident,kind)
        for a,b,relation in [(self.ref('REQ','REQ-001'),self.ref('DES','DES-001'),'realized_by'),(self.ref('DES','DES-001'),self.ref('TASK','TASK-001'),'planned_by'),(self.ref('TASK','TASK-001'),self.ref('CODE_CHANGE','CODE-001'),'implemented_by')]:
            self.r.execute('trace.link',dict(project_id=self.p,**{'from':a,'to':b},relation=relation))
        self.assertEqual('COMPLETE',self.r.lifecycle_snapshot(self.p)['traceability'][0]['status'])
        self.artifact('DOC-ROLLBACK','DOC')
        rel=self.r.execute('release.create',dict(project_id=self.p,release_id='REL-001',version='1.0',artifact_refs=[self.ref('CODE_CHANGE','CODE-001')],requirement_refs=[self.ref('REQ','REQ-001')],known_issue_refs=[],rollback_ref=self.ref('DOC','DOC-ROLLBACK')))
        for n in range(12):
            gate='G'+str(n); self.artifact('DOC-'+gate,'DOC'); subject=[self.ref('DOC','DOC-'+gate)]
            ordinary=[criterion for criterion in POLICY[gate] if criterion not in TEST_CRITERIA|REVIEW_CRITERIA|{'human_acceptance'}]
            if ordinary: self.evidence(metadata=dict(gate_id=gate,criteria=ordinary,artifact_refs=subject))
            tests=[criterion for criterion in POLICY[gate] if criterion in TEST_CRITERIA]
            if tests: self.evidence('test_execution',actor='test',metadata=dict(gate_id=gate,criteria=tests,execution_id=execution['id'],result='PASS',artifact_refs=[self.ref('TEST_CASE','TC-001')]))
            reviews=[criterion for criterion in POLICY[gate] if criterion in REVIEW_CRITERIA]
            if reviews: self.evidence('review',metadata=dict(gate_id=gate,criteria=reviews,subject_id='DOC-'+gate,result='PASS',artifact_refs=subject))
            if n>=9:
                self.r.register_human_approval(dict(project_id=self.p,kind='human_approval',status='VERIFIED',locator={'inline_json':{'synthetic_fixture':True}},observed_at=datetime.now(timezone.utc).isoformat(),metadata=dict(gate_id=gate,criteria=['human_acceptance'] if n==9 else [],decision='APPROVE',statement='Synthetic unit-test approval, not actual human acceptance',artifact_refs=subject)),operator='unit-test-fixture-human')
            assessment=self.r.execute('gate.assess',dict(project_id=self.p,gate_id=gate))
            self.assertEqual('PASS',assessment['candidate'],(gate,assessment['missing']))
            decision=self.evidence('gate_decision',metadata=dict(assessment_id=assessment['id'],status='PASS'))
            self.r.execute('gate.decide',dict(assessment_id=assessment['id'],status='PASS',decided_by='review',decision_evidence_refs=[decision]))
            if n==10:
                ready=self.r.execute('release.ready',dict(release_id=rel['id'],assessment_id=assessment['id'],decision_evidence_refs=[decision]))
                self.assertEqual('READY',ready['status'])
                env=self.evidence('deployment_environment',actor='release')
                deploy=self.evidence('deployment',actor='release',metadata=dict(subject_id=rel['id'],result='PASS',artifact_refs=[self.ref('REL',rel['id'])]))
                released=self.r.execute('release.record_deployment',dict(release_id=rel['id'],environment_ref=env,result='PASS',evidence_refs=[deploy],operator='unit-test-fixture-human'))
                self.assertEqual('RELEASED',released['status'])
        self.assertEqual('CLOSED',self.r.lifecycle_snapshot(self.p)['lifecycle']['state'])
        rollback=self.evidence('rollback',actor='release',metadata=dict(subject_id=rel['id'],result='PASS',artifact_refs=[self.ref('REL',rel['id'])]))
        rolled=self.r.execute('release.rollback',dict(release_id=rel['id'],result='PASS',reason='synthetic restore',evidence_refs=[rollback],operator='unit-test-fixture-human'))
        self.assertEqual('ROLLED_BACK',rolled['status']); self.assertEqual('PASS',rolled['deployments'][0]['result'])


if __name__ == '__main__':
    unittest.main()
