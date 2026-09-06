"""Analyze a UTF-8 CSV of expenses without floating-point arithmetic.

Requirement: REQ-MATRIX-PY
Task: TASK-V3-003
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import TextIO


EXPECTED_FIELDS = {"date", "category", "amount"}
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
MAX_SIGNIFICANT_DIGITS = 1_000
MAX_ABS_EXPONENT = 1_000
MAX_ROWS = 100_000


class InputError(ValueError):
    """A CSV or command input does not satisfy the documented format."""


def _validate_header(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise InputError("CSV is empty; a header is required")
    if len(fieldnames) != len(EXPECTED_FIELDS) or set(fieldnames) != EXPECTED_FIELDS:
        raise InputError("CSV header must contain exactly date, category, amount")


def _parse_date(value: str | None, row_number: int) -> None:
    if value is None or not DATE_PATTERN.fullmatch(value):
        raise InputError(f"row {row_number}: date must be YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise InputError(f"row {row_number}: date is not a calendar date") from exc


def _parse_amount(value: str | None, row_number: int) -> Decimal:
    if value is None or not value.strip():
        raise InputError(f"row {row_number}: amount is required")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise InputError(f"row {row_number}: amount is not a decimal") from exc
    if not amount.is_finite():
        raise InputError(f"row {row_number}: amount must be finite")
    if amount < 0:
        raise InputError(f"row {row_number}: amount must not be negative")
    decimal_tuple = amount.as_tuple()
    if len(decimal_tuple.digits) > MAX_SIGNIFICANT_DIGITS:
        raise InputError(f"row {row_number}: amount has more than {MAX_SIGNIFICANT_DIGITS} significant digits")
    if abs(decimal_tuple.exponent) > MAX_ABS_EXPONENT:
        raise InputError(f"row {row_number}: amount exponent exceeds {MAX_ABS_EXPONENT}")
    return amount


def analyze_csv(stream: TextIO) -> dict[str, object]:
    """Return Decimal category totals and total after validating *stream* fully."""
    reader = csv.DictReader(stream)
    _validate_header(reader.fieldnames)
    entries: list[tuple[str, Decimal]] = []
    for row_number, row in enumerate(reader, start=2):
        if None in row or any(value is None for value in row.values()):
            raise InputError(f"row {row_number}: expected exactly three fields")
        category = row["category"].strip()
        if not category:
            raise InputError(f"row {row_number}: category is required")
        _parse_date(row["date"], row_number)
        amount = _parse_amount(row["amount"], row_number)
        entries.append((category, amount))
        if len(entries) > MAX_ROWS:
            raise InputError(f"CSV contains more than {MAX_ROWS} expense rows")
    if not entries:
        raise InputError("CSV contains no expense rows")
    minimum_exponent = min(amount.as_tuple().exponent for _, amount in entries)
    maximum_adjusted = max(amount.adjusted() for _, amount in entries)
    required_precision = maximum_adjusted - minimum_exponent + len(str(len(entries))) + 1
    categories: dict[str, Decimal] = {}
    total = Decimal("0")
    # The bounded input representation lets this context hold every aligned
    # coefficient and carry exactly; default Decimal context is intentionally
    # not used for financial accumulation.
    with localcontext() as exact_context:
        exact_context.prec = max(1, required_precision)
        for category, amount in entries:
            categories[category] = categories.get(category, Decimal("0")) + amount
            total += amount
    return {"categories": dict(sorted(categories.items())), "total": total}


def json_result(result: dict[str, object]) -> str:
    categories = result["categories"]
    total = result["total"]
    assert isinstance(categories, dict) and isinstance(total, Decimal)
    payload = {"categories": {key: str(value) for key, value in categories.items()}, "total": str(total)}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze a UTF-8 CSV expense file")
    parser.add_argument("csv_path", type=Path, help="CSV with date, category, amount columns")
    return parser


def main(argv: list[str] | None = None) -> int:
    for output in (sys.stdout, sys.stderr):
        if hasattr(output, "reconfigure"):
            output.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        with args.csv_path.open("r", encoding="utf-8-sig", newline="") as source:
            print(json_result(analyze_csv(source)))
    except (InputError, OSError, UnicodeError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
