"""TASK-V3-019 contracts for the native Linux setup launcher.

The WSL test is intentionally an isolated Git fixture.  Its identity is a
fixture-only local configuration, never a human approval or a global setting.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "setup.sh"
WSL = shutil.which("wsl.exe")


def wsl_linux_available(command: str | None, *, runner=subprocess.run) -> bool:
    """Return whether the Windows WSL client can actually start a Linux shell."""
    if command is None:
        return False
    try:
        result = runner(
            [command, "-e", "bash", "-lc", "printf TASK_V3_019_WSL_READY"],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "TASK_V3_019_WSL_READY"


WSL_LINUX_AVAILABLE = wsl_linux_available(WSL)


class LinuxSetupContractTests(unittest.TestCase):
    def test_wsl_linux_availability_probe_requires_real_shell(self):
        calls = []

        def available_runner(*args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args[0], 0, "TASK_V3_019_WSL_READY", "")

        self.assertFalse(wsl_linux_available(None))
        self.assertTrue(wsl_linux_available("wsl.exe", runner=available_runner))
        self.assertEqual(["wsl.exe", "-e", "bash", "-lc", "printf TASK_V3_019_WSL_READY"], calls[0][0][0])
        self.assertEqual(10, calls[0][1]["timeout"])
        self.assertFalse(
            wsl_linux_available(
                "wsl.exe",
                runner=lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", "no distribution"),
            )
        )
        self.assertFalse(
            wsl_linux_available("wsl.exe", runner=lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 4294967295, "", ""))
        )

    def test_setup_declares_safe_native_contract(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertTrue(os.access(SCRIPT, os.X_OK))
        self.assertIn("set -euo pipefail", text)
        self.assertIn("Python version must be 3.11 or newer.", text)
        self.assertIn("Git user.name must be configured before setup.", text)
        self.assertIn("Git user.email must be configured before setup.", text)
        self.assertIn('"$venv_python" "scripts/write_local_config.py" "$root"', text)
        self.assertIn('"$venv_python" "scripts/validate_platform.py"', text)
        self.assertIn('"$python_command" -m venv --copies "$root/.venv"', text)
        self.assertIn("Existing virtual environment interpreter must resolve inside this repository.", text)
        self.assertIn("--skip-dependency-install", text)
        self.assertNotIn("sudo", text.lower())
        self.assertNotIn("git config --global", text.lower())
        self.assertNotIn("rm -rf", text.lower())

    @unittest.skipUnless(WSL_LINUX_AVAILABLE, "NOT_AVAILABLE: WSL cannot start a Linux distribution for this fixture")
    def test_wsl_rejects_missing_identity_before_venv_creation(self):
        """Run the real launcher in isolated WSL Git checkouts, not a selector mock."""
        source = ROOT.as_posix().replace("D:", "/mnt/d")
        command = f'''set -euo pipefail
tmp=$(mktemp -d /tmp/task-v3-019.XXXXXX)
trap 'status=$?; if [ "$status" -eq 0 ]; then rm -rf -- "$tmp"; else printf "TASK_V3_019_DIAGNOSTICS=%s\\n" "$tmp"; fi' EXIT
git clone --no-local --quiet -- "{source}" "$tmp/repo"
cp -- "{source}/scripts/setup.sh" "$tmp/repo/scripts/setup.sh"
chmod +x "$tmp/repo/scripts/setup.sh"
cd "$tmp/repo"
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 ./scripts/setup.sh --skip-dependency-install > "$tmp/missing.txt" 2>&1 && exit 91 || status=$?
[ "$status" -ne 0 ]
grep -F "Git user.name must be configured before setup." "$tmp/missing.txt"
[ ! -e .venv ]
git config user.name "TASK-V3-019 fixture"
git config user.email "task-v3-019@example.invalid"
GIT_CONFIG_NOSYSTEM=1 ./scripts/setup.sh --skip-dependency-install > "$tmp/version.txt" 2>&1 && exit 92 || status=$?
[ "$status" -ne 0 ]
grep -F "Python version must be 3.11 or newer." "$tmp/version.txt"
[ ! -e .venv ]
'''
        result = subprocess.run([WSL, "-e", "bash", "-lc", command], text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(WSL_LINUX_AVAILABLE, "NOT_AVAILABLE: WSL cannot start a Linux distribution for this fixture")
    def test_wsl_fails_closed_when_health_validator_fails(self):
        """A fixture interpreter isolates dependencies; the launcher still runs real bash control flow."""
        source = ROOT.as_posix().replace("D:", "/mnt/d")
        command = f'''set -euo pipefail
tmp=$(mktemp -d /tmp/task-v3-019-validator.XXXXXX)
trap 'status=$?; if [ "$status" -eq 0 ]; then rm -rf -- "$tmp"; else printf "TASK_V3_019_DIAGNOSTICS=%s\\n" "$tmp"; fi' EXIT
git clone --no-local --quiet -- "{source}" "$tmp/repo"
cp -- "{source}/scripts/setup.sh" "$tmp/repo/scripts/setup.sh"
chmod +x "$tmp/repo/scripts/setup.sh"
cat > "$tmp/python-fixture" <<'PYTHON'
#!/usr/bin/env bash
if [ "$1" = "-c" ]; then exit 0; fi
if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then
  [ "$3" = "--copies" ] || exit 74
  mkdir -p -- "$4/bin"
  cp -- "$0" "$4/bin/python"
  chmod +x "$4/bin/python"
  exit 0
fi
if [ "$1" = "-m" ] && [ "$2" = "pip" ] && [ "$3" = "check" ]; then exit 0; fi
case "$1" in
  scripts/write_local_config.py) exit 0 ;;
  scripts/validate_platform.py) printf '%s\\n' 'fixture health failure'; exit 1 ;;
esac
exit 97
PYTHON
chmod +x "$tmp/python-fixture"
cd "$tmp/repo"
git config user.name "TASK-V3-019 fixture"
git config user.email "task-v3-019@example.invalid"
./scripts/setup.sh --python-command "$tmp/python-fixture" --skip-dependency-install > "$tmp/result.txt" 2>&1 && exit 93 || status=$?
[ "$status" -ne 0 ]
grep -F "Platform validation failed with exit code 1" "$tmp/result.txt"
! grep -F "Setup complete." "$tmp/result.txt"
'''
        result = subprocess.run([WSL, "-e", "bash", "-lc", command], text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(WSL_LINUX_AVAILABLE, "NOT_AVAILABLE: WSL cannot start a Linux distribution for this fixture")
    def test_wsl_creates_copied_venv_and_rejects_outside_reused_interpreter(self):
        """A fixture Python proves venv-copy and safe-reuse control flow in actual Linux bash."""
        source = ROOT.as_posix().replace("D:", "/mnt/d")
        command = f'''set -euo pipefail
tmp=$(mktemp -d /tmp/task-v3-019-venv.XXXXXX)
trap 'status=$?; if [ "$status" -eq 0 ]; then rm -rf -- "$tmp"; else printf "TASK_V3_019_DIAGNOSTICS=%s\\n" "$tmp"; fi' EXIT
git clone --no-local --quiet -- "{source}" "$tmp/repo"
cp -- "{source}/scripts/setup.sh" "$tmp/repo/scripts/setup.sh"
chmod +x "$tmp/repo/scripts/setup.sh"
cat > "$tmp/python-fixture" <<'PYTHON'
#!/usr/bin/env bash
if [ "$1" = "-c" ]; then exit 0; fi
if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then
  [ "$3" = "--copies" ] || exit 74
  mkdir -p -- "$4/bin"
  cp -- "$0" "$4/bin/python"
  chmod +x "$4/bin/python"
  exit 0
fi
if [ "$1" = "-m" ] && [ "$2" = "pip" ] && [ "$3" = "check" ]; then exit 0; fi
case "$1" in
  scripts/write_local_config.py|scripts/validate_platform.py) exit 0 ;;
esac
exit 97
PYTHON
chmod +x "$tmp/python-fixture"
cd "$tmp/repo"
git config user.name "TASK-V3-019 fixture"
git config user.email "task-v3-019@example.invalid"
./scripts/setup.sh --python-command "$tmp/python-fixture" --skip-dependency-install > "$tmp/created.txt" 2>&1
grep -F "Setup complete." "$tmp/created.txt"
[ ! -L .venv/bin/python ]
cat > .venv/bin/python <<'OLD_PYTHON'
#!/usr/bin/env bash
if [ "$1" = "-c" ]; then exit 1; fi
exit 96
OLD_PYTHON
chmod +x .venv/bin/python
./scripts/setup.sh --python-command "$tmp/python-fixture" --skip-dependency-install > "$tmp/old.txt" 2>&1 && exit 95 || status=$?
[ "$status" -ne 0 ]
grep -F "Repository virtual environment Python version must be 3.11 or newer." "$tmp/old.txt"
! grep -F "Setup complete." "$tmp/old.txt"
rm -- .venv/bin/python
ln -s /usr/bin/python3.10 .venv/bin/python
./scripts/setup.sh --python-command "$tmp/python-fixture" --skip-dependency-install > "$tmp/reused.txt" 2>&1 && exit 94 || status=$?
[ "$status" -ne 0 ]
grep -F "Existing virtual environment interpreter must resolve inside this repository." "$tmp/reused.txt"
! grep -F "Setup complete." "$tmp/reused.txt"
'''
        result = subprocess.run([WSL, "-e", "bash", "-lc", command], text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
