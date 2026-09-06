"""Independent public-API tests for bounded lifecycle collection paging."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import tempfile
import unittest

from rd_platform.runtime import Runtime


class IndependentLifecycleQueryTests(unittest.TestCase):
    """TC-V3-IND-401..403 / REQ-V3-008 / NFR-V3-002,004."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ind-v3-query-")
        self.root = Path(self.temp.name)
        self.runtime = Runtime(self.root / "state.db")
        self.project = self.runtime.execute("project.create", {"name": "public collection", "idea": "independent pagination"})["id"]
        self.other = self.runtime.execute("project.create", {"name": "isolated collection", "idea": "cursor isolation"})["id"]
        self.runtime.execute("agent.register", {"id": "ind-query-dev", "role": "developer"})
        for project in (self.project, self.other):
            self.runtime.execute("lifecycle.initialize", {"project_id": project, "repository_root": str(self.root), "mode": "active"})

    def tearDown(self):
        self.temp.cleanup()

    def create_artifact(self, project, number, prefix="REQ-PUBLIC"):
        return self.runtime.execute("artifact.create", {
            "project_id": project, "artifact_id": f"{prefix}-{number:04d}", "artifact_type": "REQ",
            "title": "observable pagination item", "state": "BASELINED",
            "content_ref": {"inline_json": {"item": number}},
            "source": {"kind": "host", "actor": "ind-query-dev"},
        })

    def test_tc_v3_ind_401_public_api_reads_501_items_without_gap_or_duplicate(self):
        for number in range(501):
            self.create_artifact(self.project, number)
        cursor = None
        observed = []
        while True:
            page = self.runtime.lifecycle_collection(self.project, "artifacts", limit=73, after_cursor=cursor)
            self.assertEqual("lifecycle-collection-v1", page["schema_version"])
            self.assertEqual(501, page["total"])
            self.assertLessEqual(len(page["items"]), 73)
            observed.extend(item["id"] for item in page["items"])
            if not page["has_more"]:
                self.assertIsNone(page["next_cursor"])
                break
            cursor = page["next_cursor"]
            self.assertIsInstance(cursor, str)
        self.assertEqual([f"REQ-PUBLIC-{number:04d}" for number in range(501)], observed)
        self.assertEqual(501, len(set(observed)))

    def test_tc_v3_ind_402_cursor_cannot_cross_project_or_collection(self):
        self.create_artifact(self.project, 1)
        self.create_artifact(self.project, 2)
        self.create_artifact(self.other, 1, prefix="REQ-OTHER")
        cursor = self.runtime.lifecycle_collection(self.project, "artifacts", limit=1)["next_cursor"]
        with self.assertRaises(ValueError):
            self.runtime.lifecycle_collection(self.other, "artifacts", limit=1, after_cursor=cursor)
        with self.assertRaises(ValueError):
            self.runtime.lifecycle_collection(self.project, "evidence", limit=1, after_cursor=cursor)
        other_page = self.runtime.lifecycle_collection(self.other, "artifacts", limit=1)
        self.assertEqual(["REQ-OTHER-0001"], [item["id"] for item in other_page["items"]])

    def test_tc_v3_ind_403_huge_and_tampered_cursor_and_501_limit_rejected(self):
        def cursor(payload):
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            return "lc1." + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

        bad = (
            "lc1." + "a" * 1025,
            "lc1.not_base64!",
            cursor({"v": 1, "project_id": self.project, "collection": "artifacts", "after": 2 ** 63}),
            cursor({"v": 1, "project_id": self.project, "collection": "artifacts", "after": -1}),
            cursor({"v": True, "project_id": self.project, "collection": "artifacts", "after": 0}),
        )
        for value in bad:
            with self.subTest(cursor=value[:16]), self.assertRaises(ValueError):
                self.runtime.lifecycle_collection(self.project, "artifacts", limit=1, after_cursor=value)
        with self.assertRaises(ValueError):
            self.runtime.lifecycle_collection(self.project, "artifacts", limit=501)
        with self.assertRaises(ValueError):
            self.runtime.lifecycle_collection(self.project, "projects", limit=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
