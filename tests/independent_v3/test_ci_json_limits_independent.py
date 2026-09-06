"""Independent contracts for deterministic Store JSON admission limits.

These tests are intentionally iterative in their fixture construction so they
can reveal a Python-recursion-dependent implementation on a permissive host.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rd_platform.runtime import Runtime
from rd_platform.store import Store


def nested_list(depth: int):
    value = 0
    for _ in range(depth):
        value = [value]
    return value


def expanded_dag(levels: int, width: int):
    value = 0
    for _ in range(levels):
        value = [value] * width
    return value


class IndependentJsonLimitTests(unittest.TestCase):
    """TC-V3-IND-CI-701..706 for BUG-CI-001 / JSON Store safety."""

    def test_tc_v3_ind_ci_701_exact_container_depth_boundaries(self):
        """Root container depth is one: 64 accepts; 65 rejects before encoding."""
        accepted = nested_list(64)
        self.assertEqual(accepted, Store.loads(Store.dumps(accepted)))
        self.assertEqual({"outer": nested_list(63)}, Store.loads(Store.dumps({"outer": nested_list(63)})))
        for value in (nested_list(65), {"outer": nested_list(64)}):
            with self.subTest(value_type=type(value).__name__), \
                 patch("rd_platform.store.json.dumps", return_value="{}") as encoder:
                with self.assertRaises(ValueError):
                    Store.dumps(value)
                encoder.assert_not_called()

    def test_tc_v3_ind_ci_702_depth_limit_does_not_depend_on_python_recursion(self):
        """A 5000-level value is rejected by the Store guard, before JSON encoding."""
        with patch("rd_platform.store.json.dumps", return_value="{}") as encoder:
            with self.assertRaises(ValueError):
                Store.dumps(nested_list(5_000))
            encoder.assert_not_called()

    def test_tc_v3_ind_ci_703_cycles_reject_but_shared_dag_is_allowed(self):
        """Only active ancestry is cyclic; repeated immutable subgraphs are legal."""
        direct = []
        direct.append(direct)
        indirect = {}
        indirect["next"] = [indirect]
        for value in (direct, indirect):
            with self.subTest(value_type=type(value).__name__), \
                 patch("rd_platform.store.json.dumps", return_value="{}") as encoder:
                with self.assertRaises(ValueError):
                    Store.dumps(value)
                encoder.assert_not_called()
        shared = {"items": [1, 2]}
        self.assertEqual([shared, shared], Store.loads(Store.dumps([shared, shared])))

    def test_tc_v3_ind_ci_704_expanded_node_budget_has_exact_boundary(self):
        """Every expanded value counts: 100000 accepts, 100001 rejects."""
        accepted = [None] * 99_999  # root + 99,999 leaves = 100,000 nodes
        self.assertEqual(accepted, Store.loads(Store.dumps(accepted)))
        rejected = [None] * 100_000  # root + 100,000 leaves = 100,001 nodes
        with patch("rd_platform.store.json.dumps", return_value="[]") as encoder:
            with self.assertRaises(ValueError):
                Store.dumps(rejected)
            encoder.assert_not_called()
        # Shared references remain legal, but must consume the expanded budget.
        with patch("rd_platform.store.json.dumps", return_value="[]") as encoder:
            with self.assertRaises(ValueError):
                Store.dumps(expanded_dag(levels=6, width=10))
            encoder.assert_not_called()

    def test_tc_v3_ind_ci_705_loads_enforces_same_limits_and_finite_numbers(self):
        """Admission applies after parsing too, including raw non-finite literals."""
        self.assertEqual(nested_list(64), Store.loads("[" * 64 + "0" + "]" * 64))
        self.assertEqual([None] * 99_999, Store.loads("[" + ",".join(["null"] * 99_999) + "]"))
        for text in (
            "[" * 65 + "0" + "]" * 65,
            "[" + ",".join(["null"] * 100_000) + "]",
            "NaN", "Infinity", "-Infinity", "1e999", '{"amount":1e999}',
        ):
            with self.subTest(prefix=text[:12]):
                with self.assertRaises(ValueError):
                    Store.loads(text)
        for number in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(number=repr(number)):
                with self.assertRaises(ValueError):
                    Store.dumps({"amount": number})
                with self.assertRaises(ValueError):
                    Store.dumps({number: "key"})

    def test_tc_v3_ind_ci_706_public_runtime_rejections_are_atomic(self):
        """Invalid JSON cannot create task, request, event, or any DB mutation."""
        with tempfile.TemporaryDirectory(prefix="ind-ci-json-") as directory:
            runtime = Runtime(Path(directory) / "state.db")
            project = runtime.execute("project.create", {"name": "JSON atomicity", "idea": "independent limits"})

            def digest() -> str:
                with runtime.store.transaction(write=False) as connection:
                    return hashlib.sha256("\n".join(connection.iterdump()).encode("utf-8")).hexdigest()

            before = digest()
            invalid_values = (nested_list(65), nested_list(5_000), [None] * 100_000)
            loop = []
            loop.append(loop)
            invalid_values += (loop,)
            for index, value in enumerate(invalid_values):
                data = {
                    "project_id": project["id"], "title": "must reject", "why": "invalid JSON fixture",
                    "role": "developer", "requirements": ["REQ-CI-JSON"], "dependencies": [],
                    "inputs": {"payload": value},
                }
                with self.subTest(index=index), self.assertRaises(ValueError):
                    runtime.execute("task.create", data, request_id=f"ind-ci-invalid-{index}")
                self.assertEqual(before, digest())


if __name__ == "__main__":
    unittest.main()
