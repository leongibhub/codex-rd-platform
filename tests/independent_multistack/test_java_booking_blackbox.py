"""Independent public-CLI checks for REQ-MATRIX-JAVA with synthetic booking data."""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
JAVA = Path(r"C:\Program Files\Java\jdk-1.8\bin\java.exe")
CLASSES = ROOT / ".rd-platform" / "build" / "java_booking" / "classes"


class JavaBookingBlackBoxTest(unittest.TestCase):
    def invoke(self, data: Path, *argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(JAVA), "-cp", str(CLASSES), "booking.BookingCli", str(data), *argv], text=True, encoding="utf-8", capture_output=True, check=False)

    def test_overlap_adjacency_and_cross_process_list(self) -> None:
        self.assertTrue(JAVA.is_file(), "JDK java launcher unavailable")
        self.assertTrue(CLASSES.is_dir(), "compiled public classes unavailable")
        with tempfile.TemporaryDirectory(dir=ROOT / ".rd-platform" / "build") as directory:
            data = Path(directory) / "bookings.txt"
            first = self.invoke(data, "add", "A", "2026-09-06T09:00", "2026-09-06T10:00")
            self.assertEqual(first.returncode, 0, first.stderr)
            before = data.read_bytes()
            overlap = self.invoke(data, "add", "A", "2026-09-06T09:30", "2026-09-06T10:30")
            self.assertNotEqual(overlap.returncode, 0)
            self.assertEqual(data.read_bytes(), before)
            self.assertEqual(self.invoke(data, "add", "A", "2026-09-06T10:00", "2026-09-06T11:00").returncode, 0)
            self.assertEqual(self.invoke(data, "add", "B", "2026-09-06T09:30", "2026-09-06T10:30").returncode, 0)
            listed = self.invoke(data, "list", "A")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(len([line for line in listed.stdout.splitlines() if line]), 2)
            self.assertTrue(all("|A|" in line for line in listed.stdout.splitlines()))

    def test_cancel_and_invalid_commands_do_not_write(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".rd-platform" / "build") as directory:
            data = Path(directory) / "bookings.txt"
            created = self.invoke(data, "add", "A", "2026-09-06T09:00", "2026-09-06T10:00")
            self.assertEqual(created.returncode, 0, created.stderr)
            booking_id = created.stdout.strip()
            self.assertEqual(self.invoke(data, "cancel", booking_id).returncode, 0)
            self.assertEqual(self.invoke(data, "list").stdout, "")
            before = data.read_bytes()
            for command in (("cancel", "999"), ("add", "A", "bad", "2026-09-06T10:00"), ("list", "A", "extra")):
                result = self.invoke(data, *command)
                self.assertNotEqual(result.returncode, 0, command)
                self.assertEqual(data.read_bytes(), before, command)


if __name__ == "__main__":
    unittest.main()
