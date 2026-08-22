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
    @classmethod
    def setUpClass(cls):
        if POWERSHELL is None:
            raise unittest.SkipTest("PowerShell is required for the Windows setup contract")
        cls._positive_clone = cls._temporary_clone()
        cls.clone = cls._positive_clone.__enter__()
        subprocess.run(["git", "config", "user.name", "Setup Contract Test"], cwd=cls.clone, check=True)
        subprocess.run(["git", "config", "user.email", "setup-contract@example.test"], cwd=cls.clone, check=True)
        cls._healthy_setup = None

    @classmethod
    def tearDownClass(cls):
        cls._positive_clone.__exit__(None, None, None)

    def test_setup_rejects_missing_git_author_identity_before_venv_creation(self):
        """An isolated clone reports each missing Git identity field before creating .venv."""
        with self._temporary_clone() as clone:
            empty_global_config = clone / "empty-gitconfig"
            empty_global_config.write_text("", encoding="utf-8")
            isolated_git = {"GIT_CONFIG_GLOBAL": str(empty_global_config), "GIT_CONFIG_NOSYSTEM": "1"}

            missing_name = self._run_setup(clone, env=isolated_git)
            self.assertNotEqual(missing_name.returncode, 0, self._combined_output(missing_name))
            self.assertIn("Git user.name must be configured before setup.", self._combined_output(missing_name))
            self.assertFalse((clone / ".venv").exists())
            self.assertNotIn("Setup complete.", self._combined_output(missing_name))

            subprocess.run(["git", "config", "user.name", "Setup Contract Test"], cwd=clone, check=True)
            missing_email = self._run_setup(clone, env=isolated_git)
            self.assertNotEqual(missing_email.returncode, 0, self._combined_output(missing_email))
            self.assertIn("Git user.email must be configured before setup.", self._combined_output(missing_email))
            self.assertFalse((clone / ".venv").exists())
            self.assertNotIn("Setup complete.", self._combined_output(missing_email))

    def test_setup_rejects_python_version_probe_before_venv_creation(self):
        """A nonzero Python version probe reports the version prerequisite before creating .venv."""
        with self._temporary_clone() as clone:
            subprocess.run(["git", "config", "user.name", "Setup Contract Test"], cwd=clone, check=True)
            subprocess.run(["git", "config", "user.email", "setup-contract@example.test"], cwd=clone, check=True)
            shim = clone / "python-version-too-old.cmd"
            shim.write_text("@echo off\r\nexit /b 1\r\n", encoding="ascii")

            result = self._run_setup(clone, "-PythonCommand", str(shim))

            self.assertNotEqual(result.returncode, 0, self._combined_output(result))
            self.assertIn("Python version must be 3.11 or newer.", self._combined_output(result))
            self.assertFalse((clone / ".venv").exists())
            self.assertNotIn("Setup complete.", self._combined_output(result))

    def test_skip_dependency_install_keeps_freeze_unchanged_when_requirements_become_uninstallable(self):
        """The public skip switch neither installs altered requirements nor drifts installed packages."""
        self._ensure_healthy_setup()
        before = self._pip_freeze(self.clone)
        requirements = self.clone / "tools" / "mcp" / "company-context" / "requirements.txt"
        original_requirements = requirements.read_text(encoding="utf-8")
        requirements.write_text(
            original_requirements + f"\ntask7-uninstallable @ {(self.clone / 'does-not-exist').as_uri()}\n",
            encoding="utf-8",
        )
        try:
            skipped = self._run_setup(self.clone, "-SkipDependencyInstall")
            self.assertEqual(skipped.returncode, 0, self._combined_output(skipped))
            self.assertEqual(before, self._pip_freeze(self.clone))
            self.assertEqual(skipped.stdout.count("Setup complete."), 1)
            self._assert_skip_mutation_is_detected()
        finally:
            requirements.write_text(original_requirements, encoding="utf-8")

    def test_setup_fails_closed_when_validator_exits_nonzero(self):
        """A failing validator prevents setup success even when dependency installation is skipped."""
        self._ensure_healthy_setup()
        validator = self.clone / "scripts" / "validate_platform.py"
        original_validator = validator.read_text(encoding="utf-8")
        validator.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
        try:
            result = self._run_setup(self.clone, "-SkipDependencyInstall")
            self.assertNotEqual(result.returncode, 0, self._combined_output(result))
            self.assertIn("Platform validation failed with exit code 1.", self._combined_output(result))
            self.assertNotIn("Setup complete.", self._combined_output(result))
            self._assert_validator_mutation_is_detected()
        finally:
            validator.write_text(original_validator, encoding="utf-8")

    def test_setup_fails_closed_when_pip_check_reports_a_broken_requirement(self):
        """A synthetic installed distribution with a missing requirement blocks successful setup."""
        self._ensure_healthy_setup()
        metadata = self._site_packages(self.clone) / "task7_synthetic-0.0.0.dist-info"
        metadata.mkdir()
        (metadata / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: task7-synthetic\nVersion: 0.0.0\n"
            "Requires-Dist: task7-never-installed (==1)\n",
            encoding="utf-8",
        )
        try:
            result = self._run_setup(self.clone, "-SkipDependencyInstall")
            self.assertNotEqual(result.returncode, 0, self._combined_output(result))
            self.assertIn("Dependency consistency check failed with exit code 1.", self._combined_output(result))
            self.assertNotIn("Setup complete.", self._combined_output(result))
        finally:
            (metadata / "METADATA").unlink(missing_ok=True)
            metadata.rmdir()

    def test_default_setup_does_not_change_user_company_local_roots(self):
        """Default setup leaves the user-level COMPANY_LOCAL_ROOTS registry value untouched."""
        before = self._read_user_company_local_roots()
        self._ensure_healthy_setup()
        after = self._read_user_company_local_roots()
        self.assertTrue(after == before, "Default setup changed the user-level COMPANY_LOCAL_ROOTS value.")

    def test_setup_declares_explicit_safe_options_as_a_supplemental_contract(self):
        text = (ROOT / "scripts" / "setup.ps1").read_text(encoding="utf-8")
        self.assertIn("[switch]$PersistLocalRoot", text)
        self.assertIn("[switch]$SkipDependencyInstall", text)
        self.assertIn("if ($PersistLocalRoot)", text)
        self.assertIn("python version must be 3.11 or newer", text.lower())
        self.assertNotIn("pip install --upgrade pip", text)

    def _ensure_healthy_setup(self):
        if self.__class__._healthy_setup is None:
            self.__class__._healthy_setup = self._run_setup(self.clone)
        result = self.__class__._healthy_setup
        self.assertEqual(result.returncode, 0, self._combined_output(result))
        self.assertEqual(result.stdout.count("Setup complete."), 1)
        self.assertTrue((self.clone / ".venv" / "Scripts" / "python.exe").is_file())
        self.assertTrue((self.clone / "knowledge" / "local").is_dir())

    def _assert_skip_mutation_is_detected(self):
        setup = self.clone / "scripts" / "setup.ps1"
        original_setup = setup.read_text(encoding="utf-8")
        setup.write_text(original_setup.replace("if (-not $SkipDependencyInstall)", "if ($true)", 1), encoding="utf-8")
        try:
            mutated = self._run_setup(self.clone, "-SkipDependencyInstall")
            self.assertNotEqual(mutated.returncode, 0, self._combined_output(mutated))
            self.assertIn("Constrained dependency installation failed", self._combined_output(mutated))
            self.assertNotIn("Setup complete.", self._combined_output(mutated))
        finally:
            setup.write_text(original_setup, encoding="utf-8")

    def _assert_validator_mutation_is_detected(self):
        setup = self.clone / "scripts" / "setup.ps1"
        original_setup = setup.read_text(encoding="utf-8")
        checked = 'Invoke-Native "Platform validation" { & $VenvPython "scripts\\validate_platform.py" }'
        self.assertIn(checked, original_setup)
        setup.write_text(original_setup.replace(checked, '& $VenvPython "scripts\\validate_platform.py" | Out-Null', 1), encoding="utf-8")
        try:
            mutated = self._run_setup(self.clone, "-SkipDependencyInstall")
            self.assertEqual(mutated.returncode, 0, self._combined_output(mutated))
            self.assertIn("Setup complete.", mutated.stdout)
        finally:
            setup.write_text(original_setup, encoding="utf-8")

    @staticmethod
    def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
        return result.stdout + result.stderr

    @staticmethod
    def _run_setup(clone: Path, *arguments: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        if env:
            environment.update(env)
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(clone / "scripts" / "setup.ps1"), *arguments],
            cwd=clone, env=environment, text=True, capture_output=True, check=False,
        )

    @staticmethod
    def _pip_freeze(clone: Path) -> str:
        result = subprocess.run([str(clone / ".venv" / "Scripts" / "python.exe"), "-m", "pip", "freeze", "--all"], cwd=clone, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)
        return result.stdout

    @staticmethod
    def _site_packages(clone: Path) -> Path:
        result = subprocess.run([str(clone / ".venv" / "Scripts" / "python.exe"), "-c", "import site; print(site.getsitepackages()[0])"], cwd=clone, text=True, capture_output=True, check=True)
        return Path(result.stdout.strip())

    @staticmethod
    def _read_user_company_local_roots():
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as environment_key:
                return winreg.QueryValueEx(environment_key, "COMPANY_LOCAL_ROOTS")
        except FileNotFoundError:
            return None

    @staticmethod
    def _temporary_clone():
        class TemporaryClone:
            def __enter__(self):
                self._temporary_directory = TemporaryDirectory(prefix="codex-rd-setup-")
                self.path = Path(self._temporary_directory.name) / "platform"
                subprocess.run(["git", "clone", "--no-local", str(ROOT), str(self.path)], cwd=ROOT, text=True, capture_output=True, check=True)
                shutil.copy2(ROOT / "scripts" / "setup.ps1", self.path / "scripts" / "setup.ps1")
                return self.path

            def __exit__(self, exc_type, exc_value, traceback):
                resolved_clone = self.path.resolve()
                resolved_temp_root = Path(self._temporary_directory.name).resolve()
                resolved_system_temp = Path(tempfile.gettempdir()).resolve()
                if (resolved_temp_root == resolved_system_temp or not resolved_temp_root.is_relative_to(resolved_system_temp)
                        or resolved_clone.parent != resolved_temp_root or resolved_clone == resolved_temp_root):
                    raise RuntimeError("refusing to clean an unexpected temporary clone path")
                self._temporary_directory.cleanup()

        return TemporaryClone()


if __name__ == "__main__":
    unittest.main()
