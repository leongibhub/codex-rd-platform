"""Independent public-CLI checks for REQ-MATRIX-PY; synthetic data only."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "examples" / "multistack" / "python_expenses" / "expense_analyzer.py"


class PythonExpensesBlackBoxTest(unittest.TestCase):
    def run_cli(self, path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(APP), str(path), *extra], text=True, encoding="utf-8", capture_output=True, check=False)

    def test_bom_reordered_header_and_exact_totals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "expenses.csv"
            source.write_text("category,amount,date\n餐饮,0.10,2026-09-01\n出行,0.20,2026-09-02\n餐饮,1.00,2026-09-03\n", encoding="utf-8-sig")
            result = self.run_cli(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), {"categories": {"出行": "0.20", "餐饮": "1.10"}, "total": "1.30"})

    def test_rejected_inputs_have_no_success_output(self) -> None:
        cases = {
            "empty.csv": "",
            "header.csv": "date,category,amount\n",
            "date.csv": "date,category,amount\n2026-02-30,x,1\n",
            "negative.csv": "date,category,amount\n2026-01-01,x,-1\n",
            "infinite.csv": "date,category,amount\n2026-01-01,x,Infinity\n",
            "shape.csv": "date,category,amount\n2026-01-01,x,1,extra\n",
        }
        with tempfile.TemporaryDirectory() as directory:
            for name, content in cases.items():
                source = Path(directory) / name
                source.write_text(content, encoding="utf-8")
                result = self.run_cli(source)
                self.assertNotEqual(result.returncode, 0, name)
                self.assertEqual(result.stdout, "", name)
                self.assertTrue(result.stderr.startswith("error:"), result.stderr)
            missing = self.run_cli(Path(directory) / "missing.csv")
        self.assertEqual(missing.returncode, 1)
        self.assertEqual(missing.stdout, "")
        self.assertTrue(missing.stderr.startswith("error:"))

    def test_large_decimal_total_remains_exact_json_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "large.csv"
            source.write_text(
                "date,category,amount\n"
                "2026-09-01,large,99999999999999999999999999999999999999999999999999.1\n"
                "2026-09-02,large,0.2\n",
                encoding="utf-8",
            )
            result = self.run_cli(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "categories": {"large": "99999999999999999999999999999999999999999999999999.3"},
            "total": "99999999999999999999999999999999999999999999999999.3",
        })

    def test_unbounded_exponent_is_rejected_without_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "overflow.csv"
            source.write_text("date,category,amount\n2026-09-01,large,1E+1000000\n", encoding="utf-8")
            result = self.run_cli(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("error:"), result.stderr)

    def test_argument_contract(self) -> None:
        no_argument = subprocess.run([sys.executable, str(APP)], text=True, encoding="utf-8", capture_output=True, check=False)
        extra_argument = subprocess.run([sys.executable, str(APP), "a.csv", "b.csv"], text=True, encoding="utf-8", capture_output=True, check=False)
        for result in (no_argument, extra_argument):
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
