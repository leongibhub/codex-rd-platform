"""Developer tests for the committed-only D-drive transfer contract.

Task: TASK-V3-015
Bug: BUG-INSTALL-001
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
import locale
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "install-to-D.ps1"
CANONICAL_KNOWLEDGE_STUB = (
    "# Local knowledge\n\n"
    "Only commit non-sensitive knowledge that is approved for this repository.\n\n"
    "Do not add credentials, tokens, customer data, private documents, or other restricted material here. "
    "Configure private knowledge directories outside this repository with `COMPANY_LOCAL_ROOTS`.\n"
)
CANONICAL_KNOWLEDGE_BLOB = "f361c8f3bd3b7bb62af25fb46bb48c0965c2e263"


@unittest.skipUnless(shutil.which("powershell"), "requires Windows PowerShell")
class InstallTransferTests(unittest.TestCase):
    """Exercise a tiny committed repository; never target the live workspace."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="rd-platform-install-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        self.root.mkdir()
        (self.root / "scripts").mkdir()
        shutil.copy2(INSTALLER, self.root / "install-to-D.ps1")
        (self.root / "scripts" / "setup.ps1").write_text(
            "Set-Content -LiteralPath (Join-Path $PSScriptRoot '..\\setup-ran.txt') -Value 'ok'\n",
            encoding="utf-8",
        )
        (self.root / "tracked.txt").write_text("committed\n", encoding="utf-8")
        (self.root / ".gitignore").write_text(".env\n.venv/\n.rd-platform/\n", encoding="utf-8")
        (self.root / ".env").write_text("SECRET=must-not-transfer\n", encoding="utf-8")
        (self.root / ".venv").mkdir()
        (self.root / ".venv" / "state.txt").write_text("ignored\n", encoding="utf-8")
        canonical = self.root / "knowledge" / "local" / "README.md"
        canonical.parent.mkdir(parents=True)
        canonical.write_text(CANONICAL_KNOWLEDGE_STUB, encoding="utf-8")
        self._git("init")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "user.name", "Install transfer test")
        self._git("add", "install-to-D.ps1", "scripts/setup.ps1", "tracked.txt", ".gitignore", "knowledge/local/README.md")
        self._git("commit", "-m", "committed delivery")

    def _git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, timeout=20)

    def _run(self, destination: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(self.root / "install-to-D.ps1"), "-Destination", str(destination), *arguments,
            ],
            cwd=self.root,
            capture_output=True,
            timeout=30,
        )

    @staticmethod
    def _output(result: subprocess.CompletedProcess[bytes]) -> str:
        encoding = locale.getpreferredencoding(False)
        return result.stdout.decode(encoding, errors="replace") + result.stderr.decode(encoding, errors="replace")

    def test_transfers_only_committed_tree_and_runs_setup(self) -> None:
        destination = Path(self.temp.name) / "delivered"

        result = self._run(destination)

        self.assertEqual(result.returncode, 0, self._output(result))
        self.assertEqual((destination / "tracked.txt").read_text(encoding="utf-8"), "committed\n")
        self.assertTrue((destination / "setup-ran.txt").is_file())
        self.assertTrue((destination / ".git").is_dir())
        self.assertEqual(
            subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=destination, check=True, capture_output=True, timeout=20).stdout.decode("ascii").strip(),
            "1",
        )
        self.assertEqual(
            subprocess.run(["git", "remote"], cwd=destination, check=True, capture_output=True, timeout=20).stdout.decode("ascii").strip(),
            "",
        )
        self.assertFalse((destination / ".env").exists())
        self.assertFalse((destination / ".venv").exists())
        self.assertFalse((destination / ".rd-platform").exists())
        self.assertEqual((destination / "knowledge" / "local" / "README.md").read_text(encoding="utf-8"), CANONICAL_KNOWLEDGE_STUB)

    def test_rejects_existing_nonempty_destination_without_overwrite(self) -> None:
        destination = Path(self.temp.name) / "existing"
        destination.mkdir()
        protected = destination / "keep.txt"
        protected.write_text("do not overwrite\n", encoding="utf-8")

        result = self._run(destination)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not empty", self._output(result))
        self.assertEqual(protected.read_text(encoding="utf-8"), "do not overwrite\n")

    def test_rejects_force_instead_of_merging_existing_destination(self) -> None:
        destination = Path(self.temp.name) / "existing-force"
        destination.mkdir()
        (destination / "keep.txt").write_text("do not overwrite\n", encoding="utf-8")

        result = self._run(destination, "-Force")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not supported", self._output(result))
        self.assertTrue((destination / "keep.txt").is_file())

    def test_rejects_source_and_descendant_destination(self) -> None:
        for destination in (self.root, self.root / "nested-delivery"):
            with self.subTest(destination=destination):
                result = self._run(destination)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("source", self._output(result).lower())

    def test_rejects_reparse_destination(self) -> None:
        target = Path(self.temp.name) / "reparse-target"
        target.mkdir()
        destination = Path(self.temp.name) / "junction"
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(destination), str(target)],
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(created.returncode, 0, self._output(created))

        result = self._run(destination)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reparse", self._output(result).lower())

    def test_rejects_reparse_source_ancestor(self) -> None:
        source_link = Path(self.temp.name) / "junction-source"
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(source_link), str(self.root)],
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(created.returncode, 0, self._output(created))
        destination = Path(self.temp.name) / "source-link-delivery"

        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(source_link / "install-to-D.ps1"), "-Destination", str(destination),
            ],
            cwd=source_link,
            capture_output=True,
            timeout=30,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source path", self._output(result).lower())

    def test_rejects_each_committed_local_or_cache_path_before_fetch(self) -> None:
        for unsafe_path in (".env", ".worktrees/local", ".pytest_cache/state", "__pycache__/state.pyc", "cache/state"):
            with self.subTest(unsafe_path=unsafe_path):
                path = self.root / unsafe_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("unsafe\n", encoding="utf-8")
                self._git("add", "-f", unsafe_path)
                self._git("commit", "-m", f"unsafe {unsafe_path}")
                destination = Path(self.temp.name) / f"blocked-{len(unsafe_path)}"

                result = self._run(destination)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("delivery-blocked", self._output(result))
                self.assertTrue((destination / ".install-failed").is_file())
                self.assertFalse((destination / "tracked.txt").exists())

    def test_rejects_modified_canonical_knowledge_stub_before_fetch(self) -> None:
        canonical = self.root / "knowledge" / "local" / "README.md"
        canonical.write_text(CANONICAL_KNOWLEDGE_STUB + "modified\n", encoding="utf-8")
        self._git("add", "knowledge/local/README.md")
        self._git("commit", "-m", "modified local knowledge stub")

        result = self._run(Path(self.temp.name) / "modified-stub")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("delivery-blocked", self._output(result))

    def test_rejects_case_variant_of_approved_knowledge_path_before_fetch(self) -> None:
        self._git("mv", "knowledge/local/README.md", "knowledge/local/staging.md")
        self._git("mv", "knowledge/local/staging.md", "knowledge/local/readme.md")
        self._git("commit", "-m", "case variant of local knowledge stub")

        result = self._run(Path(self.temp.name) / "case-variant-stub")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("delivery-blocked", self._output(result))

    def test_rejects_bystander_local_knowledge_file_before_fetch(self) -> None:
        bystander = self.root / "knowledge" / "local" / "notes.md"
        bystander.write_text("not the approved stub\n", encoding="utf-8")
        self._git("add", "knowledge/local/notes.md")
        self._git("commit", "-m", "bystander local knowledge")

        result = self._run(Path(self.temp.name) / "bystander-local")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("delivery-blocked", self._output(result))

    def test_repository_canonical_stub_has_approved_blob_identity(self) -> None:
        blob = subprocess.run(
            ["git", "rev-parse", "HEAD:knowledge/local/README.md"], cwd=ROOT,
            check=True, capture_output=True, timeout=20,
        ).stdout.decode("ascii").strip()

        self.assertEqual(blob, CANONICAL_KNOWLEDGE_BLOB)

    def test_pinned_fetch_and_detached_checkout_are_required_by_contract(self) -> None:
        text = INSTALLER.read_text(encoding="utf-8")

        self.assertIn('rev-parse --verify "HEAD^{commit}"', text)
        self.assertIn('ls-tree -r --name-only $Commit', text)
        self.assertIn('fetch --depth 1 --no-tags -- $Source $Commit', text)
        self.assertIn('checkout --detach --quiet $Commit', text)


if __name__ == "__main__":
    unittest.main()
