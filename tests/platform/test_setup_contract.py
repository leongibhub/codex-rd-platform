import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")


class SetupContractTests(unittest.TestCase):
    def test_setup_runs_twice_in_clone_when_author_is_configured(self):
        """A normal clone creates its environment once and can skip reinstalling it later."""
        with self._temporary_clone() as clone:
            subprocess.run(
                ["git", "config", "user.name", "Setup Contract Test"],
                cwd=clone,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "setup-contract@example.test"],
                cwd=clone,
                check=True,
            )

            first = self._run_setup(clone)
            second = self._run_setup(clone, "-SkipDependencyInstall")

            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(first.stdout.count("Setup complete."), 1)
            self.assertEqual(second.stdout.count("Setup complete."), 1)
            self.assertTrue((clone / ".venv" / "Scripts" / "python.exe").is_file())
            self.assertTrue((clone / "knowledge" / "local").is_dir())

    def test_setup_rejects_repository_without_git_author_identity(self):
        """A clone without user.name/user.email must fail before setup can succeed."""
        with self._temporary_clone() as clone:
            empty_global_config = clone / "empty-gitconfig"
            empty_global_config.write_text("", encoding="utf-8")
            result = self._run_setup(
                clone,
                env={
                    "GIT_CONFIG_GLOBAL": str(empty_global_config),
                    "GIT_CONFIG_NOSYSTEM": "1",
                },
            )

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("Setup complete.", result.stdout)

    def test_setup_declares_explicit_safe_options_as_a_supplemental_contract(self):
        text = (ROOT / "scripts" / "setup.ps1").read_text(encoding="utf-8")

        self.assertIn("[switch]$PersistLocalRoot", text)
        self.assertIn("[switch]$SkipDependencyInstall", text)
        self.assertIn("if ($PersistLocalRoot)", text)
        self.assertIn("python version must be 3.11 or newer", text.lower())
        self.assertNotIn("pip install --upgrade pip", text)

    @staticmethod
    def _run_setup(clone: Path, *arguments: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        if POWERSHELL is None:
            raise unittest.SkipTest("PowerShell is required for the Windows setup contract")
        environment = os.environ.copy()
        if env:
            environment.update(env)
        return subprocess.run(
            [
                POWERSHELL,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(clone / "scripts" / "setup.ps1"),
                *arguments,
            ],
            cwd=clone,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    @staticmethod
    def _temporary_clone():
        class TemporaryClone:
            def __enter__(self):
                self._temporary_directory = TemporaryDirectory(prefix="codex-rd-setup-")
                self.path = Path(self._temporary_directory.name) / "platform"
                subprocess.run(
                    ["git", "clone", "--no-local", str(ROOT), str(self.path)],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=True,
                )
                shutil.copy2(ROOT / "scripts" / "setup.ps1", self.path / "scripts" / "setup.ps1")
                return self.path

            def __exit__(self, exc_type, exc_value, traceback):
                resolved_clone = self.path.resolve()
                resolved_temp_root = Path(self._temporary_directory.name).resolve()
                resolved_system_temp = Path(tempfile.gettempdir()).resolve()
                if (
                    resolved_temp_root == resolved_system_temp
                    or not resolved_temp_root.is_relative_to(resolved_system_temp)
                    or resolved_clone.parent != resolved_temp_root
                    or resolved_clone == resolved_temp_root
                ):
                    raise RuntimeError("refusing to clean an unexpected temporary clone path")
                self._temporary_directory.cleanup()

        return TemporaryClone()


if __name__ == "__main__":
    unittest.main()
