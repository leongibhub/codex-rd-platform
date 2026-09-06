"""TASK-V3-007 contract tests; fixtures are synthetic, never project approvals."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from rd_platform.runtime import Runtime
from rd_platform.store import Store


class LifecycleExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.runtime=Runtime(self.root/'state.db')
        self.project=self.runtime.execute('project.create',dict(name='export fixture',idea='complete evidence'))['id']
        self.runtime.execute('agent.register',dict(id='dev',role='developer'))
        self.runtime.execute('lifecycle.initialize',dict(project_id=self.project,repository_root=str(self.root),mode='active'))

    def tearDown(self): self.temp.cleanup()

    def seed_cases(self,count=507):
        # Synthetic fixture rows obey real evidence provenance/binding rules;
        # they are not actual project execution or approval evidence.
        self.runtime.execute('agent.register',dict(id='test',role='tester'))
        req=self.runtime.execute('artifact.create',dict(project_id=self.project,artifact_type='REQ',artifact_id='REQ-scale',title='scale fixture',state='BASELINED',content_ref={'inline_json':{'synthetic':True}},source={'kind':'host','actor':'dev'}))
        requirements=[{'type':'REQ','id':req['id'],'version':1}]
        now=datetime.now(timezone.utc).isoformat()
        environment=self.runtime.execute('evidence.register',dict(project_id=self.project,kind='test_environment',status='VERIFIED',source={'kind':'host','actor':'test'},locator={'inline_json':{'synthetic':True}},observed_at=now,metadata={}))
        with self.runtime.store.transaction() as c:
            for n in range(count):
                case=dict(id=f'TC-{n}',project_id=self.project,version=1,state='BASELINED',status='AUTOMATED',test_type='FUNCTIONAL',requirement_refs=requirements)
                run=dict(id=f'execution-{n}',project_id=self.project,case_id=case['id'],case_version=1,result='FAIL' if n==count-1 else 'PASS',status='FINISHED',executor_id='test',created_at=now,requirement_refs=requirements,environment_ref={'type':'EVIDENCE','id':environment['id'],'version':1},evidence_refs=[{'type':'EVIDENCE','id':f'EVD-{n}','version':1}])
                body={'synthetic_observation':n}
                evidence=dict(id=f'EVD-{n}',project_id=self.project,version=1,kind='test_execution',status='VERIFIED',source={'kind':'host','actor':'test'},recorded_by='test',recorded_role='tester',observed_at=now,locator={'inline_json':body,'sha256':hashlib.sha256(Store.dumps(body).encode()).hexdigest()},metadata={'execution_id':run['id'],'result':run['result'],'artifact_refs':[{'type':'TEST_CASE','id':case['id'],'version':1}]})
                c.execute('INSERT INTO lc_test_cases VALUES (?,?,?,?)',(case['id'],self.project,case['status'],Store.dumps(case)))
                c.execute('INSERT INTO lc_test_case_versions VALUES (?,?,?)',(case['id'],1,Store.dumps(case)))
                c.execute('INSERT INTO lc_test_executions VALUES (?,?,?,?)',(run['id'],self.project,run['status'],Store.dumps(run)))
                c.execute('INSERT INTO lc_evidence VALUES (?,?,?,?)',(evidence['id'],self.project,evidence['status'],Store.dumps(evidence)))

    def digest(self):
        with self.runtime.store.transaction(write=False) as c:
            return hashlib.sha256('\n'.join(c.iterdump()).encode()).hexdigest()

    def test_report_reads_all_pages_and_late_failure(self):
        from rd_platform.lifecycle_reporting import lifecycle_report_from_runtime
        self.seed_cases(); before=self.digest()
        report=lifecycle_report_from_runtime(self.runtime,self.project,page_size=73)
        self.assertEqual(507,report['total']); self.assertEqual(506,report['counts']['PASS']); self.assertEqual(1,report['counts']['FAIL'])
        self.assertEqual('FAIL',report['conclusion']); self.assertTrue(report['complete_snapshot'])
        self.assertEqual(before,self.digest()); self.assertIn('sha256',report['source_revision'])

    def test_export_complete_active_projection_with_undecided_gates(self):
        from rd_platform.lifecycle_export import export_project
        self.seed_cases(); before=self.digest(); target=self.root/'delivery'
        result=export_project(self.runtime,self.project,target,page_size=61)
        self.assertEqual('COMPLETE',result['status']); self.assertEqual(before,self.digest())
        manifest=json.loads((target/'platform-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual('active',manifest['lifecycle_mode']); self.assertEqual('READ_ONLY_EXPORT',manifest['authority'])
        report=json.loads((target/'docs/06-test/test-report.json').read_text(encoding='utf-8'))
        self.assertEqual(507,report['total']); self.assertFalse(report['recommend_release'])
        gates=json.loads((target/'docs/08-project-management/gates.json').read_text(encoding='utf-8'))
        self.assertEqual(12,len(gates)); self.assertTrue(all(g['gate_status'] is None for g in gates))
        history=json.loads((target/'docs/evidence/version-index.json').read_text(encoding='utf-8'))
        self.assertEqual(507,len(history['test_cases']))
        with self.assertRaises(ValueError): export_project(self.runtime,self.project,target)

    def test_export_omits_raw_bodies_tokens_and_signed_url_queries(self):
        from rd_platform.lifecycle_export import export_project
        artifact=self.runtime.execute('artifact.create',dict(project_id=self.project,artifact_type='REQ',artifact_id='REQ-1',title='requirement',state='BASELINED',content_ref={'inline_json':{'text':'private source body'}},source={'kind':'host','actor':'dev'}))
        with self.runtime.store.transaction() as c:
            row=dict(id='EVD-secret',project_id=self.project,kind='document',status='OBSERVED',version=1,locator={'inline_json':{'stdout':'Authorization: Bearer synthetic-secret'}},metadata={'password':'synthetic-password','url':'https://example.test/result?X-Amz-Signature=synthetic-signature'},source={'kind':'host','actor':'dev'})
            c.execute('INSERT INTO lc_evidence VALUES (?,?,?,?)',(row['id'],self.project,row['status'],Store.dumps(row)))
        target=self.root/'sanitized'; export_project(self.runtime,self.project,target)
        text='\n'.join(path.read_text(encoding='utf-8') for path in target.rglob('*') if path.is_file())
        for forbidden in ('synthetic-secret','synthetic-password','synthetic-signature','private source body'):
            self.assertNotIn(forbidden,text)
        self.assertIn(artifact['content_ref']['sha256'],text)

    def test_failure_marker_and_path_rejection(self):
        import rd_platform.lifecycle_export as module
        with self.assertRaises(ValueError): module.export_project(self.runtime,self.project,self.root/'x'/'..'/'outside')
        with self.assertRaises(ValueError): module.export_project(self.runtime,self.project,self.root)
        original=module._write_text
        def fail_report(path,text):
            if path.name=='test-report.md': raise OSError('synthetic disk failure')
            return original(path,text)
        target=self.root/'failed'
        with patch.object(module,'_write_text',side_effect=fail_report):
            with self.assertRaises(OSError): module.export_project(self.runtime,self.project,target)
        manifest=json.loads((target/'export-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual('FAILED',manifest['status'])
        with self.assertRaises(ValueError): module.export_project(self.runtime,self.project,target)

    def test_report_is_one_consistent_revision_during_concurrent_write(self):
        from rd_platform.lifecycle_reporting import lifecycle_report_from_runtime
        from rd_platform.lifecycle_query import LifecycleCollectionQuery
        self.seed_cases(); inserted=threading.Event(); errors=[]; writers=[]; original=LifecycleCollectionQuery.read
        def writer():
            try:
                with self.runtime.store.transaction() as c:
                    data=dict(id='TC-concurrent',project_id=self.project,version=1,state='BASELINED',status='MANUAL')
                    c.execute('INSERT INTO lc_test_cases VALUES (?,?,?,?)',(data['id'],self.project,data['status'],Store.dumps(data)))
                    inserted.set()
            except BaseException as error: errors.append(error); inserted.set()
        def intercept(query,connection,project_id,collection,**kwargs):
            page=original(query,connection,project_id,collection,**kwargs)
            if collection=='test_cases' and not writers:
                thread=threading.Thread(target=writer); writers.append(thread); thread.start()
                self.assertTrue(inserted.wait(5))
            return page
        with patch.object(LifecycleCollectionQuery,'read',intercept):
            first=lifecycle_report_from_runtime(self.runtime,self.project,page_size=100)
        for thread in writers: thread.join(10)
        self.assertFalse(errors); self.assertEqual(507,first['total'])
        second=lifecycle_report_from_runtime(self.runtime,self.project,page_size=100)
        self.assertEqual(508,second['total']); self.assertNotEqual(first['source_revision']['sha256'],second['source_revision']['sha256'])

    def test_version_index_preserves_revisions_without_copying_content(self):
        from rd_platform.lifecycle_export import export_project
        self.runtime.execute('artifact.create',dict(project_id=self.project,artifact_type='REQ',artifact_id='REQ-history',title='history',state='BASELINED',content_ref={'inline_json':{'text':'private-v1'}},source={'kind':'host','actor':'dev'}))
        self.runtime.execute('artifact.revise',dict(artifact_id='REQ-history',expected_version=1,state='BASELINED',content_ref={'inline_json':{'text':'private-v2'}},reason='wording',material=False))
        target=self.root/'history'; export_project(self.runtime,self.project,target)
        rows=json.loads((target/'docs/evidence/version-index.json').read_text(encoding='utf-8'))['artifacts']
        self.assertEqual([1,2],[r['version'] for r in rows]); self.assertNotEqual(rows[0]['content_sha256'],rows[1]['content_sha256'])
        self.assertNotIn('private-v1',(target/'docs/evidence/version-index.json').read_text(encoding='utf-8'))

    def test_link_parent_and_invalid_page_size_are_rejected(self):
        from rd_platform.lifecycle_export import export_project
        from rd_platform.lifecycle_reporting import lifecycle_report_from_runtime
        with self.assertRaises(ValueError): lifecycle_report_from_runtime(self.runtime,self.project,page_size=501)
        with self.assertRaises(ValueError): export_project(self.runtime,self.project,self.root/'missing'/'child')
        # Link creation is platform/permission dependent; the rejection itself is
        # exercised with a direct lstat-level link observation without OS mutation.
        import rd_platform.lifecycle_export as module
        original=module._is_link
        with patch.object(module,'_is_link',side_effect=lambda p: p==self.root or original(p)):
            with self.assertRaises(ValueError): export_project(self.runtime,self.project,self.root/'link-child')

    def test_markdown_cells_cannot_create_links_or_html(self):
        from rd_platform.lifecycle_export import _cell
        self.assertEqual(r'\[click\]\(https://example.test\) &lt;script&gt; \|',
                         _cell('[click](https://example.test) <script> |'))

    def test_stale_gate_export_preserves_history_without_source_mutation(self):
        from rd_platform.lifecycle_export import export_project
        from rd_platform.lifecycle_governance import POLICY
        self.runtime.execute('agent.register',dict(id='review',role='reviewer'))
        path=self.root/'charter.txt'; path.write_text('synthetic baseline',encoding='utf-8')
        template=self.root/'platform-manifest.json'; template.write_text('{"lifecycle_mode":"template"}',encoding='utf-8')
        self.runtime.execute('artifact.create',dict(project_id=self.project,artifact_type='DOC',artifact_id='DOC-G0',title='fixture charter',state='BASELINED',content_ref={'path':'charter.txt','sha256':hashlib.sha256(path.read_bytes()).hexdigest()},source={'kind':'host','actor':'dev'}))
        def evidence(kind,metadata):
            data=dict(project_id=self.project,kind=kind,status='VERIFIED',source={'kind':'host','actor':'review'},locator={'inline_json':{'fixture':'synthetic mechanism test, not project acceptance'}},observed_at=datetime.now(timezone.utc).isoformat(),metadata=metadata)
            row=self.runtime.execute('evidence.register',data)
            return {'type':'EVIDENCE','id':row['id'],'version':1}
        evidence('document',dict(gate_id='G0',criteria=list(POLICY['G0']),artifact_refs=[{'type':'DOC','id':'DOC-G0','version':1}]))
        assessment=self.runtime.execute('gate.assess',dict(project_id=self.project,gate_id='G0'))
        decision=evidence('gate_decision',dict(assessment_id=assessment['id'],status='PASS'))
        self.runtime.execute('gate.decide',dict(assessment_id=assessment['id'],status='PASS',decided_by='review',decision_evidence_refs=[decision]))
        path.write_text('synthetic external drift',encoding='utf-8'); before=self.digest()
        target=self.root/'stale'; export_project(self.runtime,self.project,target)
        gates=json.loads((target/'docs/08-project-management/gates.json').read_text(encoding='utf-8'))
        self.assertIsNone(gates[0]['gate_status']); self.assertEqual('PASS',gates[0]['recorded_gate_status'])
        self.assertEqual('STALE',gates[0]['freshness']); self.assertEqual('NOT_EVALUATED',gates[0]['evaluation_state'])
        report=json.loads((target/'docs/06-test/test-report.json').read_text(encoding='utf-8'))
        self.assertFalse(report['recommend_release']); self.assertEqual(before,self.digest())
        self.assertEqual('{"lifecycle_mode":"template"}',template.read_text(encoding='utf-8'))

    def test_real_execution_file_drift_is_blocked_but_history_preserved(self):
        from tests.runtime.test_lifecycle_runner import LifecycleRunnerTests
        from rd_platform.lifecycle_reporting import lifecycle_report_from_runtime
        from rd_platform.lifecycle_export import export_project
        fixture=LifecycleRunnerTests(); fixture.setUp()
        try:
            executed=fixture.run_case(); runtime=fixture.f.r; project=fixture.f.p
            self.assertEqual('PASS',lifecycle_report_from_runtime(runtime,project)['case_results'][0]['result'])
            path=fixture.f.root/executed['result_path']
            path.write_text('altered observation',encoding='utf-8')
            for action in ('overwrite','delete'):
                if action=='delete': path.unlink()
                with runtime.store.transaction(write=False) as c: before=list(c.iterdump())
                report=lifecycle_report_from_runtime(runtime,project)
                self.assertEqual('BLOCKED',report['case_results'][0]['result'])
                self.assertEqual('PASS',report['case_results'][0]['observed_result'])
                self.assertEqual('STALE',report['case_results'][0]['freshness'])
                self.assertEqual({'PASS':1},report['historical_execution_counts'])
                target=fixture.f.root/('export-'+action); export_project(runtime,project,target)
                exported=json.loads((target/'docs/06-test/test-report.json').read_text(encoding='utf-8'))
                self.assertEqual('BLOCKED',exported['case_results'][0]['result'])
                self.assertFalse(exported['recommend_release'])
                with runtime.store.transaction(write=False) as c: self.assertEqual(before,list(c.iterdump()))
        finally: fixture.tearDown()

    def test_missing_execution_evidence_is_not_a_current_pass(self):
        from rd_platform.lifecycle_reporting import lifecycle_report_from_runtime
        self.seed_cases(1)
        with self.runtime.store.transaction() as c:
            row=Store.loads(c.execute('SELECT data FROM lc_test_executions').fetchone()[0]); row.update(result='PASS',evidence_refs=[])
            c.execute('UPDATE lc_test_executions SET data=?',(Store.dumps(row),))
        report=lifecycle_report_from_runtime(self.runtime,self.project)
        self.assertEqual('BLOCKED',report['case_results'][0]['result'])

    def test_current_evidence_role_identity_version_status_and_freshness(self):
        import copy
        from rd_platform.lifecycle_reporting import lifecycle_report_from_runtime
        self.seed_cases(2)
        with self.runtime.store.transaction(write=False) as c:
            original=Store.loads(c.execute("SELECT data FROM lc_evidence WHERE id='EVD-0'").fetchone()[0])
        changes={
            'role':lambda row:row.update(recorded_role='developer'),
            'actor':lambda row:row.update(recorded_by='dev'),
            'status':lambda row:row.update(status='OBSERVED'),
            'kind':lambda row:row.update(kind='document'),
            'result':lambda row:row['metadata'].update(result='FAIL'),
            'execution':lambda row:row['metadata'].update(execution_id='wrong-execution'),
            'case_version':lambda row:row['metadata']['artifact_refs'][0].update(version=2),
            'unbound_case':lambda row:row['metadata'].update(artifact_refs=[]),
            'old_observation':lambda row:row.update(observed_at='2000-01-01T00:00:00+00:00'),
            'content_hash':lambda row:row['locator'].update(sha256='0'*64),
        }
        for name,change in changes.items():
            with self.subTest(name=name):
                row=copy.deepcopy(original); change(row)
                with self.runtime.store.transaction() as c:
                    c.execute("UPDATE lc_evidence SET data=? WHERE id='EVD-0'",(Store.dumps(row),))
                before=self.digest(); report=lifecycle_report_from_runtime(self.runtime,self.project)
                self.assertEqual('BLOCKED',report['case_results'][0]['result'])
                self.assertTrue(report['case_results'][0]['freshness_reason']); self.assertEqual(before,self.digest())
        with self.runtime.store.transaction() as c:
            c.execute("UPDATE lc_evidence SET data=? WHERE id='EVD-0'",(Store.dumps(original),))
            superseding=dict(original,id='EVD-new',supersedes_id='EVD-0')
            c.execute('INSERT INTO lc_evidence VALUES (?,?,?,?)',('EVD-new',self.project,'VERIFIED',Store.dumps(superseding)))
        self.assertEqual('BLOCKED',lifecycle_report_from_runtime(self.runtime,self.project)['case_results'][0]['result'])
        with self.runtime.store.transaction() as c:
            c.execute("DELETE FROM lc_evidence WHERE id IN ('EVD-0','EVD-new')")
        self.assertEqual('BLOCKED',lifecycle_report_from_runtime(self.runtime,self.project)['case_results'][0]['result'])


if __name__=='__main__': unittest.main()
