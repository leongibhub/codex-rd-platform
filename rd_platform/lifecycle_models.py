"""Versioned test-model definitions backed by TEST_MODEL artifacts.

Each current test-model row has the same identifier and version as its
immutable TEST_MODEL artifact version.  This deliberately leaves legacy
unbacked rows readable, but refuses to promote or revise them without a
separate, evidenced adoption workflow.
"""
from .store import Store
from .lifecycle_base import STATES
from .lifecycle_testing import TEST_TYPES


class TestModelCommands:
    def _test_model_definition(self, c, d, *, project=None):
        p = project or self.project(c, d.get('project_id'))['id']
        refs = self.requirement_refs(c, p, d.get('requirement_refs'))
        tree = d.get('function_tree')
        if not isinstance(tree, (dict, list)) or not tree:
            raise ValueError('function_tree required')
        risks, points, objects = d.get('risks'), d.get('test_points'), d.get('objects')
        if not isinstance(risks, list) or not risks or not isinstance(points, list) or not points or not isinstance(objects, list) or not objects:
            raise ValueError('risks, objects and test points required')
        types = self.strings(d.get('types'), 'test types')
        for typ in types:
            self.enum(typ, TEST_TYPES, 'test type')
        object_ids = []
        for obj in objects:
            if not isinstance(obj, dict):
                raise ValueError('test objects must have object_id and description')
            object_ids.append(self.text(obj.get('object_id'), 'object_id'))
            self.text(obj.get('description'), 'object description')
        if len(set(object_ids)) != len(object_ids):
            raise ValueError('duplicate object id')
        reqids, riskids = {r['id'] for r in refs}, []
        for risk in risks:
            if not isinstance(risk, dict):
                raise ValueError('risk must be object')
            riskids.append(self.text(risk.get('risk_id'), 'risk_id'))
            self.text(risk.get('description'), 'risk description')
            self.enum(risk.get('likelihood'), {'LOW', 'MEDIUM', 'HIGH'}, 'risk likelihood')
            self.enum(risk.get('impact'), {'LOW', 'MEDIUM', 'HIGH'}, 'risk impact')
            self.enum(risk.get('priority'), {'P0', 'P1', 'P2', 'P3'}, 'risk priority')
            if not {r['id'] for r in self.requirement_refs(c, p, risk.get('requirement_refs'))} <= reqids:
                raise ValueError('risk references outside model')
        if len(set(riskids)) != len(riskids):
            raise ValueError('duplicate risk id')
        pointids = []
        for point in points:
            if not isinstance(point, dict):
                raise ValueError('point must be object')
            pointids.append(self.text(point.get('point_id'), 'point_id'))
            if point.get('object_id') not in object_ids or point.get('type') not in types:
                raise ValueError('unknown point object or test type')
            for field in ('rationale', 'coverage_rule'):
                self.text(point.get(field), field)
            if not set(self.strings(point.get('risk_refs'), 'risk_refs')) <= set(riskids):
                raise ValueError('unknown risk reference')
            if not {r['id'] for r in self.requirement_refs(c, p, point.get('requirement_refs'))} <= reqids:
                raise ValueError('point requirement outside model')
        if len(set(pointids)) != len(pointids):
            raise ValueError('duplicate point id')
        return dict(project_id=p, requirement_refs=refs, function_tree=tree, risks=risks,
                    objects=objects, types=types, test_points=points)

    @staticmethod
    def _model_content(model):
        return {key: model[key] for key in ('requirement_refs', 'function_tree', 'risks', 'objects', 'types', 'test_points')}

    def test_model_create(self, c, d):
        model = self._test_model_definition(c, d)
        ident = self.text(d.get('artifact_id'), 'artifact_id')
        if not ident.startswith('TM-'):
            raise ValueError('test model id must start TM-')
        source = self.source(c, d.get('source'))
        state = self.enum(d.get('state', 'BASELINED'), STATES, 'test model state')
        model.update(id=ident, artifact_id=ident, version=1, state=state, status='CURRENT',
                     source=source, created_by=source['actor'], created_at=self.now())
        artifact = dict(id=ident, artifact_id=ident, project_id=model['project_id'], artifact_type='TEST_MODEL',
                        title=self.text(d.get('title', ident), 'title'), version=1, state=state,
                        content_ref=self.content(c, model['project_id'], {'inline_json': self._model_content(model)}),
                        source=source, created_by=source['actor'], created_at=model['created_at'])
        self.put(c, 'artifacts', artifact, new=True)
        c.execute('INSERT INTO lc_artifact_versions VALUES (?,?,?)', (ident, 1, Store.dumps(artifact)))
        self.put(c, 'test_models', model, new=True)
        self.event(c, model['project_id'], 'test_model.created', ident, {'version': 1, 'artifact_id': ident})
        return model

    def test_model_revise(self, c, d):
        old = self.get(c, 'test_models', d.get('artifact_id'))
        if old.get('artifact_id') != old['id'] or not old.get('source') or not c.execute('SELECT 1 FROM lc_artifacts WHERE id=?', (old['id'],)).fetchone():
            raise ValueError('legacy test model lacks artifact provenance; explicit evidenced adoption required')
        if self.integer(d.get('expected_version'), 'expected_version') != old['version']:
            raise ValueError('test model revision conflict')
        reason = self.text(d.get('reason'), 'reason')
        material = d.get('material', True)
        if type(material) is not bool:
            raise ValueError('material must be boolean')
        change = d.get('change_id')
        if material and not change:
            raise ValueError('material revision requires CR')
        if change:
            self.ref(c, old['project_id'], {'type': 'CR', 'id': change})
        artifact = self.get(c, 'artifacts', old['artifact_id'])
        if artifact['artifact_type'] != 'TEST_MODEL' or artifact['version'] != old['version']:
            raise ValueError('test model artifact/version mismatch')
        model = self._test_model_definition(c, dict(old, **d), project=old['project_id'])
        source = self.source(c, d['source']) if 'source' in d else old['source']
        state = self.enum(d.get('state', old.get('state', artifact['state'])), STATES, 'test model state')
        model.update(id=old['id'], artifact_id=old['artifact_id'], version=old['version'] + 1, state=state,
                     status='CURRENT', source=source, created_by=source['actor'], created_at=self.now(),
                     reason=reason, change_id=change)
        revised_artifact = dict(artifact, version=model['version'], state=state,
                                content_ref=self.content(c, old['project_id'], {'inline_json': self._model_content(model)}),
                                source=source, created_by=source['actor'], created_at=model['created_at'],
                                reason=reason, change_id=change)
        self.put(c, 'artifacts', revised_artifact)
        c.execute('INSERT INTO lc_artifact_versions VALUES (?,?,?)',
                  (revised_artifact['id'], revised_artifact['version'], Store.dumps(revised_artifact)))
        self.put(c, 'test_models', model)
        affected = self._invalidate_model_dependents(c, old, reason, change)
        self.event(c, old['project_id'], 'test_model.revised', old['id'],
                   {'version': model['version'], 'reason': reason, 'affected': sorted(affected)})
        return model

    def test_model_adopt(self, c, d):
        """Explicitly attach a legacy model to immutable artifact history.

        Adoption records who now vouches for the imported definition.  It never
        claims that person created the legacy v1 definition.
        """
        old = self.get(c, 'test_models', d.get('artifact_id'))
        if old.get('source') or c.execute('SELECT 1 FROM lc_artifacts WHERE id=?', (old['id'],)).fetchone():
            raise ValueError('test model already has artifact provenance')
        if self.integer(d.get('expected_version'), 'expected_version') != old.get('version', 1):
            raise ValueError('test model adoption conflict')
        reason = self.text(d.get('reason'), 'reason')
        source = self.source(c, d.get('source'))
        state = self.enum(d.get('state', 'BASELINED'), STATES, 'test model state')
        body = self._test_model_definition(c, old, project=old['project_id'])
        ident = old['id']
        if c.execute('SELECT 1 FROM lc_artifacts WHERE id=?', (ident,)).fetchone():
            raise ValueError('legacy test model artifact id is already occupied')
        imported_source = dict(source, original_source_status='NOT_AVAILABLE')
        imported_artifact = dict(id=ident, artifact_id=ident, project_id=old['project_id'], artifact_type='TEST_MODEL',
                                 title=self.text(d.get('title', ident), 'title'), version=1, state='OBSOLETE',
                                 content_ref=self.content(c, old['project_id'], {'inline_json': self._model_content(body)}),
                                 source=imported_source, created_by=source['actor'], created_at=old.get('created_at', self.now()),
                                 legacy_source_status='NOT_AVAILABLE', adopted_at=self.now())
        self.put(c, 'artifacts', imported_artifact, new=True)
        c.execute('INSERT INTO lc_artifact_versions VALUES (?,?,?)', (ident, 1, Store.dumps(imported_artifact)))
        model = dict(body, id=ident, artifact_id=ident, version=2, state=state, status='CURRENT', source=source,
                     created_by=source['actor'], created_at=self.now(), reason=reason, adopted_from_version=old.get('version', 1),
                     legacy_source_status='NOT_AVAILABLE', adopted_at=self.now())
        artifact = dict(imported_artifact, version=2, state=state,
                        content_ref=self.content(c, old['project_id'], {'inline_json': self._model_content(model)}),
                        source=source, created_by=source['actor'], created_at=model['created_at'], reason=reason)
        self.put(c, 'artifacts', artifact)
        c.execute('INSERT INTO lc_artifact_versions VALUES (?,?,?)', (ident, 2, Store.dumps(artifact)))
        self.put(c, 'test_models', model)
        affected = self._invalidate_model_dependents(c, old, reason, None)
        self.event(c, old['project_id'], 'test_model.adopted', ident,
                   {'version': 2, 'reason': reason, 'legacy_source_status': 'NOT_AVAILABLE', 'affected': sorted(affected)})
        return model

    def _invalidate_model_dependents(self, c, old, reason, change):
        affected = set(self.invalidate(c, old['project_id'], {'type': 'TEST_MODEL', 'id': old['id'], 'version': old.get('version', 1)}, reason, change))
        for case in self.rows(c, 'test_cases', old['project_id']):
            if case.get('test_model_id') == old['id']:
                case['status'] = 'REVIEW_REQUIRED'
                self.put(c, 'test_cases', case)
                affected.update(self.invalidate(c, old['project_id'], {'type': 'TEST_CASE', 'id': case['id'], 'version': case['version']}, reason, change))
        return affected
