"""TASK-V3-010 real subprocess and fail-closed binding checks."""
import hashlib
import sys
import unittest
from unittest.mock import patch

from tests.runtime import test_lifecycle as fixture_module


class LifecycleRunnerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.LifecycleTests()
        self.fixture.setUp()
        self.f = self.fixture
        self.code = self.f.root / 'check.py'
        self.code.write_text('print("verified assertion")\n', encoding='utf-8')
        self.f.artifact('CODE-001', 'CODE_CHANGE', content_ref={
            'path': 'check.py', 'sha256': hashlib.sha256(self.code.read_bytes()).hexdigest()})
        self.f.artifact()
        self.case = self.f.model_case()
        self.case = self.f.r.execute('test_case.revise', dict(case_id=self.case['id'], expected_version=1,
            reason='Bind executable automation', automation={'status':'AUTOMATED', 'method':'argv',
                'tool':'python', 'entrypoint':'check.py', 'argv':['{python}', 'check.py'], 'cwd':'.',
                'subject_refs':[{'type':'CODE_CHANGE','id':'CODE-001','version':1}]}))

    def tearDown(self):
        self.f.tearDown()

    def run_case(self, **extra):
        from rd_platform.lifecycle_runner import run_case
        return run_case(self.f.r, project_id=self.f.p, case_id=self.case['id'],
                        case_version=self.case['version'], executor_id='test', **extra)

    def test_real_process_records_environment_execution_and_file_digest(self):
        result = self.run_case()
        self.assertEqual('PASS', result['execution']['result'])
        self.assertEqual(0, result['command']['exit_code'])
        path = self.f.root / result['result_path']
        self.assertTrue(path.is_file())
        evidence = self.f.r.lifecycle_snapshot(self.f.p)['evidence']
        self.assertEqual({'test_environment','test_execution'}, {e['kind'] for e in evidence})
        self.assertIn('CODE-001', str(evidence))

    def test_process_failure_opens_defect(self):
        with patch('rd_platform.lifecycle_runner.run_command', return_value={
            'status':'FAIL','exit_code':7,'stdout':'assertion failed','duration_seconds':0.1}):
            result = self.run_case()
        self.assertEqual('FAIL', result['execution']['result'])
        self.assertIn('defect_id', result['execution'])

    def test_wrong_version_or_role_never_executes(self):
        from rd_platform.lifecycle_runner import run_case
        with patch('rd_platform.lifecycle_runner.run_command') as command:
            for version, actor in [(1, 'test'), (2, 'dev')]:
                with self.assertRaises(ValueError):
                    run_case(self.f.r, project_id=self.f.p, case_id=self.case['id'],
                             case_version=version, executor_id=actor)
            command.assert_not_called()

    def test_source_drift_during_command_is_blocked_and_execution_not_active(self):
        def mutate(*args, **kwargs):
            self.code.write_text('print("changed")', encoding='utf-8')
            return {'status':'PASS','exit_code':0,'stdout':'old result','duration_seconds':0.1}
        with patch('rd_platform.lifecycle_runner.run_command', side_effect=mutate):
            result = self.run_case()
        self.assertEqual('BLOCKED', result['execution']['result'])
        self.assertEqual('FINISHED', result['execution']['status'])
        self.assertFalse(self.f.r.lifecycle_snapshot(self.f.p)['defects'])

    def test_adapter_exception_terminates_execution_without_pass(self):
        with patch('rd_platform.lifecycle_runner.run_command', side_effect=RuntimeError('adapter failure')):
            result = self.run_case()
        self.assertEqual('FAIL', result['execution']['result'])
        self.assertEqual('FINISHED', result['execution']['status'])

    def test_paused_project_does_not_launch(self):
        self.f.r.execute('lifecycle.control', {'project_id':self.f.p,'action':'pause','reason':'user paused'})
        with patch('rd_platform.lifecycle_runner.run_command') as command:
            with self.assertRaises(ValueError): self.run_case()
            command.assert_not_called()

    def test_timeout_before_side_effects(self):
        for timeout in (0, True, float('nan'), 3601):
            with self.assertRaises(ValueError): self.run_case(timeout=timeout)
        self.assertFalse(self.f.r.lifecycle_snapshot(self.f.p)['test_executions'])

    def test_interrupt_is_blocked_without_product_failure(self):
        with patch('rd_platform.lifecycle_runner.run_command', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): self.run_case()
        state = self.f.r.lifecycle_snapshot(self.f.p)
        self.assertEqual('BLOCKED', state['test_executions'][0]['result'])
        self.assertFalse(state['defects'])
        self.assertFalse([e for e in state['evidence'] if e['kind'] == 'test_execution'])

    def test_draft_case_must_not_execute(self):
        self.case = self.f.r.execute('test_case.revise', dict(case_id=self.case['id'],
            expected_version=2, state='DRAFT', reason='Unreviewed draft'))
        with patch('rd_platform.lifecycle_runner.run_command') as command:
            with self.assertRaises(ValueError): self.run_case()
            command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
