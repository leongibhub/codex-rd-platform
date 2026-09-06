"""Independent security tests for the committed-only local installer.

All side effects are under one temporary directory.  The module deliberately
does not invoke the repository's installer outside that isolated fixture.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "install-to-D.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")


@unittest.skipUnless(POWERSHELL and shutil.which("git"), "requires PowerShell and Git")
class IndependentInstallTransferTests(unittest.TestCase):
    """TC-V3-IND-INSTALL-901..904 / TASK-V3-015, BUG-INSTALL-001."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="rd-platform-independent-install-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.source = self.base / "source"
        (self.source / "scripts").mkdir(parents=True)
        shutil.copy2(INSTALLER, self.source / "install-to-D.ps1")
        # A safe setup double: it writes a marker only after proving that the
        # delivered directory has a real Git HEAD.  It does not install or
        # contact anything.
        (self.source / "scripts" / "setup.ps1").write_text(
            "$ErrorActionPreference = 'Stop'\n"
            "$repo = Split-Path -Parent $PSScriptRoot\n"
            "$head = (& git -C $repo rev-parse HEAD).Trim()\n"
            "if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($head)) { throw 'fixture requires delivered Git HEAD' }\n"
            "Set-Content -LiteralPath (Join-Path $repo 'setup-ran.txt') -Value $head -NoNewline\n",
            encoding="utf-8",
        )
        (self.source / "approved").mkdir()
        (self.source / "approved" / "payload.txt").write_text("first committed payload\n", encoding="utf-8")
        (self.source / ".gitignore").write_text(
            ".env\n.venv/\n.rd-platform/\n.worktrees/\nknowledge/local/\ncache/\n", encoding="utf-8"
        )
        self._git("init")
        self._git("config", "user.email", "fixture@example.invalid")
        self._git("config", "user.name", "Independent installer QA")
        self._git("add", "install-to-D.ps1", "scripts/setup.ps1", "approved/payload.txt", ".gitignore")
        self._git("commit", "-m", "first committed fixture")
        (self.source / "approved" / "payload.txt").write_text("current committed payload\n", encoding="utf-8")
        self._git("add", "approved/payload.txt")
        self._git("commit", "-m", "current committed fixture")
        self.source_head = self._git("rev-parse", "HEAD").stdout.strip()

        for relative in (
            ".env",
            ".venv/private-state.txt",
            ".rd-platform/state.db",
            ".worktrees/worktree.txt",
            "knowledge/local/private.txt",
            "cache/private.txt",
            "untracked-private.txt",
        ):
            marker = self.source / relative
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(f"must-not-transfer:{relative}\n", encoding="utf-8")
        (self.source / ".git" / "hooks" / "source-only-hook").write_text("host hook\n", encoding="utf-8")
        self._git("config", "fixture.sourceMarker", "must-not-transfer")

    def _git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            ["git", *arguments], cwd=self.source, text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed

    def _run(self, destination: Path, *, source_script: Path | None = None,
             force: bool = False) -> subprocess.CompletedProcess[str]:
        script = source_script or self.source / "install-to-D.ps1"
        arguments = [POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
                     str(script), "-Destination", str(destination)]
        if force:
            arguments.append("-Force")
        return subprocess.run(
            arguments,
            cwd=script.parent,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=60,
            check=False,
        )

    @staticmethod
    def _output(completed: subprocess.CompletedProcess[str]) -> str:
        return completed.stdout + completed.stderr

    @staticmethod
    def _diagnostic(completed: subprocess.CompletedProcess[bytes]) -> str:
        """Decode Windows command diagnostics without letting locale bytes fail QA."""
        return (completed.stdout + completed.stderr).decode("mbcs", errors="replace")

    def test_tc_v3_ind_install_901_only_current_committed_content_and_new_git_metadata(self) -> None:
        destination = self.base / "delivered"

        completed = self._run(destination)

        self.assertEqual(completed.returncode, 0, self._output(completed))
        self.assertEqual((destination / "approved" / "payload.txt").read_text(encoding="utf-8"), "current committed payload\n")
        self.assertEqual((destination / "setup-ran.txt").read_text(encoding="utf-8"), self.source_head)
        delivered_head = subprocess.run(
            ["git", "-C", str(destination), "rev-parse", "HEAD"], text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(delivered_head.returncode, 0, delivered_head.stderr)
        self.assertEqual(delivered_head.stdout.strip(), self.source_head)
        history = subprocess.run(
            ["git", "-C", str(destination), "rev-list", "--count", "HEAD"], text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(history.returncode, 0, history.stderr)
        self.assertEqual(history.stdout.strip(), "1", "delivery must be a clean shallow/current checkout")
        remote = subprocess.run(
            ["git", "-C", str(destination), "remote"], text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(remote.returncode, 0, remote.stderr)
        self.assertEqual(remote.stdout.strip(), "", "delivered checkout must not retain source remote metadata")
        self.assertFalse((destination / ".git" / "hooks" / "source-only-hook").exists())
        self.assertNotIn("sourceMarker", (destination / ".git" / "config").read_text(encoding="utf-8"))
        forbidden = (".env", ".venv", ".rd-platform", ".worktrees", "knowledge/local", "cache", "untracked-private.txt")
        leaked = [entry for entry in forbidden if (destination / entry).exists()]
        self.assertEqual(leaked, [], f"delivery leaked source-local state: {leaked}")

    def test_tc_v3_ind_install_902_existing_destination_is_byte_preserved(self) -> None:
        destination = self.base / "old-destination"
        destination.mkdir()
        sentinel = destination / "do-not-touch.bin"
        sentinel.write_bytes(b"old-destination-sentinel\\x00")
        before = self._tree_digest(destination)

        completed = self._run(destination)

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(self._tree_digest(destination), before)
        self.assertEqual(sentinel.read_bytes(), b"old-destination-sentinel\\x00")

    def test_tc_v3_ind_install_903_source_and_descendant_destinations_fail_closed(self) -> None:
        source_before = self._tree_digest(self.source, exclude_git=True)
        for destination in (self.source, self.source / "child-delivery"):
            with self.subTest(destination=destination):
                completed = self._run(destination)
                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(self._tree_digest(self.source, exclude_git=True), source_before)
                self.assertFalse((self.source / "child-delivery").exists())

    def test_tc_v3_ind_install_904_legacy_force_is_rejected_without_creating_target(self) -> None:
        destination = self.base / "force-target"

        completed = self._run(destination, force=True)

        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(destination.exists())

    def test_tc_v3_ind_install_905_source_or_destination_reparse_paths_fail_closed(self) -> None:
        destination_target = self.base / "junction-target"
        destination_target.mkdir()
        protected = destination_target / "protected.txt"
        protected.write_text("do not touch\n", encoding="utf-8")
        destination_link = self.base / "destination-link"
        source_link = self.base / "source-link"
        for link, target in ((destination_link, destination_target), (source_link, self.source)):
            made = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                capture_output=True, timeout=20, check=False,
            )
            self.assertEqual(made.returncode, 0, self._diagnostic(made))

        destination_result = self._run(destination_link)
        source_result = self._run(self.base / "would-not-be-created", source_script=source_link / "install-to-D.ps1")

        self.assertNotEqual(destination_result.returncode, 0)
        self.assertNotEqual(source_result.returncode, 0)
        self.assertEqual(protected.read_text(encoding="utf-8"), "do not touch\n")
        self.assertFalse((self.base / "would-not-be-created").exists())

    def test_tc_v3_ind_install_906_committed_prohibited_paths_fail_before_delivery(self) -> None:
        """Every named local-state path is rejected even if maliciously tracked."""
        prohibited = (".env", ".worktrees/marker", ".pytest_cache/marker", "__pycache__/marker", "cache/marker")
        for index, relative in enumerate(prohibited):
            with self.subTest(relative=relative):
                source = self.base / f"prohibited-source-{index}"
                cloned = subprocess.run(
                    ["git", "clone", "--no-local", str(self.source), str(source)], text=True, encoding="utf-8",
                    errors="replace", capture_output=True, timeout=20, check=False,
                )
                self.assertEqual(cloned.returncode, 0, cloned.stderr)
                configured = subprocess.run(
                    ["git", "-C", str(source), "config", "user.email", "fixture@example.invalid"], text=True,
                    encoding="utf-8", errors="replace", capture_output=True, timeout=20, check=False,
                )
                self.assertEqual(configured.returncode, 0, configured.stderr)
                configured = subprocess.run(
                    ["git", "-C", str(source), "config", "user.name", "Independent installer QA"], text=True,
                    encoding="utf-8", errors="replace", capture_output=True, timeout=20, check=False,
                )
                self.assertEqual(configured.returncode, 0, configured.stderr)
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("tracked prohibited marker\n", encoding="utf-8")
                added = subprocess.run(
                    ["git", "-C", str(source), "add", "-f", relative], text=True, encoding="utf-8",
                    errors="replace", capture_output=True, timeout=20, check=False,
                )
                self.assertEqual(added.returncode, 0, added.stderr)
                committed = subprocess.run(
                    ["git", "-C", str(source), "commit", "-m", "fixture prohibited path"], text=True,
                    encoding="utf-8", errors="replace", capture_output=True, timeout=20, check=False,
                )
                self.assertEqual(committed.returncode, 0, committed.stderr)
                destination = self.base / f"prohibited-destination-{index}"

                completed = self._run(destination, source_script=source / "install-to-D.ps1")

                self.assertNotEqual(completed.returncode, 0)
                self.assertFalse((destination / "approved" / "payload.txt").exists())

    @staticmethod
    def _tree_digest(root: Path, *, exclude_git: bool = False) -> str:
        digest = hashlib.sha256()
        for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
            relative = path.relative_to(root)
            if exclude_git and relative.parts[0] == ".git":
                continue
            digest.update(relative.as_posix().encode("utf-8"))
            if path.is_file():
                digest.update(path.read_bytes())
        return digest.hexdigest()


if __name__ == "__main__":
    unittest.main()
