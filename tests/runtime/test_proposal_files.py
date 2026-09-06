"""Host proposal-file batch journal contracts (CR-V3-004)."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from rd_platform.proposal_files import apply, commit, prepare, recover


class ProposalFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "src").mkdir()
        self.source = self.root / "src" / "existing.txt"
        self.source.write_text("old", encoding="utf-8")
        self.allowlist = ["src/existing.txt", "src/new.txt"]

    def tearDown(self):
        self.temp.cleanup()

    def proposal(self, *, action="update", path="src/existing.txt", content="new", expected=None):
        if expected is None and action == "update": expected = hashlib.sha256(self.source.read_bytes()).hexdigest()
        return {"action": action, "id": "DOC-PROPOSAL", "type": "DOC", "title": "proposal",
                "relative_path": path, "content": content, "expected_sha256": expected}

    def test_batch_validates_all_before_writing_any_file(self):
        bad = self.proposal(action="create", path="src/new.txt", content="new", expected="not-null")
        with self.assertRaisesRegex(ValueError, "create"):
            prepare(self.root, [self.proposal(), bad], self.allowlist)
        self.assertEqual("old", self.source.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "src" / "new.txt").exists())

    def test_apply_is_cas_guarded_and_commit_preserves_exact_artifact_refs(self):
        journal, changes = prepare(self.root, [self.proposal()], self.allowlist)
        self.assertEqual("PREPARED", __import__("json").loads(journal.read_text())["state"])
        applied = apply(journal)
        self.assertEqual("APPLIED", applied["state"])
        self.assertEqual("new", self.source.read_text(encoding="utf-8"))
        committed = commit(journal, [{"type": "DOC", "id": "DOC-PROPOSAL", "version": 1}])
        self.assertEqual("COMMITTED", committed["state"])
        recovered = recover(journal, lambda record: record["artifact_refs"] == [{"type": "DOC", "id": "DOC-PROPOSAL", "version": 1}])
        self.assertEqual("COMMITTED", recovered["state"])
        self.assertEqual("new", self.source.read_text(encoding="utf-8"))

    def test_recovery_without_sqlite_commit_restores_original_bytes(self):
        journal, _ = prepare(self.root, [self.proposal()], self.allowlist)
        apply(journal)
        recovered = recover(journal, lambda _record: False)
        self.assertEqual("ROLLED_BACK", recovered["state"])
        self.assertEqual("old", self.source.read_text(encoding="utf-8"))

    def test_recovery_repairs_crash_after_atomic_replace_before_applied_journal_save(self):
        journal, changes = prepare(self.root, [self.proposal()], self.allowlist)
        # Simulates a process dying after os.replace but before `applied=True`
        # is durably saved. Recovery must inspect bytes, not trust that flag.
        self.source.write_bytes(__import__("base64").b64decode(changes[0]["new_b64"]))
        recovered = recover(journal, lambda _record: False)
        self.assertEqual("ROLLED_BACK", recovered["state"])
        self.assertEqual("old", self.source.read_text(encoding="utf-8"))

    def test_nested_new_directory_is_recorded_and_removed_on_uncommitted_recovery(self):
        proposal = self.proposal(action="create", path="docs/generated/new.txt", content="new", expected=None)
        journal, _ = prepare(self.root, [proposal], ["docs/generated/new.txt"])
        apply(journal)
        self.assertTrue((self.root / "docs" / "generated" / "new.txt").is_file())
        recover(journal, lambda _record: False)
        self.assertFalse((self.root / "docs").exists())

    def test_recovery_keeps_applied_files_only_when_sqlite_returns_exact_refs(self):
        journal, _ = prepare(self.root, [self.proposal()], self.allowlist)
        apply(journal)
        refs = [{"type": "DOC", "id": "DOC-PROPOSAL", "version": 7}]
        recovered = recover(journal, lambda _record: refs)
        self.assertEqual("COMMITTED", recovered["state"])
        self.assertEqual(refs, recovered["artifact_refs"])
        self.assertEqual("new", self.source.read_text(encoding="utf-8"))

    def test_recovery_refuses_external_drift_instead_of_overwriting(self):
        journal, _ = prepare(self.root, [self.proposal()], self.allowlist)
        apply(journal)
        self.source.write_text("external", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "external drift"):
            recover(journal, lambda _record: False)
        self.assertEqual("external", self.source.read_text(encoding="utf-8"))

    def test_links_control_paths_duplicates_and_cas_mismatch_are_rejected(self):
        link = self.root / "src" / "linked.txt"
        try:
            link.symlink_to(self.source)
        except OSError:
            link = None
        if link is not None:
            with self.assertRaisesRegex(ValueError, "link"):
                prepare(self.root, [self.proposal(path="src/linked.txt")], ["src/linked.txt"])
        with self.assertRaisesRegex(ValueError, "control"):
            prepare(self.root, [self.proposal(path=".rd-platform/state.json")], [".rd-platform/state.json"])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            prepare(self.root, [self.proposal(), self.proposal()], self.allowlist)
        alias = self.proposal(path="src/EXISTING.txt")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            prepare(self.root, [self.proposal(), alias], self.allowlist + ["src/EXISTING.txt"])
        with self.assertRaisesRegex(ValueError, "CAS"):
            prepare(self.root, [self.proposal(expected="0" * 64)], self.allowlist)

    @unittest.skipUnless(__import__("os").name == "nt", "Windows junction fixture")
    def test_proposal_journal_control_directory_junction_is_rejected(self):
        import subprocess
        outside = self.root.parent / (self.root.name + "-journal-outside")
        outside.mkdir(); linked = self.root / ".rd-platform"
        made = subprocess.run(["cmd", "/c", "mklink", "/J", str(linked), str(outside)], capture_output=True)
        if made.returncode: self.skipTest("host cannot create junction")
        try:
            with self.assertRaisesRegex(ValueError, "journal control directory"):
                prepare(self.root, [self.proposal()], self.allowlist)
        finally:
            subprocess.run(["cmd", "/c", "rmdir", str(linked)], capture_output=True)
            outside.rmdir()
