"""REQ-V3-003/004/007: reports do not promote missing or stale evidence."""
import unittest


class LifecycleReportTests(unittest.TestCase):
    def test_empty_project_is_not_test_pass(self):
        from rd_platform.lifecycle_reporting import lifecycle_report
        result = lifecycle_report({'project_id':'p','lifecycle':{},'test_cases':[], 'test_executions':[]})
        self.assertEqual(result['conclusion'], 'CONDITIONAL PASS')
        self.assertFalse(result['recommend_release'])
        self.assertIsNone(result['pass_rate'])

    def test_latest_version_fail_cannot_be_hidden_by_history_pass(self):
        from rd_platform.lifecycle_reporting import lifecycle_report
        result = lifecycle_report({'project_id':'p','test_cases':[{'id':'TC-1','version':2,'test_type':'BOUNDARY'}],
            'test_executions':[{'id':'old','case_id':'TC-1','case_version':1,'result':'PASS'},
                               {'id':'new','case_id':'TC-1','case_version':2,'result':'FAIL'}]})
        self.assertEqual(result['conclusion'], 'FAIL')
        self.assertEqual(result['counts']['FAIL'], 1)
        self.assertEqual(result['historical_execution_counts'], {'PASS':1, 'FAIL':1})

    def test_missing_current_case_and_truncation_prevent_success(self):
        from rd_platform.lifecycle_reporting import lifecycle_report
        result = lifecycle_report({'project_id':'p','test_cases':[{'id':'TC-1','version':2}],
            'test_executions':[{'case_id':'TC-1','case_version':1,'result':'PASS'}],
            'collections_truncated':{'test_cases':True}})
        self.assertEqual(result['counts']['NOT_EXECUTED'], 1)
        self.assertFalse(result['complete_snapshot'])
        self.assertFalse(result['recommend_release'])

    def test_test_pass_does_not_imply_release_or_unrun_test_types(self):
        from rd_platform.lifecycle_reporting import lifecycle_report
        result = lifecycle_report({'project_id':'p','test_cases':[{'id':'TC-1','version':1,'test_type':'FUNCTIONAL'}],
            'test_executions':[{'case_id':'TC-1','case_version':1,'result':'PASS'}]})
        self.assertEqual(result['conclusion'], 'PASS')
        self.assertFalse(result['recommend_release'])
        self.assertEqual(result['test_types']['STABILITY']['status'], 'NOT_EXECUTED')

    def test_failed_or_absent_release_prevents_recommendation(self):
        from rd_platform.lifecycle_reporting import lifecycle_report
        snapshot = {'project_id':'p','test_cases':[{'id':'TC-1','version':1}],
            'test_executions':[{'case_id':'TC-1','case_version':1,'result':'PASS'}],
            'gates':[{'gate_id':f'G{n}','gate_status':'PASS'} for n in range(11)],
            'traceability':[{'requirement_id':'REQ-1','status':'COMPLETE'}]}
        for releases in ([], [{'status':'DEPLOYMENT_FAILED'}], [{'status':'CHANGE_PENDING'}],
                         [{'status':'ROLLED_BACK'}]):
            with self.subTest(releases=releases):
                self.assertFalse(lifecycle_report(dict(snapshot, releases=releases))['recommend_release'])


if __name__ == '__main__':
    unittest.main()
