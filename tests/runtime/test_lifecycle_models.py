"""TC-V3-321..325 / REQ-V3-002,005,009: test-model provenance/versioning."""
import tempfile
import unittest
from pathlib import Path

from rd_platform.lifecycle import LifecycleService
from rd_platform.runtime import Runtime


class LifecycleModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = Runtime(self.root / 'state.db')
        self.project = self.runtime.execute('project.create', {'name': 'model', 'idea': 'versioned test model'})['id']
        self.other = self.runtime.execute('project.create', {'name': 'other', 'idea': 'isolated model'})['id']
        for ident, role in (('dev', 'developer'), ('tester', 'tester')):
            self.runtime.execute('agent.register', {'id': ident, 'role': role})
        for project in (self.project, self.other):
            self.runtime.execute('lifecycle.initialize', {'project_id': project, 'repository_root': str(self.root), 'mode': 'active'})
        self.requirement('REQ-321')

    def tearDown(self):
        self.temp.cleanup()

    def requirement(self, ident, project=None):
        return self.runtime.execute('artifact.create', {'project_id': project or self.project, 'artifact_type': 'REQ',
            'artifact_id': ident, 'title': ident, 'state': 'BASELINED', 'content_ref': {'inline_json': {'criterion': ident}},
            'source': {'kind': 'host', 'actor': 'dev'}})

    def model_data(self, **changes):
        data = {'project_id': self.project, 'artifact_id': 'TM-321', 'source': {'kind': 'host', 'actor': 'tester'},
            'requirement_refs': ['REQ-321'], 'function_tree': {'name': 'input', 'children': ['validation']},
            'risks': [{'risk_id': 'RISK-321', 'description': 'invalid input', 'likelihood': 'HIGH', 'impact': 'HIGH', 'priority': 'P0', 'requirement_refs': ['REQ-321']}],
            'objects': [{'object_id': 'OBJ-321', 'description': 'public input'}], 'types': ['FUNCTIONAL'],
            'test_points': [{'point_id': 'TP-321', 'object_id': 'OBJ-321', 'type': 'FUNCTIONAL', 'rationale': 'risk coverage', 'risk_refs': ['RISK-321'], 'requirement_refs': ['REQ-321'], 'coverage_rule': 'valid and invalid'}]}
        data.update(changes)
        return data

    def create_case(self, model_id='TM-321'):
        return self.runtime.execute('test_case.create', {'project_id': self.project, 'case_id': 'TC-321', 'test_model_id': model_id,
            'test_point_refs': ['TP-321'], 'requirement_refs': ['REQ-321'], 'test_type': 'FUNCTIONAL', 'module': 'input',
            'priority': 'P0', 'risk': 'HIGH', 'preconditions': [], 'test_data': {},
            'steps': [{'order': 1, 'action': 'submit', 'expected_observation': 'validation'}],
            'expected_result': 'valid result', 'automation': {'status': 'MANUAL'}, 'state': 'BASELINED'})

    def test_tc_v3_321_create_requires_explicit_provenance_and_creates_artifact_history(self):
        with self.assertRaisesRegex(ValueError, 'source provenance required'):
            self.runtime.execute('test_model.create', self.model_data(source=None))
        created = self.runtime.execute('test_model.create', self.model_data())
        self.assertEqual((1, 'BASELINED', 'tester'), (created['version'], created['state'], created['source']['actor']))
        snapshot = self.runtime.lifecycle_snapshot(self.project)
        backing = next(a for a in snapshot['artifacts'] if a['id'] == 'TM-321')
        self.assertEqual(('TEST_MODEL', 1, created['source']), (backing['artifact_type'], backing['version'], backing['source']))
        with self.runtime.store.transaction(write=False) as connection:
            self.assertEqual(1, connection.execute('SELECT COUNT(*) FROM lc_artifact_versions WHERE artifact_id=?', ('TM-321',)).fetchone()[0])
        with self.assertRaisesRegex(ValueError, 'use test_model.create'):
            self.runtime.execute('artifact.create', {'project_id': self.project, 'artifact_type': 'TEST_MODEL', 'artifact_id': 'TM-BARE-321',
                'title': 'bypass', 'state': 'BASELINED', 'content_ref': {'inline_json': {}}, 'source': {'kind': 'host', 'actor': 'tester'}})

    def test_tc_v3_322_material_revision_is_append_only_and_invalidates_case(self):
        self.runtime.execute('test_model.create', self.model_data())
        self.create_case()
        self.runtime.execute('artifact.create', {'project_id': self.project, 'artifact_type': 'CR', 'artifact_id': 'CR-321', 'title': 'model change',
            'state': 'BASELINED', 'content_ref': {'inline_json': {'reason': 'coverage change'}}, 'source': {'kind': 'host', 'actor': 'dev'}})
        with self.assertRaisesRegex(ValueError, 'requires CR'):
            self.runtime.execute('test_model.revise', self.model_data(expected_version=1, reason='coverage change'))
        revised = self.runtime.execute('test_model.revise', self.model_data(expected_version=1, reason='coverage change', change_id='CR-321', material=True,
            function_tree={'name': 'input', 'children': ['validation', 'recovery']}))
        self.assertEqual(2, revised['version'])
        with self.assertRaisesRegex(ValueError, 'use test_model.revise'):
            self.runtime.execute('artifact.revise', {'artifact_id': 'TM-321', 'expected_version': 2, 'state': 'BASELINED',
                'content_ref': {'inline_json': {}}, 'reason': 'bypass', 'change_id': 'CR-321'})
        snapshot = self.runtime.lifecycle_snapshot(self.project)
        case = next(c for c in snapshot['test_cases'] if c['id'] == 'TC-321')
        self.assertEqual(('REVIEW_REQUIRED', 1), (case['status'], case['test_model_version']))
        with self.assertRaisesRegex(ValueError, 'stale or needs review'):
            self.runtime.execute('test_execution.start', {'case_id': 'TC-321', 'case_version': 1, 'executor_id': 'tester',
                'environment_ref': {'type': 'EVIDENCE', 'id': 'EVD-missing', 'version': 1}})
        revised_case = self.runtime.execute('test_case.revise', {'case_id': 'TC-321', 'expected_version': 1, 'reason': 'align with test model'})
        self.assertEqual((2, 2), (revised_case['version'], revised_case['test_model_version']))
        with self.runtime.store.transaction(write=False) as connection:
            self.assertEqual(2, connection.execute('SELECT COUNT(*) FROM lc_artifact_versions WHERE artifact_id=?', ('TM-321',)).fetchone()[0])

    def test_tc_v3_323_cross_project_requirement_is_rejected(self):
        self.requirement('REQ-OTHER-321', self.other)
        with self.assertRaises(ValueError):
            self.runtime.execute('test_model.create', self.model_data(requirement_refs=['REQ-OTHER-321']))

    def test_tc_v3_324_obsolete_model_cannot_create_case(self):
        self.runtime.execute('test_model.create', self.model_data(state='OBSOLETE'))
        with self.assertRaisesRegex(ValueError, 'test model'):
            self.create_case()

    def test_tc_v3_325_legacy_model_is_readable_but_requires_explicit_adoption(self):
        legacy = self.model_data()
        legacy.pop('source')
        legacy.update(id='TM-LEGACY-321', artifact_id='TM-LEGACY-321', version=1, status='CURRENT')
        with self.runtime.store.transaction() as connection:
            LifecycleService().put(connection, 'test_models', legacy, new=True)
        self.assertEqual('TM-LEGACY-321', self.runtime.lifecycle_snapshot(self.project)['test_models'][0]['id'])
        with self.assertRaisesRegex(ValueError, 'lacks current artifact provenance'):
            self.create_case('TM-LEGACY-321')
        with self.assertRaisesRegex(ValueError, 'lacks artifact provenance'):
            self.runtime.execute('test_model.revise', dict(legacy, expected_version=1, reason='unproven history'))
        adopted = self.runtime.execute('test_model.adopt', {'artifact_id': 'TM-LEGACY-321', 'expected_version': 1,
            'reason': 'tester verified imported model identity', 'source': {'kind': 'host', 'actor': 'tester'}, 'state': 'BASELINED'})
        self.assertEqual((2, 'NOT_AVAILABLE', 'tester'), (adopted['version'], adopted['legacy_source_status'], adopted['source']['actor']))
        with self.runtime.store.transaction(write=False) as connection:
            self.assertEqual(2, connection.execute('SELECT COUNT(*) FROM lc_artifact_versions WHERE artifact_id=?', ('TM-LEGACY-321',)).fetchone()[0])


if __name__ == '__main__':
    unittest.main()
