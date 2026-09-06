"""Independent public-contract checks for source-bound test-model versions."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from rd_platform.lifecycle import LifecycleService
from rd_platform.runtime import Runtime


class IndependentLifecycleModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ind-v3-model-")
        self.root = Path(self.temp.name); self.runtime = Runtime(self.root / "state.db")
        self.project = self.runtime.execute("project.create", {"name":"ind model", "idea":"version contract"})["id"]
        self.runtime.execute("agent.register", {"id":"ind-model-dev", "role":"developer"})
        self.runtime.execute("agent.register", {"id":"ind-model-test", "role":"tester"})
        self.runtime.execute("lifecycle.initialize", {"project_id":self.project,"repository_root":str(self.root),"mode":"active"})
        self.runtime.execute("artifact.create", {"project_id":self.project,"artifact_type":"REQ","artifact_id":"REQ-IND-M","title":"criterion","state":"BASELINED","content_ref":{"inline_json":{"criterion":"observable"}},"source":{"kind":"host","actor":"ind-model-dev"}})
    def tearDown(self): self.temp.cleanup()
    def model(self, **extra):
        d={"project_id":self.project,"artifact_id":"TM-IND-M","source":{"kind":"host","actor":"ind-model-test"},"requirement_refs":["REQ-IND-M"],"function_tree":{"name":"model","children":["validation"]},"risks":[{"risk_id":"RISK-M","description":"stale coverage","likelihood":"HIGH","impact":"HIGH","priority":"P0","requirement_refs":["REQ-IND-M"]}],"objects":[{"object_id":"OBJ-M","description":"public model"}],"types":["FUNCTIONAL"],"test_points":[{"point_id":"TP-M","object_id":"OBJ-M","type":"FUNCTIONAL","rationale":"risk","risk_refs":["RISK-M"],"requirement_refs":["REQ-IND-M"],"coverage_rule":"all"}]}
        d.update(extra); return d
    def case(self):
        return self.runtime.execute("test_case.create", {"project_id":self.project,"case_id":"TC-IND-M","test_model_id":"TM-IND-M","test_point_refs":["TP-M"],"requirement_refs":["REQ-IND-M"],"test_type":"FUNCTIONAL","module":"model","priority":"P0","risk":"HIGH","preconditions":[],"test_data":{},"steps":[{"order":1,"action":"run","expected_observation":"result"}],"expected_result":"result","automation":{"status":"MANUAL"},"state":"BASELINED"})
    def test_tc_v3_ind_501_source_required_and_backing_artifact_is_versioned(self):
        with self.assertRaises(ValueError): self.runtime.execute("test_model.create", self.model(source=None))
        created=self.runtime.execute("test_model.create",self.model()); snap=self.runtime.lifecycle_snapshot(self.project)
        backing=next(x for x in snap["artifacts"] if x["id"]=="TM-IND-M")
        self.assertEqual((1,"ind-model-test"),(created["version"],backing["source"]["actor"]))
    def test_tc_v3_ind_502_material_revision_requires_cr_and_invalidates_case(self):
        self.runtime.execute("test_model.create",self.model()); self.case()
        with self.assertRaises(ValueError): self.runtime.execute("test_model.revise",self.model(expected_version=1,reason="material"))
        self.runtime.execute("artifact.create", {"project_id":self.project,"artifact_type":"CR","artifact_id":"CR-IND-M","title":"change","state":"BASELINED","content_ref":{"inline_json":{}},"source":{"kind":"host","actor":"ind-model-dev"}})
        revised=self.runtime.execute("test_model.revise",self.model(expected_version=1,reason="material",change_id="CR-IND-M",material=True,function_tree={"name":"model","children":["validation","recovery"]}))
        case=next(x for x in self.runtime.lifecycle_snapshot(self.project)["test_cases"] if x["id"]=="TC-IND-M")
        self.assertEqual((2,"REVIEW_REQUIRED",1),(revised["version"],case["status"],case["test_model_version"]))
    def test_tc_v3_ind_503_legacy_model_requires_explicit_source_bound_adoption(self):
        legacy=self.model(); legacy.pop("source"); legacy.update(id="TM-LEGACY-M",artifact_id="TM-LEGACY-M",version=1,status="CURRENT")
        with self.runtime.store.transaction() as c: LifecycleService().put(c,"test_models",legacy,new=True)
        with self.assertRaises(ValueError): self.runtime.execute("test_model.adopt",{"artifact_id":"TM-LEGACY-M","expected_version":1,"reason":"missing source"})
        adopted=self.runtime.execute("test_model.adopt",{"artifact_id":"TM-LEGACY-M","expected_version":1,"reason":"maintainer adopts legacy","source":{"kind":"host","actor":"ind-model-test"},"state":"BASELINED"})
        self.assertEqual((2,"NOT_AVAILABLE","ind-model-test"),(adopted["version"],adopted["legacy_source_status"],adopted["source"]["actor"]))

if __name__ == "__main__": unittest.main(verbosity=2)
