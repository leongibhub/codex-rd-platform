import tempfile
import unittest
from pathlib import Path
from rd_platform.runtime import Runtime
from rd_platform.orchestration import start_project


class OrchestrationTests(unittest.TestCase):
    def test_repeated_bootstrap_preserves_one_workflow_and_no_approvals(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Runtime(Path(tmp) / 'state.db')
            kwargs = dict(name='Expense tool', idea='Summarize my CSV expenses', repository_root=tmp, request_id='one')
            first = start_project(r, **kwargs)
            again = start_project(r, **kwargs)
            self.assertEqual(first, again)
            s = r.lifecycle_snapshot(first['project_id'])
            self.assertEqual(12, len(s['work_orders']))
            self.assertFalse(s['gate_decisions'])
            self.assertFalse(s['evidence'])
            self.assertTrue(all(g['gate_status'] is None for g in s['gates']))
            with self.assertRaises(ValueError):
                start_project(r, **{**kwargs, 'idea': 'A changed idea'})
