"""Developer unit tests for REQ-MATRIX-PY; independent black-box tests are separate."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from expense_analyzer import InputError, analyze_csv


APP = Path(__file__).resolve().parents[1] / "expense_analyzer.py"


class ExpenseAnalyzerTests(unittest.TestCase):
    def analyze(self, text: str):
        import io

        return analyze_csv(io.StringIO(text))

    def test_category_and_total_are_exact_and_sorted(self) -> None:
        result = self.analyze(
            "date,category,amount\n"
            "2026-01-02,transport,2.00\n"
            "2026-01-01,food,0.10\n"
            "2026-01-03,food,0.20\n"
        )
        self.assertEqual(result, {"categories": {"food": Decimal("0.30"), "transport": Decimal("2.00")}, "total": Decimal("2.30")})

    def test_reordered_header_and_zero_amount_are_accepted(self) -> None:
        result = self.analyze("amount,date,category\n0,2026-02-28, zero \n")
        self.assertEqual(result["categories"], {"zero": Decimal("0")})
        self.assertEqual(result["total"], Decimal("0"))

    def test_large_decimal_total_is_exact_without_context_rounding(self) -> None:
        result = self.analyze(
            "date,category,amount\n"
            "2026-01-01,x,9999999999999999999999999999\n"
            "2026-01-02,x,2\n"
        )
        self.assertEqual(result["categories"], {"x": Decimal("10000000000000000000000000001")})
        self.assertEqual(result["total"], Decimal("10000000000000000000000000001"))

    def test_rejects_amount_beyond_documented_exponent_limit(self) -> None:
        with self.assertRaises(InputError):
            self.analyze("date,category,amount\n2026-01-01,x,1e1001\n")

    def test_enforces_documented_decimal_digit_boundary_without_rounding(self) -> None:
        at_limit = "9" * 1000
        result = self.analyze(f"date,category,amount\n2026-01-01,x,{at_limit}\n")
        self.assertEqual(result["total"], Decimal(at_limit))
        with self.assertRaises(InputError):
            self.analyze(f"date,category,amount\n2026-01-01,x,{'9' * 1001}\n")

    def test_accepts_amount_at_documented_exponent_limit(self) -> None:
        result = self.analyze("date,category,amount\n2026-01-01,x,1e1000\n")
        self.assertEqual(result["total"], Decimal("1e1000"))

    def test_rejects_empty_input_and_header_only(self) -> None:
        for value in ("", "date,category,amount\n"):
            with self.subTest(value=value), self.assertRaises(InputError):
                self.analyze(value)

    def test_rejects_invalid_dates(self) -> None:
        for value in ("", "2026/01/01", "2026-02-30"):
            with self.subTest(value=value), self.assertRaises(InputError):
                self.analyze(f"date,category,amount\n{value},food,1\n")

    def test_rejects_invalid_amounts(self) -> None:
        for value in ("", "not-a-number", "-0.01", "NaN", "sNaN", "Infinity", "-Infinity"):
            with self.subTest(value=value), self.assertRaises(InputError):
                self.analyze(f"date,category,amount\n2026-01-01,food,{value}\n")

    def test_rejects_invalid_csv_structure_and_empty_category(self) -> None:
        cases = (
            "date,category\n2026-01-01,food\n",
            "date,category,amount,extra\n2026-01-01,food,1,no\n",
            "date,category,amount\n2026-01-01,food\n",
            "date,category,amount\n2026-01-01,food,1,extra\n",
            "date,category,amount\n2026-01-01,  ,1\n",
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(InputError):
                self.analyze(value)

    def test_cli_accepts_utf8_bom_and_serializes_decimal_strings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "expenses.csv"
            source.write_text("amount,date,category\n0.10,2026-01-01,food\n0.20,2026-01-02,food\n", encoding="utf-8-sig")
            completed = subprocess.run([sys.executable, str(APP), str(source)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"categories": {"food": "0.30"}, "total": "0.30"})
        self.assertEqual(completed.stderr, "")

    def test_cli_accepts_bom_category_amount_date_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "expenses.csv"
            source.write_text(
                "category,amount,date\n餐饮,0.10,2026-09-01\n出行,0.20,2026-09-02\n餐饮,1.00,2026-09-03\n",
                encoding="utf-8-sig",
            )
            completed = subprocess.run([sys.executable, str(APP), str(source)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"categories": {"出行": "0.20", "餐饮": "1.10"}, "total": "1.30"})
        self.assertEqual(completed.stderr, "")

    def test_cli_invalid_input_and_missing_file_do_not_emit_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.csv"
            invalid.write_text("date,category,amount\n2026-01-01,food,-1\n", encoding="utf-8")
            commands = ([sys.executable, str(APP), str(invalid)], [sys.executable, str(APP), str(Path(directory) / "missing.csv")])
            for command in commands:
                with self.subTest(command=command):
                    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
                    self.assertEqual(completed.returncode, 1)
                    self.assertEqual(completed.stdout, "")
                    self.assertTrue(completed.stderr.startswith("error:"), completed.stderr)

    def test_cli_argument_errors_are_nonzero(self) -> None:
        for command in ([sys.executable, str(APP)], [sys.executable, str(APP), "a.csv", "b.csv"]):
            with self.subTest(command=command):
                completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")


if __name__ == "__main__":
    unittest.main()
