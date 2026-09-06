"""Independent public-CLI checks for REQ-MATRIX-CPP via the documented WSL executable."""
from __future__ import annotations

import subprocess
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
EXE = ROOT / ".rd-platform" / "build" / "cpp_inventory" / "inventory"


def wsl_path(path: Path) -> str:
    resolved = path.resolve()
    return "/mnt/" + resolved.drive.rstrip(":").lower() + resolved.as_posix()[2:]


class CppInventoryBlackBoxTest(unittest.TestCase):
    def invoke(self, data: Path, *argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["wsl.exe", "--", wsl_path(EXE), wsl_path(data), *argv], text=True, encoding="utf-8", capture_output=True, check=False)

    def test_add_reload_and_sorted_list(self) -> None:
        self.assertTrue(EXE.is_file(), "public executable was not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".rd-platform" / "build") as directory:
            data = Path(directory) / "inventory.tsv"
            self.assertEqual(self.invoke(data, "add", "zeta", "2").returncode, 0)
            self.assertEqual(self.invoke(data, "add", "alpha", "3").returncode, 0)
            self.assertEqual(self.invoke(data, "add", "zeta", "5").returncode, 0)
            self.assertEqual(self.invoke(data, "get", "zeta").stdout, "7\n")
            listed = self.invoke(data, "list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(listed.stdout, "alpha\t3\nzeta\t7\n")
            self.assertNotEqual(self.invoke(data, "get", "absent").returncode, 0)

    def test_rejected_mutations_preserve_bytes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".rd-platform" / "build") as directory:
            data = Path(directory) / "inventory.tsv"
            self.assertEqual(self.invoke(data, "add", "widget", "1").returncode, 0)
            before = data.read_bytes()
            for command in (("deduct", "widget", "2"), ("add", "widget", "-1"), ("add", "widget", "1.0"), ("add", "widget", "1", "extra")):
                result = self.invoke(data, *command)
                self.assertNotEqual(result.returncode, 0, command)
                self.assertEqual(data.read_bytes(), before, command)
            corrupt = Path(directory) / "corrupt.tsv"
            corrupt.write_text("widget\tNaN\n", encoding="utf-8")
            corrupt_before = corrupt.read_bytes()
            self.assertNotEqual(self.invoke(corrupt, "add", "next", "1").returncode, 0)
            self.assertEqual(corrupt.read_bytes(), corrupt_before)


if __name__ == "__main__":
    unittest.main()
