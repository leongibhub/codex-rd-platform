"""Independent acceptance tests for TASK-V3-005 lifecycle benchmark safety.

These cases deliberately use small, isolated SQLite fixtures.  They prove
the benchmark's accounting and terminal-result semantics without claiming the
separate 100-project / 100k-version / 1M-event execution has completed.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).parents[2]


def load_benchmark_module():
    """Load a fresh benchmark module so fault injection stays test-local."""
    path = REPOSITORY_ROOT / "scripts" / "benchmark_lifecycle.py"
    name = "independent_benchmark_lifecycle"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class IndependentBenchmarkTests(unittest.TestCase):
    """Risk-based tests for NFR-V3-002 / TASK-V3-005."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.benchmark = load_benchmark_module()
        self.small = self.benchmark.CapacityProfile(
            "independent-small", projects=3, artifact_versions=31, events=79, samples=4
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_tc_v3_ind_601_profile_contract_and_small_seed_have_exact_counts(self):
        """Full-profile contract is exact; a small real seed has no phantom counts."""
        full = self.benchmark.PROFILES["full"]
        self.assertEqual((100, 100_000, 1_000_000, 100),
                         (full.projects, full.artifact_versions, full.events, full.samples))

        result = self.benchmark.run_capacity(
            self.root / "exact-counts", self.small,
            disk_budget_bytes=10 * 1024 * 1024, time_budget_seconds=30,
        )
        self.assertEqual("PASS", result["status"])
        self.assertEqual("synthetic_batch_sql", result["seed_mode"])
        self.assertEqual(
            {"projects": 3, "artifact_versions": 31, "events": 79}, result["seeded"]
        )
        database = self.root / "exact-counts" / "state.db"
        connection = sqlite3.connect(database)
        try:
            self.assertEqual(3, connection.execute("SELECT count(*) FROM projects").fetchone()[0])
            self.assertEqual(3, connection.execute("SELECT count(*) FROM lc_projects").fetchone()[0])
            self.assertEqual(36, connection.execute("SELECT count(*) FROM lc_gates").fetchone()[0])
            self.assertEqual(31, connection.execute("SELECT count(*) FROM lc_artifacts").fetchone()[0])
            self.assertEqual(31, connection.execute("SELECT count(*) FROM lc_artifact_versions").fetchone()[0])
            self.assertEqual(79, connection.execute("SELECT count(*) FROM lc_events").fetchone()[0])
        finally:
            connection.close()
        for operation in ("collection", "snapshot"):
            stats = result["reads"][operation]
            self.assertEqual(4, stats["count"])
            self.assertLessEqual(stats["p50_ms"], stats["p95_ms"])
            self.assertLessEqual(stats["p95_ms"], stats["p99_ms"])
        self.assertEqual([], result["reads"]["errors"])
        terminal = json.loads(Path(result["terminal_json"]).read_text(encoding="utf-8"))
        self.assertEqual("PASS", terminal["status"])

    def test_tc_v3_ind_602_existing_database_is_preserved_not_overwritten(self):
        """A pre-existing state DB is a hard refusal and its bytes stay intact."""
        output = self.root / "preserve-existing"
        output.mkdir()
        database = output / "state.db"
        original = b"independent sentinel: never overwrite"
        database.write_bytes(original)

        with self.assertRaises(FileExistsError):
            self.benchmark.run_capacity(output, self.small, disk_budget_bytes=1024, time_budget_seconds=30)

        self.assertEqual(original, database.read_bytes())

    def test_tc_v3_ind_603_budget_abort_is_terminal_and_never_pass(self):
        """Real disk and elapsed-time budget breaches are observably ABORTED."""
        result = self.benchmark.run_capacity(
            self.root / "budget-abort", self.small, disk_budget_bytes=1, time_budget_seconds=30
        )
        self.assertEqual("ABORTED", result["status"])
        self.assertEqual(2, result["exit_code"])
        self.assertIn("budget exceeded", result["reason"])
        terminal = json.loads(Path(result["terminal_json"]).read_text(encoding="utf-8"))
        self.assertEqual("ABORTED", terminal["status"])
        self.assertNotEqual("PASS", terminal["status"])

        timed = self.benchmark.run_capacity(
            self.root / "time-abort", self.small, disk_budget_bytes=10 * 1024 * 1024, time_budget_seconds=0
        )
        self.assertEqual("ABORTED", timed["status"])
        self.assertEqual(2, timed["exit_code"])
        self.assertEqual("time budget exceeded", timed["reason"])
        self.assertNotEqual("PASS", json.loads(Path(timed["terminal_json"]).read_text(encoding="utf-8"))["status"])

    def test_tc_v3_ind_604_seed_exception_and_soak_interrupt_cannot_pass(self):
        """Synthetic execution failures must remain explicit terminal failures."""
        with patch.object(self.benchmark, "_seed", side_effect=RuntimeError("independent injected seed fault")):
            failed = self.benchmark.run_capacity(
                self.root / "seed-fault", self.small, disk_budget_bytes=10 * 1024 * 1024, time_budget_seconds=30
            )
        self.assertEqual("FAIL", failed["status"])
        self.assertEqual(1, failed["exit_code"])
        self.assertIn("RuntimeError: independent injected seed fault", failed["error"])
        self.assertNotEqual("PASS", json.loads(Path(failed["terminal_json"]).read_text(encoding="utf-8"))["status"])

        clean = {"collection": self.benchmark._percentiles([1_000_000]),
                 "snapshot": self.benchmark._percentiles([2_000_000]), "errors": []}
        with patch.object(self.benchmark, "_measure_reads", side_effect=[clean, KeyboardInterrupt()]):
            interrupted = self.benchmark.run_soak(
                self.root / "soak-interrupt",
                self.benchmark.CapacityProfile("interrupt", 1, 5, 5, 1),
                duration_seconds=1, interval_seconds=1, disk_budget_bytes=10 * 1024 * 1024,
            )
        self.assertEqual("INTERRUPTED", interrupted["status"])
        self.assertEqual(130, interrupted["exit_code"])
        self.assertTrue(Path(interrupted["checkpoint_json"]).is_file())
        self.assertNotEqual("PASS", json.loads(Path(interrupted["terminal_json"]).read_text(encoding="utf-8"))["status"])

    def test_tc_v3_ind_605_short_soak_reports_samples_and_monotonic_percentiles(self):
        """A one-second soak is a bounded operational test, not an eight-hour claim."""
        result = self.benchmark.run_soak(
            self.root / "short-soak",
            self.benchmark.CapacityProfile("soak-small", 1, 9, 17, 1),
            duration_seconds=1, interval_seconds=1, disk_budget_bytes=10 * 1024 * 1024,
        )
        self.assertEqual("PASS", result["status"])
        self.assertGreaterEqual(result["elapsed_seconds"], 1)
        self.assertTrue(Path(result["checkpoint_json"]).is_file())
        terminal = json.loads(Path(result["terminal_json"]).read_text(encoding="utf-8"))
        self.assertEqual("PASS", terminal["status"])
        for operation in ("collection", "snapshot"):
            stats = result["reads"][operation]
            self.assertGreaterEqual(stats["count"], 1)
            self.assertLessEqual(stats["p50_ms"], stats["p95_ms"])
            self.assertLessEqual(stats["p95_ms"], stats["p99_ms"])

    def test_tc_v3_ind_606_percentile_nearest_rank_and_invalid_soak_inputs(self):
        """Boundary validation and p50/p95/p99 semantics are deterministic."""
        self.assertEqual(
            {"count": 4, "p50_ms": 2.0, "p95_ms": 4.0, "p99_ms": 4.0, "throughput_per_second": 400.0},
            self.benchmark._percentiles([1_000_000, 2_000_000, 3_000_000, 4_000_000]),
        )
        for duration, interval in ((0, 1), (259_201, 1), (True, 1), (1, 0), (1, True)):
            with self.subTest(duration=duration, interval=interval):
                with self.assertRaises(ValueError):
                    self.benchmark.run_soak(
                        self.root / f"invalid-{duration!r}-{interval!r}", self.small,
                        duration_seconds=duration, interval_seconds=interval,
                    )

    def test_tc_v3_ind_607_cli_smoke_emits_a_pass_terminal_contract(self):
        """The supported command-line path produces parseable isolated evidence."""
        output = self.root / "cli-smoke"
        completed = subprocess.run(
            [sys.executable, "scripts/benchmark_lifecycle.py", "capacity", "--output-dir", str(output), "--profile", "smoke"],
            cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual("PASS", result["status"])
        self.assertEqual({"projects": 2, "artifact_versions": 200, "events": 1000}, result["seeded"])
        self.assertTrue(Path(result["terminal_json"]).is_file())

    def test_tc_v3_ind_608_total_capacity_deadline_covers_public_read_measurement(self):
        """NFR budget covers the whole capacity run, not only synthetic seeding."""
        original_measure_reads = self.benchmark._measure_reads

        def read_after_deadline(db_path, project_ids, samples, *, deadline=None):
            # The public-read phase itself must observe and enforce a deadline.
            return original_measure_reads(db_path, project_ids, samples, deadline=-1.0)

        with patch.object(self.benchmark, "_measure_reads", side_effect=read_after_deadline):
            result = self.benchmark.run_capacity(
                self.root / "read-over-deadline", self.small,
                disk_budget_bytes=10 * 1024 * 1024, time_budget_seconds=600,
            )
        self.assertEqual("ABORTED", result["status"])
        self.assertEqual(2, result["exit_code"])
        self.assertIn("time budget exceeded", result["reason"])

    def test_tc_v3_ind_609_soak_persists_resource_trends_and_read_workload_scope(self):
        """Long-soak evidence needs per-sample resource history and explicit reads."""
        result = self.benchmark.run_soak(
            self.root / "soak-observability",
            self.benchmark.CapacityProfile("observability-small", 1, 9, 17, 1),
            duration_seconds=1, interval_seconds=1, disk_budget_bytes=10 * 1024 * 1024,
        )
        self.assertEqual("PASS", result["status"])
        checkpoint = json.loads(Path(result["checkpoint_json"]).read_text(encoding="utf-8"))
        self.assertEqual(len(checkpoint["samples"]["collection_ms"]), len(checkpoint["resource_samples"]))
        for sample in checkpoint["resource_samples"]:
            self.assertIsInstance(sample["rss_bytes"], (int, type(None)))
            self.assertIsInstance(sample["cpu_seconds"], (int, float))
            self.assertIsInstance(sample["database_bytes"], int)
        self.assertEqual(
            {"Runtime.lifecycle_collection", "Runtime.lifecycle_snapshot"},
            set(result["workload_scope"]["public_read_operations"]),
        )

    def test_tc_v3_ind_610_setup_interrupt_writes_its_own_terminal_without_sampling(self):
        """Ctrl+C during capacity setup must not escape or become a soak PASS."""
        with patch.object(self.benchmark, "_seed", side_effect=KeyboardInterrupt):
            result = self.benchmark.run_soak(
                self.root / "setup-interrupt",
                self.benchmark.CapacityProfile("setup-interrupt", 1, 5, 5, 1),
                duration_seconds=1, interval_seconds=1, disk_budget_bytes=10 * 1024 * 1024,
            )
        self.assertEqual("INTERRUPTED", result["status"])
        self.assertEqual(130, result["exit_code"])
        self.assertEqual("capacity_setup", result["phase"])
        self.assertEqual([], result["samples"]["collection_ms"])
        self.assertEqual([], result["samples"]["snapshot_ms"])
        self.assertEqual([], result["resource_samples"])
        checkpoint = json.loads(Path(result["checkpoint_json"]).read_text(encoding="utf-8"))
        terminal = json.loads(Path(result["terminal_json"]).read_text(encoding="utf-8"))
        for record in (checkpoint, terminal):
            self.assertEqual("INTERRUPTED", record["status"])
            self.assertEqual(130, record["exit_code"])
            self.assertEqual("capacity_setup", record["phase"])
            self.assertEqual([], record["samples"]["collection_ms"])


if __name__ == "__main__":
    unittest.main()
