"""Developer contracts for NFR-V3-002 benchmark safety and evidence."""

import importlib.util
import sys
import tempfile
import time
from unittest.mock import patch
import unittest
from pathlib import Path


def load_benchmark_module():
    path = Path(__file__).parents[2] / "scripts" / "benchmark_lifecycle.py"
    spec = importlib.util.spec_from_file_location("benchmark_lifecycle", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LifecycleBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.benchmark = load_benchmark_module()
        self.small = self.benchmark.CapacityProfile("test", projects=2, artifact_versions=20, events=100, samples=3)

    def tearDown(self):
        self.temp.cleanup()

    def test_smoke_capacity_is_isolated_and_measures_public_runtime_reads(self):
        result = self.benchmark.run_capacity(self.root / "capacity", self.small, disk_budget_bytes=10 * 1024 * 1024, time_budget_seconds=30)
        self.assertEqual("PASS", result["status"])
        self.assertEqual("synthetic_batch_sql", result["seed_mode"])
        self.assertEqual(["Runtime.lifecycle_collection", "Runtime.lifecycle_snapshot"], result["workload_scope"]["public_read_operations"])
        self.assertEqual(2, result["seeded"]["projects"])
        self.assertEqual(20, result["seeded"]["artifact_versions"])
        self.assertEqual(100, result["seeded"]["events"])
        self.assertEqual(3, result["reads"]["collection"]["count"])
        self.assertIn("p95_ms", result["reads"]["snapshot"])
        self.assertIsInstance(result["rss_bytes"], int)
        self.assertTrue((self.root / "capacity" / "state.db").is_file())
        self.assertTrue(Path(result["checkpoint_json"]).is_file())
        self.assertTrue(Path(result["terminal_json"]).is_file())

    def test_existing_database_is_refused_and_budget_abort_is_not_pass(self):
        existing = self.root / "existing"
        existing.mkdir()
        (existing / "state.db").write_bytes(b"do not replace")
        with self.assertRaises(FileExistsError):
            self.benchmark.run_capacity(existing, self.small, disk_budget_bytes=1024, time_budget_seconds=30)
        aborted = self.benchmark.run_capacity(self.root / "aborted", self.small, disk_budget_bytes=1, time_budget_seconds=30)
        self.assertEqual("ABORTED", aborted["status"])
        self.assertNotEqual(0, aborted["exit_code"])
        self.assertTrue(Path(aborted["terminal_json"]).is_file())

    def test_short_soak_writes_checkpoint_and_terminal_evidence(self):
        result = self.benchmark.run_soak(self.root / "soak", self.small, duration_seconds=1, interval_seconds=1, disk_budget_bytes=10 * 1024 * 1024)
        self.assertEqual("PASS", result["status"])
        self.assertGreaterEqual(result["reads"]["collection"]["count"], 1)
        self.assertGreaterEqual(len(result["resource_samples"]), 1)
        self.assertEqual("SQLite public read-only probes", result["workload_scope"]["kind"])
        self.assertTrue({"elapsed_seconds", "rss_bytes", "cpu_seconds", "database_bytes"} <= set(result["resource_samples"][0]))
        self.assertTrue(Path(result["checkpoint_json"]).is_file())
        self.assertTrue(Path(result["terminal_json"]).is_file())

    def test_read_measurement_obeys_capacity_deadline(self):
        result = self.benchmark.run_capacity(self.root / "deadline", self.small, disk_budget_bytes=10 * 1024 * 1024, time_budget_seconds=30)
        with self.assertRaises(self.benchmark.BudgetExceeded):
            self.benchmark._measure_reads(Path(self.root / "deadline" / "state.db"), ["perf-project-000"], 1, deadline=time.monotonic() - 1)

    def test_soak_bounds_reject_before_database_creation(self):
        for duration, interval in ((0, 1), (259201, 1), (1, 0)):
            with self.subTest(duration=duration, interval=interval), self.assertRaises(ValueError):
                self.benchmark.run_soak(self.root / f"bad-{duration}-{interval}", self.small, duration_seconds=duration, interval_seconds=interval)

    def test_setup_interrupt_writes_soak_terminal_and_checkpoint(self):
        with patch.object(self.benchmark, "_seed", side_effect=KeyboardInterrupt):
            result = self.benchmark.run_soak(self.root / "setup-interrupt", self.small, duration_seconds=1, interval_seconds=1,
                                              disk_budget_bytes=10 * 1024 * 1024)
        self.assertEqual("INTERRUPTED", result["status"])
        self.assertEqual(130, result["exit_code"])
        self.assertEqual("capacity_setup", result["phase"])
        self.assertGreaterEqual(result["actual_duration_seconds"], 0)
        self.assertTrue(Path(result["checkpoint_json"]).is_file())
        self.assertTrue(Path(result["terminal_json"]).is_file())


if __name__ == "__main__":
    unittest.main()
