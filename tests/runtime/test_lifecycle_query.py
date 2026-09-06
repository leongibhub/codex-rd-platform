"""Unit contracts for the public lifecycle collection reader.

Traceability: REQ-V3-008, NFR-V3-002, NFR-V3-004; TASK-V3-004.
"""

import base64
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from rd_platform.runtime import Runtime
from rd_platform.store import Store


class LifecycleCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = Runtime(self.root / "state.db")
        self.project = self.runtime.execute("project.create", {"name": "query", "idea": "pagination"})["id"]
        self.other_project = self.runtime.execute("project.create", {"name": "other", "idea": "isolation"})["id"]
        for project in (self.project, self.other_project):
            self.runtime.execute("lifecycle.initialize", {"project_id": project, "repository_root": str(self.root), "mode": "active"})

    def tearDown(self):
        self.temp.cleanup()

    def _insert_artifacts(self, project_id, count, prefix="REQ-PAGE"):
        with self.runtime.store.transaction() as connection:
            for number in range(count):
                item = {"id": f"{prefix}-{number:04d}", "project_id": project_id, "artifact_type": "REQ", "version": 1,
                        "state": "BASELINED", "content_ref": {"inline_json": {"fixture": number}, "sha256": "fixture"},
                        "created_at": "2026-09-06T00:00:00+00:00"}
                connection.execute("INSERT INTO lc_artifacts VALUES (?,?,?,?)", (item["id"], project_id, "BASELINED", Store.dumps(item)))

    def test_artifact_pagination_over_500_has_no_duplicate_or_omitted_rows(self):
        self._insert_artifacts(self.project, 501)
        cursor = None
        seen = []
        while True:
            page = self.runtime.lifecycle_collection(self.project, "artifacts", limit=73, after_cursor=cursor)
            self.assertEqual("lifecycle-collection-v1", page["schema_version"])
            self.assertEqual(501, page["total"])
            seen.extend(item["id"] for item in page["items"])
            if not page["has_more"]:
                self.assertIsNone(page["next_cursor"])
                break
            self.assertIsInstance(page["next_cursor"], str)
            cursor = page["next_cursor"]
        self.assertEqual(501, len(seen))
        self.assertEqual(501, len(set(seen)))
        self.assertEqual([f"REQ-PAGE-{number:04d}" for number in range(501)], seen)

    def test_cursor_and_rows_are_bound_to_the_requested_project(self):
        self._insert_artifacts(self.project, 2, "REQ-FIRST")
        self._insert_artifacts(self.other_project, 1, "REQ-OTHER")
        first = self.runtime.lifecycle_collection(self.project, "artifacts", limit=1)
        self.assertEqual(["REQ-FIRST-0000"], [item["id"] for item in first["items"]])
        with self.assertRaises(ValueError):
            self.runtime.lifecycle_collection(self.other_project, "artifacts", limit=1, after_cursor=first["next_cursor"])
        other = self.runtime.lifecycle_collection(self.other_project, "artifacts", limit=500)
        self.assertEqual(["REQ-OTHER-0000"], [item["id"] for item in other["items"]])

    def test_rejects_non_whitelisted_collection_and_invalid_pagination(self):
        def cursor(data):
            return "lc1." + base64.urlsafe_b64encode(Store.dumps(data).encode("utf-8")).decode("ascii").rstrip("=")

        for collection, limit, value in (("projects", 1, None), ("sqlite_master", 1, None), ("artifacts", True, None),
                                          ("artifacts", 0, None), ("artifacts", 501, None), ("artifacts", 1, "not-a-cursor"),
                                          ("artifacts", 1, cursor({"v": True, "project_id": self.project, "collection": "artifacts", "after": 0})),
                                          ("artifacts", 1, cursor({"v": 1, "project_id": self.project, "collection": "artifacts", "after": 2 ** 63})),
                                          ("artifacts", 1, cursor({"v": 1, "project_id": self.project, "collection": "artifacts", "after": 0, "extra": "no"})),
                                          ("artifacts", 1, "lc1." + "a" * 1025)):
            with self.subTest(collection=collection, limit=limit, cursor=value), self.assertRaises(ValueError):
                self.runtime.lifecycle_collection(self.project, collection, limit=limit, after_cursor=value)

    def test_public_rows_do_not_expose_internal_digests_or_unredacted_secrets(self):
        with self.runtime.store.transaction() as connection:
            row = {"id": "release-public", "project_id": self.project, "status": "DRAFT", "release_digest": "internal-only",
                   "notes": "authorization=Bearer fixture-secret"}
            connection.execute("INSERT INTO lc_releases VALUES (?,?,?,?)", (row["id"], self.project, "DRAFT", Store.dumps(row)))
        page = self.runtime.lifecycle_collection(self.project, "releases", limit=1)
        self.assertNotIn("release_digest", page["items"][0])
        self.assertNotIn("fixture-secret", str(page))

    def test_cli_parser_and_loopback_http_reject_duplicate_or_invalid_query_fields(self):
        from rd_platform.cli import build_parser
        from rd_platform.web import create_server

        args = build_parser().parse_args(["lifecycle-collection", "--project-id", self.project, "artifacts", "--limit", "1"])
        self.assertEqual("lifecycle-collection", args.operation)
        server = create_server(self.root / "state.db", port=0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            connection = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
            connection.request("GET", f"/api/lifecycle/collection?project_id={self.project}&collection=artifacts&limit=1")
            response = connection.getresponse()
            self.assertEqual(200, response.status)
            response.read()
            connection.request("GET", f"/api/lifecycle/collection?project_id={self.project}&collection=artifacts&collection=releases")
            response = connection.getresponse()
            self.assertEqual(400, response.status)
            response.read()
            connection.request("GET", f"/api/lifecycle/collection?project_id={self.project}&collection=artifacts&limit=-1")
            response = connection.getresponse()
            self.assertEqual(400, response.status)
            response.read()
            connection.request("GET", f"/api/lifecycle/collection?project_id={self.project}&collection=artifacts&after_cursor=lc1.{ 'a' * 1025}")
            response = connection.getresponse()
            self.assertEqual(400, response.status)
            response.read()
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
