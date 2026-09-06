"""Host admission integration with mocked transport, not live model evidence."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from tests.runtime.test_worker_service import WorkerServiceTests
from rd_platform.worker_service import run_service


class ProposalAdmissionTests(WorkerServiceTests):
    def config_proposal(self):
        cfg = self.config([])
        cfg['workers'][0].update(source_paths=['app.py', 'other.py'],
            backend={'type': 'responses', 'model': 'fixture', 'api_key_env': 'FIXTURE_UNUSED'})
        return cfg

    def proposal(self, *, update=False, ident='CODE-APP-1', path='app.py', content='value = 1\n'):
        return {'action': 'update' if update else 'create', 'id': ident, 'type': 'CODE_CHANGE',
            'title': 'Fixture code', 'relative_path': path, 'content': content,
            'expected_sha256': hashlib.sha256((self.root/path).read_bytes()).hexdigest() if update else None}

    def execute_proposals(self, proposals, side_effect=None):
        def transport(spec, **kwargs):
            self.assertEqual('responses', spec['type'])
            self.assertIn('work', kwargs['context_bundle'])
            self.assertEqual(['app.py', 'other.py'], [s['path'] for s in kwargs['context_bundle']['allowed_sources']])
            if side_effect: side_effect()
            return {'status': 'PASS', 'stdout': json.dumps({'status': 'DONE', 'summary': 'fixture', 'proposals': proposals})}
        with patch('rd_platform.worker_service.execute_backend', side_effect=transport):
            return run_service(self.runtime, self.config_proposal(), once=True)

    def test_actual_create_then_cas_update_and_host_hash(self):
        self.work(required_types=['CODE_CHANGE'])
        self.assertEqual(1, self.execute_proposals([self.proposal()])['completed'])
        self.work(required_types=['CODE_CHANGE'])
        update = self.proposal(update=True, ident='CODE-APP-2', content='value = 2\n')
        self.assertEqual(1, self.execute_proposals([update])['completed'])
        self.assertEqual('value = 2\n', (self.root/'app.py').read_text())
        artifacts = self.runtime.lifecycle_snapshot(self.project)['artifacts']
        self.assertTrue(all(a['state'] == 'DRAFT' for a in artifacts))
        self.assertEqual(2, len(artifacts))

    def test_second_invalid_artifact_rolls_back_all_files_and_db(self):
        self.work(required_types=['CODE_CHANGE'])
        a, b = self.proposal(), self.proposal(ident='INVALID-ID', path='other.py')
        self.assertEqual(1, self.execute_proposals([a, b])['failed'])
        self.assertFalse((self.root/'app.py').exists())
        self.assertFalse((self.root/'other.py').exists())
        self.assertFalse(self.runtime.lifecycle_snapshot(self.project)['artifacts'])

    def test_pause_before_admission_creates_no_files(self):
        self.work(required_types=['CODE_CHANGE'])
        self.execute_proposals([self.proposal()], lambda: self.runtime.execute('lifecycle.control',
            {'project_id': self.project, 'action': 'pause', 'reason': 'fixture race'}))
        self.assertFalse((self.root/'app.py').exists())

    def test_external_drift_during_rollback_is_durable_failure(self):
        self.work(required_types=['CODE_CHANGE'])
        def fail_admission(*args, **kwargs):
            (self.root/'app.py').write_text('external', encoding='utf-8')
            raise ValueError('fixture admission failure')
        with patch('rd_platform.worker_service._register_artifacts', side_effect=fail_admission):
            self.assertEqual(1, self.execute_proposals([self.proposal()])['failed'])
        snapshot = self.runtime.lifecycle_snapshot(self.project)
        self.assertEqual('FAILED', snapshot['work_orders'][0]['status'])
        self.assertEqual('external', (self.root/'app.py').read_text())
        self.assertTrue(snapshot['evidence'][0]['locator']['inline_json']['command']['recovery_required'])

    def test_another_project_cannot_recover_our_journal(self):
        self.work(required_types=['CODE_CHANGE'])
        with patch('rd_platform.worker_service.commit_proposals', side_effect=OSError('fixture disk')):
            self.assertEqual(1, self.execute_proposals([self.proposal()])['completed'])
        other = self.runtime.execute('project.create', {'name': 'Other', 'idea': 'Same root distinct project'})['id']
        self.runtime.execute('lifecycle.initialize', {'project_id': other, 'repository_root': str(self.root), 'mode': 'active'})
        config = self.config_proposal(); config['project_id'] = other
        run_service(self.runtime, config, once=True)
        self.assertTrue((self.root/'app.py').exists())
        self.assertEqual('DONE', self.runtime.lifecycle_snapshot(self.project)['work_orders'][0]['status'])

    def test_forged_journal_root_cannot_touch_sibling(self):
        self.work(required_types=['CODE_CHANGE'])
        with patch('rd_platform.worker_service.commit_proposals', side_effect=OSError('fixture disk')):
            self.assertEqual(1, self.execute_proposals([self.proposal()])['completed'])
        sibling = self.root.parent/'sibling'; sibling.mkdir()
        sentinel = sibling/'app.py'; sentinel.write_text('value = 1\n', encoding='utf-8')
        journal = next((self.root/'.rd-platform/proposal-journal').glob('*.json'))
        record = json.loads(journal.read_text()); record['root'] = str(sibling)
        journal.write_text(json.dumps(record), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'root'):
            run_service(self.runtime, self.config_proposal(), once=True)
        self.assertTrue(sentinel.exists())

    def test_committed_db_does_not_hide_changed_file_on_recovery(self):
        self.work(required_types=['CODE_CHANGE'])
        with patch('rd_platform.worker_service.commit_proposals', side_effect=OSError('fixture disk')):
            self.assertEqual(1, self.execute_proposals([self.proposal()])['completed'])
        (self.root/'app.py').write_text('external', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'drift'):
            run_service(self.runtime, self.config_proposal(), once=True)
        self.assertEqual('external', (self.root/'app.py').read_text())

    def test_rollback_preserves_existing_empty_parent_directory(self):
        from rd_platform.proposal_files import prepare, apply, rollback
        parent = self.root/'existing'; parent.mkdir()
        p = self.proposal(path='existing/file.py')
        journal, _ = prepare(self.root, [p], ['existing/file.py'])
        apply(journal); rollback(journal)
        self.assertTrue(parent.is_dir())
        self.assertFalse((parent/'file.py').exists())

    def test_external_cas_change_preserved(self):
        (self.root/'app.py').write_text('old', encoding='utf-8')
        p = self.proposal(update=True)
        self.work(required_types=['CODE_CHANGE'])
        result = self.execute_proposals([p], lambda: (self.root/'app.py').write_text('external', encoding='utf-8'))
        self.assertEqual(1, result['failed'])
        self.assertEqual('external', (self.root/'app.py').read_text())

    def test_post_db_commit_journal_error_preserves_files_and_recovers(self):
        self.work(required_types=['CODE_CHANGE'])
        with patch('rd_platform.worker_service.commit_proposals', side_effect=OSError('fixture disk')):
            self.assertEqual(1, self.execute_proposals([self.proposal()])['completed'])
        self.assertTrue((self.root/'app.py').exists())
        run_service(self.runtime, self.config_proposal(), once=True)
        journals = list((self.root/'.rd-platform/proposal-journal').glob('*.json'))
        self.assertEqual('COMMITTED', json.loads(journals[0].read_text())['state'])
