import tempfile
import unittest
from pathlib import Path

from rd_platform.runtime import Runtime


class ExecutionBoardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.r = Runtime(Path(self.tmp.name) / 'state.db')
        self.p = self.r.execute('project.create', {'name': 'Board', 'idea': 'Actual work'})['id']
        self.r.execute('agent.register', {'id': 'worker', 'role': 'developer'})
        self.r.execute('lifecycle.initialize', {'project_id': self.p, 'repository_root': self.tmp.name, 'mode': 'active'})

    def work(self):
        return self.r.execute('work.create', {'project_id': self.p, 'gate_id': 'G6',
            'activity': 'Implement input validation', 'why': 'Reject invalid data',
            'required_role': 'developer', 'input_refs': [], 'dependencies': [],
            'output_contract': {'required_types': [], 'min_outputs': 0}})

    def test_claim_is_visible_without_fabricated_v2_run(self):
        w = self.work()
        self.r.execute('work.claim', {'work_order_id': w['id'], 'agent_id': 'worker'})
        s = self.r.snapshot(self.p)
        a = s['agents'][0]
        self.assertEqual('WORKING', a['effective_status'])
        self.assertEqual(w['id'], a['current_work']['id'])
        self.assertEqual('Reject invalid data', a['current_work']['why'])
        self.assertNotIn('lease_digest', str(a))
        self.assertNotIn('lease_token', str(a))
        self.assertEqual([], s['runs'])
        self.assertIsNone(a['current_work']['progress_percent'])

    def test_completed_work_and_handoff_not_claimed_as_active(self):
        w = self.work()
        claim = self.r.execute('work.claim', {'work_order_id': w['id'], 'agent_id': 'worker'})
        self.r.execute('work.finish', {'work_order_id': w['id'], 'agent_id': 'worker',
            'lease_token': claim['lease_token'], 'status': 'DONE', 'summary': 'Actual result', 'output_refs': []})
        a = self.r.snapshot(self.p)['agents'][0]
        self.assertEqual('DONE', a['effective_status'])
        self.assertEqual(100, a['current_work']['progress_percent'])

    def test_other_project_work_is_not_misattributed(self):
        self.r.execute('work.claim', {'work_order_id': self.work()['id'], 'agent_id': 'worker'})
        other = self.r.execute('project.create', {'name': 'Other', 'idea': 'Separate'})['id']
        a = self.r.snapshot(other)['agents'][0]
        self.assertIsNone(a['current_work'])
        self.assertEqual('IDLE', a['effective_status'])

    def test_expired_lease_does_not_show_working(self):
        w = self.work()
        self.r.execute('work.claim', {'work_order_id': w['id'], 'agent_id': 'worker'})
        from unittest.mock import patch
        with patch.object(Runtime, '_now', return_value='2999-01-01T00:00:00+00:00'):
            a = self.r.snapshot(self.p)['agents'][0]
        self.assertEqual('BLOCKED', a['effective_status'])
        self.assertIn('expired', a['current_work']['blocked_reason'])

    def test_explicit_waiting_user_resume_does_not_approve_gates(self):
        w = self.work()
        claim = self.r.execute('work.claim', {'work_order_id': w['id'], 'agent_id': 'worker'})
        self.r.execute('work.finish', {'work_order_id': w['id'], 'agent_id': 'worker',
            'lease_token': claim['lease_token'], 'status': 'WAITING_USER', 'summary': 'Need a real decision', 'output_refs': []})
        self.r.execute('lifecycle.control', {'project_id': self.p, 'action': 'resume', 'reason': 'Continue analysis; not acceptance'})
        self.r.execute('work.control', {'work_order_id': w['id'], 'action': 'retry', 'reason': 'Use the supplied clarification'})
        self.r.execute('work.claim', {'work_order_id': w['id'], 'agent_id': 'worker'})
        s = self.r.lifecycle_snapshot(self.p)
        self.assertEqual('ACTIVE', s['lifecycle']['state'])
        self.assertFalse(s['gate_decisions'])
