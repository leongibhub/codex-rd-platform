import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.platform_validation import (
    load_manifest,
    validate_gate_contract,
    validate_rtm_contract,
)


ROOT = Path(__file__).resolve().parents[2]


class GovernanceContractTests(unittest.TestCase):
    def test_gate_template_has_all_gates_and_controlled_states(self):
        manifest = load_manifest(ROOT)

        self.assertEqual(validate_gate_contract(ROOT, manifest), [])

    def test_rtm_has_auditable_columns(self):
        manifest = load_manifest(ROOT)

        self.assertEqual(validate_rtm_contract(ROOT, manifest), [])

    def test_template_mode_does_not_require_active_gate_register(self):
        manifest = load_manifest(ROOT)

        self.assertEqual(manifest["lifecycle_mode"], "template")
        self.assertFalse((ROOT / manifest["active_gate_register"]).exists())
        self.assertEqual(validate_gate_contract(ROOT, manifest), [])

    def test_active_mode_without_central_register_returns_stable_error(self):
        with self._temporary_governance_root(lifecycle_mode="active") as root:
            manifest = load_manifest(root)

            self.assertEqual(
                self._codes(validate_gate_contract(root, manifest)),
                ["GOVERNANCE_ACTIVE_REGISTER_MISSING"],
            )

    def test_gate_template_with_a_missing_gate_is_rejected(self):
        with self._temporary_governance_root() as root:
            template = root / "templates" / "gate-register-template.md"
            template.write_text(
                template.read_text(encoding="utf-8").replace(
                    "| G11 | Project Closure |", "| REMOVED | Project Closure |"
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                self._codes(validate_gate_contract(root, load_manifest(root))),
                ["GOVERNANCE_GATE_TEMPLATE_INVALID"],
            )

    def test_rtm_with_a_noncanonical_header_is_rejected(self):
        with self._temporary_governance_root() as root:
            rtm = root / "docs" / "03-requirements" / "requirement-traceability-matrix.md"
            rtm.write_text(
                rtm.read_text(encoding="utf-8").replace("Last Verified", "Verified On"),
                encoding="utf-8",
            )

            self.assertEqual(
                self._codes(validate_rtm_contract(root, load_manifest(root))),
                ["GOVERNANCE_RTM_HEADER_INVALID"],
            )

    def test_gate_template_rejects_artifact_type_text_outside_metadata(self):
        with self._temporary_governance_root() as root:
            template = root / "templates" / "gate-register-template.md"
            template.write_text(
                template.read_text(encoding="utf-8")
                .replace("- Artifact Type: TEMPLATE", "- Artifact Type: ACTIVE")
                + "\n`Artifact Type: TEMPLATE` in prose is not metadata.\n",
                encoding="utf-8",
            )

            self.assertEqual(
                self._codes(validate_gate_contract(root, load_manifest(root))),
                ["GOVERNANCE_GATE_TEMPLATE_INVALID"],
            )

    def test_active_gate_register_rejects_invalid_status_or_evaluation(self):
        cases = (
            ("NOT_EVALUATED", "DECIDED"),
            ("BLOCKED", "BLOCKED"),
        )
        for status, evaluation in cases:
            with self.subTest(status=status, evaluation=evaluation), self._temporary_governance_root(
                lifecycle_mode="active"
            ) as root:
                register = self._write_active_register(root)
                self._set_gate_values(
                    register,
                    "G0",
                    {"Gate Status": status, "Evaluation State": evaluation},
                )

                self.assertEqual(
                    self._codes(validate_gate_contract(root, load_manifest(root))),
                    ["GOVERNANCE_ACTIVE_REGISTER_INVALID"],
                )

    def test_active_gate_pass_rejects_placeholder_evidence_and_required_fields(self):
        placeholders = ("-", "TBD", "TODO", "PENDING", "NOT_AVAILABLE", "NOT EXECUTED", "INFERRED", "N/A", "{{evidence}}", "[待确认]")
        for placeholder in placeholders:
            with self.subTest(placeholder=placeholder), self._temporary_governance_root(
                lifecycle_mode="active"
            ) as root:
                register = self._write_active_register(root)
                self._set_gate_values(
                    register,
                    "G0",
                    {
                        "Gate Status": "PASS",
                        "Evaluation State": "DECIDED",
                        "Baseline": "main@ab100598",
                        "Evaluated At": "2026-08-22T19:12:05+08:00",
                        "Evaluator Role": "tester",
                        "Recorder": "recorder",
                        "Criteria Result": "criteria evaluated",
                        "Evidence IDs": placeholder,
                        "Rationale": "evidence-backed rationale",
                        "Next Action": "archive the decision",
                        "Owner": "owner",
                        "Target Date": "2026-08-23",
                    },
                )

                self.assertEqual(
                    self._codes(validate_gate_contract(root, load_manifest(root))),
                    ["GOVERNANCE_ACTIVE_REGISTER_INVALID"],
                )

    def test_active_gate_pass_rejects_mixed_placeholder_or_unresolvable_evidence(self):
        cases = ("TBD EVD-001", "EVD-999")
        for evidence in cases:
            with self.subTest(evidence=evidence), self._temporary_governance_root(
                lifecycle_mode="active"
            ) as root:
                register = self._write_active_register(root)
                self._set_gate_values(register, "G0", self._pass_gate_values(evidence))

                self.assertEqual(
                    self._codes(validate_gate_contract(root, load_manifest(root))),
                    ["GOVERNANCE_ACTIVE_REGISTER_INVALID"],
                )

    def test_active_gate_pass_accepts_external_declared_evidence(self):
        with self._temporary_governance_root(lifecycle_mode="active") as root:
            register = self._write_active_register(root)
            self._write_evidence_document(root, "EVD-001")
            self._set_gate_values(register, "G0", self._pass_gate_values("EVD-001"))

            self.assertEqual(validate_gate_contract(root, load_manifest(root)), [])

    def test_active_gate_pass_rejects_evidence_declared_by_its_own_register(self):
        with self._temporary_governance_root(lifecycle_mode="active") as root:
            register = self._write_active_register(root)
            self._set_gate_values(register, "G0", self._pass_gate_values("EVD-001"))
            register.write_text(
                register.read_text(encoding="utf-8") + "\n- Record ID: EVD-001\n",
                encoding="utf-8",
            )

            self.assertEqual(
                self._codes(validate_gate_contract(root, load_manifest(root))),
                ["GOVERNANCE_ACTIVE_REGISTER_INVALID"],
            )

    def test_active_gate_links_resolve_from_register_and_reject_self_rtm_or_outside_targets(self):
        valid_links = (
            ("[EVD-002](../evidence/EVD-002.md)", "EVD-002.md"),
            ("[EVD Two](<../evidence/EVD Two.md>)", "EVD Two.md"),
        )
        for evidence_reference, filename in valid_links:
            with self.subTest(evidence_reference=evidence_reference), self._temporary_governance_root(
                lifecycle_mode="active"
            ) as root:
                register = self._write_active_register(root)
                evidence = root / "docs" / "evidence" / filename
                evidence.parent.mkdir(parents=True)
                evidence.write_text("external evidence\n", encoding="utf-8")
                self._set_gate_values(
                    register, "G0", self._pass_gate_values(evidence_reference)
                )

                self.assertEqual(validate_gate_contract(root, load_manifest(root)), [])

        cases = (
            "[self](gate-register.md)",
            "[rtm](../03-requirements/requirement-traceability-matrix.md)",
            "[outside](../../../outside.md)",
        )
        for evidence_reference in cases:
            with self.subTest(evidence_reference=evidence_reference), self._temporary_governance_root(
                lifecycle_mode="active"
            ) as root:
                register = self._write_active_register(root)
                if "outside" in evidence_reference:
                    (root.parent / "outside.md").write_text("outside\n", encoding="utf-8")
                self._set_gate_values(register, "G0", self._pass_gate_values(evidence_reference))

                self.assertEqual(
                    self._codes(validate_gate_contract(root, load_manifest(root))),
                    ["GOVERNANCE_ACTIVE_REGISTER_INVALID"],
                )

    def test_active_gate_register_rejects_an_extra_table_or_repeated_gate_after_blank_line(self):
        with self._temporary_governance_root(lifecycle_mode="active") as root:
            register = self._write_active_register(root)
            register.write_text(
                register.read_text(encoding="utf-8") + "\n\n" + register.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            self.assertEqual(
                self._codes(validate_gate_contract(root, load_manifest(root))),
                ["GOVERNANCE_ACTIVE_REGISTER_INVALID"],
            )

        with self._temporary_governance_root(lifecycle_mode="active") as root:
            register = self._write_active_register(root)
            first_gate_row = next(
                line for line in register.read_text(encoding="utf-8").splitlines() if line.startswith("| G0 |")
            )
            register.write_text(
                register.read_text(encoding="utf-8") + "\n\n" + first_gate_row + "\n",
                encoding="utf-8",
            )

            self.assertEqual(
                self._codes(validate_gate_contract(root, load_manifest(root))),
                ["GOVERNANCE_ACTIVE_REGISTER_INVALID"],
            )

    def test_active_rtm_rejects_duplicate_trace_or_requirement_ids(self):
        cases = (
            ({"Trace ID": "TRACE-001", "REQ/NFR": "NFR-001"}),
            ({"Trace ID": "TRACE-002", "REQ/NFR": "REQ-001"}),
        )
        for duplicate_values in cases:
            with self.subTest(duplicate_values=duplicate_values), self._temporary_governance_root(
                lifecycle_mode="active"
            ) as root:
                first = self._complete_rtm_row()
                duplicate = self._complete_rtm_row(**duplicate_values)
                self._write_active_rtm(root, [first, duplicate])

                self.assertEqual(
                    self._codes(validate_rtm_contract(root, load_manifest(root))),
                    ["GOVERNANCE_ACTIVE_RTM_ROW_INVALID"],
                )

    def test_rtm_rejects_an_extra_table_or_data_after_a_blank_line(self):
        with self._temporary_governance_root() as root:
            rtm = root / "docs" / "03-requirements" / "requirement-traceability-matrix.md"
            contents = rtm.read_text(encoding="utf-8")
            rtm.write_text(contents + "\n\n" + contents, encoding="utf-8")

            self.assertEqual(
                self._codes(validate_rtm_contract(root, load_manifest(root))),
                ["GOVERNANCE_RTM_HEADER_INVALID"],
            )

        with self._temporary_governance_root() as root:
            rtm = root / "docs" / "03-requirements" / "requirement-traceability-matrix.md"
            rtm.write_text(
                rtm.read_text(encoding="utf-8") + "\n\n" + self._rtm_row_line(self._complete_rtm_row()) + "\n",
                encoding="utf-8",
            )

            self.assertEqual(
                self._codes(validate_rtm_contract(root, load_manifest(root))),
                ["GOVERNANCE_RTM_HEADER_INVALID"],
            )

    def test_active_rtm_rejects_released_without_executed_evidence(self):
        with self._temporary_governance_root(lifecycle_mode="active") as root:
            row = self._complete_rtm_row(
                **{
                    "TC": "",
                    "Test Execution/Evidence": "",
                    "Verification Result": "NOT_EXECUTED",
                    "REL": "REL-001",
                    "Traceability Status": "PARTIAL",
                    "Evidence Status": "NOT_EXECUTED",
                }
            )
            self._write_active_rtm(root, [row])

            self.assertEqual(
                self._codes(validate_rtm_contract(root, load_manifest(root))),
                ["GOVERNANCE_ACTIVE_RTM_ROW_INVALID"],
            )

    def test_active_rtm_rejects_wrong_typed_links_or_closed_bug_without_bug(self):
        cases = (
            {"Test Execution/Evidence": "BG-001"},
            {"BG": "business goal text"},
            {"BUG": "-", "Defect Disposition": "CLOSED"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides), self._temporary_governance_root(
                lifecycle_mode="active"
            ) as root:
                self._write_active_rtm(root, [self._complete_rtm_row(**overrides)])

                self.assertEqual(
                    self._codes(validate_rtm_contract(root, load_manifest(root))),
                    ["GOVERNANCE_ACTIVE_RTM_ROW_INVALID"],
                )

    def test_active_rtm_rejects_noncanonical_defect_disposition(self):
        for disposition in ("CLOSED TBD", "closed", "WAIVED"):
            with self.subTest(disposition=disposition), self._temporary_governance_root(
                lifecycle_mode="active"
            ) as root:
                self._write_active_rtm(
                    root,
                    [self._complete_rtm_row(**{"Defect Disposition": disposition})],
                )

                self.assertEqual(
                    self._codes(validate_rtm_contract(root, load_manifest(root))),
                    ["GOVERNANCE_ACTIVE_RTM_ROW_INVALID"],
                )

    def test_active_rtm_accepts_controlled_defect_dispositions(self):
        cases = (
            ("OPEN", ""),
            ("IN_PROGRESS", ""),
            ("RESOLVED", ""),
            ("CLOSED", "BUG-001"),
            ("ACCEPTED_RISK", ""),
            ("NOT_APPLICABLE", ""),
        )
        for disposition, bug in cases:
            with self.subTest(disposition=disposition), self._temporary_governance_root(
                lifecycle_mode="active"
            ) as root:
                self._write_active_rtm(
                    root,
                    [
                        self._complete_rtm_row(
                            **{"BUG": bug, "Defect Disposition": disposition}
                        )
                    ],
                )

                self.assertEqual(validate_rtm_contract(root, load_manifest(root)), [])

    def test_active_rtm_rejects_embedded_or_mixed_typed_references_and_placeholder_prose(self):
        cases = (
            {"CR": "TBD CR-001"},
            {"BUG": "wrong BUG-001 prose"},
            {"REL": "REL-001 TBD"},
            {"Test Execution/Evidence": "wrong EVD-001 prose"},
            {"Acceptance Criteria": "TBD criteria"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides), self._temporary_governance_root(
                lifecycle_mode="active"
            ) as root:
                self._write_active_rtm(root, [self._complete_rtm_row(**overrides)])

                self.assertEqual(
                    self._codes(validate_rtm_contract(root, load_manifest(root))),
                    ["GOVERNANCE_ACTIVE_RTM_ROW_INVALID"],
                )

    def test_active_rtm_prose_placeholder_rules_are_context_sensitive(self):
        with self._temporary_governance_root(lifecycle_mode="active") as root:
            self._write_active_rtm(
                root,
                [
                    self._complete_rtm_row(
                        **{
                            "Acceptance Criteria": "system displays PENDING while approval is outstanding"
                        }
                    )
                ],
            )

            self.assertEqual(validate_rtm_contract(root, load_manifest(root)), [])

        invalid_prose = (
            "PENDING while approval is outstanding",
            "NOT_EXECUTED: execution evidence will follow",
            "INFERRED - confirmation is required",
            "criterion remains [待项目组确认] after review",
            "criterion remains {{acceptance_criterion}} after review",
        )
        for acceptance_criteria in invalid_prose:
            with self.subTest(acceptance_criteria=acceptance_criteria), self._temporary_governance_root(
                lifecycle_mode="active"
            ) as root:
                self._write_active_rtm(
                    root,
                    [
                        self._complete_rtm_row(
                            **{"Acceptance Criteria": acceptance_criteria}
                        )
                    ],
                )

                self.assertEqual(
                    self._codes(validate_rtm_contract(root, load_manifest(root))),
                    ["GOVERNANCE_ACTIVE_RTM_ROW_INVALID"],
                )

    def test_active_rtm_cannot_self_declare_test_execution_evidence(self):
        with self._temporary_governance_root(lifecycle_mode="active") as root:
            self._write_active_rtm(root, [self._complete_rtm_row()])
            (root / "docs" / "evidence" / "EVD-001.md").unlink()
            rtm = root / "docs" / "03-requirements" / "requirement-traceability-matrix.md"
            rtm.write_text(
                rtm.read_text(encoding="utf-8") + "\n- Evidence ID: EVD-001\n",
                encoding="utf-8",
            )

            self.assertEqual(
                self._codes(validate_rtm_contract(root, load_manifest(root))),
                ["GOVERNANCE_ACTIVE_RTM_ROW_INVALID"],
            )

    def test_active_rtm_rejects_empty_trace_id(self):
        with self._temporary_governance_root(lifecycle_mode="active") as root:
            self._write_active_rtm(root, [self._complete_rtm_row(**{"Trace ID": ""})])

            self.assertEqual(
                self._codes(validate_rtm_contract(root, load_manifest(root))),
                ["GOVERNANCE_ACTIVE_RTM_ROW_INVALID"],
            )

    def test_active_rtm_accepts_evidence_backed_fail_or_blocked_without_release(self):
        for result in ("FAIL", "BLOCKED"):
            with self.subTest(result=result), self._temporary_governance_root(
                lifecycle_mode="active"
            ) as root:
                self._write_active_rtm(
                    root,
                    [
                        self._complete_rtm_row(
                            **{
                                "Verification Result": result,
                                "REL": "",
                                "Traceability Status": "PARTIAL",
                            }
                        )
                    ],
                )

                self.assertEqual(validate_rtm_contract(root, load_manifest(root)), [])

    def test_active_rtm_rejects_closed_bug_without_fix_and_regression_evidence(self):
        with self._temporary_governance_root(lifecycle_mode="active") as root:
            row = self._complete_rtm_row(
                **{
                    "Commit/MR": "",
                    "TC": "",
                    "Test Execution/Evidence": "",
                    "Verification Result": "NOT_EXECUTED",
                    "BUG": "BUG-001",
                    "Defect Disposition": "CLOSED",
                    "REL": "",
                    "Traceability Status": "PARTIAL",
                    "Evidence Status": "NOT_EXECUTED",
                    "Last Verified": "",
                }
            )
            self._write_active_rtm(root, [row])

            self.assertEqual(
                self._codes(validate_rtm_contract(root, load_manifest(root))),
                ["GOVERNANCE_ACTIVE_RTM_ROW_INVALID"],
            )

    def test_active_rtm_rejects_change_without_approval_evidence(self):
        with self._temporary_governance_root(lifecycle_mode="active") as root:
            row = self._complete_rtm_row(
                **{"CR": "CR-001", "Test Execution/Evidence": "manual test output"}
            )
            self._write_active_rtm(root, [row])

            self.assertEqual(
                self._codes(validate_rtm_contract(root, load_manifest(root))),
                ["GOVERNANCE_ACTIVE_RTM_ROW_INVALID"],
            )

    def test_active_rtm_rejects_complete_traceability_with_missing_links(self):
        with self._temporary_governance_root(lifecycle_mode="active") as root:
            row = self._complete_rtm_row(**{"BG": ""})
            self._write_active_rtm(root, [row])

            self.assertEqual(
                self._codes(validate_rtm_contract(root, load_manifest(root))),
                ["GOVERNANCE_ACTIVE_RTM_ROW_INVALID"],
            )

    def test_fenced_metadata_or_table_cannot_supply_a_governance_contract(self):
        for fence in ("```", "~~~"):
            with self.subTest(fence=fence, kind="metadata"), self._temporary_governance_root() as root:
                template = root / "templates" / "gate-register-template.md"
                template.write_text(
                    template.read_text(encoding="utf-8").replace(
                        "- Artifact Type: TEMPLATE",
                        f"- Artifact Type: ACTIVE\n{fence}markdown\n- Artifact Type: TEMPLATE\n{fence}",
                    ),
                    encoding="utf-8",
                )

                self.assertEqual(
                    self._codes(validate_gate_contract(root, load_manifest(root))),
                    ["GOVERNANCE_GATE_TEMPLATE_INVALID"],
                )

            with self.subTest(fence=fence, kind="table"), self._temporary_governance_root() as root:
                template = root / "templates" / "gate-register-template.md"
                contents = template.read_text(encoding="utf-8")
                table_start = contents.index("| Gate ID |")
                template.write_text(
                    contents[:table_start] + f"{fence}markdown\n" + contents[table_start:] + f"{fence}\n",
                    encoding="utf-8",
                )

                self.assertEqual(
                    self._codes(validate_gate_contract(root, load_manifest(root))),
                    ["GOVERNANCE_GATE_TEMPLATE_INVALID"],
                )

    def test_invalid_fence_closing_cannot_expose_metadata_or_table(self):
        with self._temporary_governance_root() as root:
            template = root / "templates" / "gate-register-template.md"
            template.write_text(
                template.read_text(encoding="utf-8")
                .replace(
                    "- Artifact Type: TEMPLATE",
                    "- Artifact Type: ACTIVE\n```markdown\n- Artifact Type: TEMPLATE\n````not-a-valid-close\n- Artifact Type: TEMPLATE",
                )
                + "\n```\n",
                encoding="utf-8",
            )

            self.assertEqual(
                self._codes(validate_gate_contract(root, load_manifest(root))),
                ["GOVERNANCE_GATE_TEMPLATE_INVALID"],
            )

    def test_backtick_info_string_with_backtick_does_not_hide_a_real_table(self):
        with self._temporary_governance_root() as root:
            template = root / "templates" / "gate-register-template.md"
            template.write_text(
                template.read_text(encoding="utf-8")
                + "\n```markdown`invalid\n| Extra | Table |\n|---|---|\n| real | data |\n",
                encoding="utf-8",
            )

            self.assertEqual(
                self._codes(validate_gate_contract(root, load_manifest(root))),
                ["GOVERNANCE_GATE_TEMPLATE_INVALID"],
            )

    def test_tilde_info_string_with_backtick_still_opens_a_fence(self):
        with self._temporary_governance_root() as root:
            template = root / "templates" / "gate-register-template.md"
            template.write_text(
                template.read_text(encoding="utf-8")
                + "\n   ~~~markdown`allowed\n| Hidden | Table |\n|---|---|\n| fenced | data |\n   ~~~\n",
                encoding="utf-8",
            )

            self.assertEqual(validate_gate_contract(root, load_manifest(root)), [])

    @staticmethod
    def _codes(issues):
        return [issue.code for issue in issues]

    def _temporary_governance_root(self, lifecycle_mode: str = "template"):
        return _TemporaryGovernanceRoot(lifecycle_mode)

    @staticmethod
    def _write_active_register(root: Path) -> Path:
        template = root / "templates" / "gate-register-template.md"
        register = root / "docs" / "08-project-management" / "gate-register.md"
        register.parent.mkdir(parents=True, exist_ok=True)
        register.write_text(
            template.read_text(encoding="utf-8")
            .replace("{{PASS\\|FAIL\\|BLOCKED}}", "BLOCKED")
            .replace("{{NOT_EVALUATED\\|IN_REVIEW\\|DECIDED}}", "DECIDED"),
            encoding="utf-8",
        )
        return register

    @staticmethod
    def _set_gate_values(register: Path, gate_id: str, values: dict[str, str]):
        lines = register.read_text(encoding="utf-8").splitlines()
        header = next(line for line in lines if line.startswith("| Gate ID |"))
        headers = [cell.strip() for cell in header.strip("|").split("|")]
        for index, line in enumerate(lines):
            if line.startswith(f"| {gate_id} |"):
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                for name, value in values.items():
                    cells[headers.index(name)] = value
                lines[index] = "| " + " | ".join(cells) + " |"
                register.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return
        raise AssertionError(f"missing {gate_id} row")

    @staticmethod
    def _complete_rtm_row(**overrides: str) -> dict[str, str]:
        row = {
            "Trace ID": "TRACE-001",
            "Scope Status": "IN_SCOPE",
            "BG": "BG-001",
            "PRD": "PRD-001",
            "REQ/NFR": "REQ-001",
            "Acceptance Criteria": "observable acceptance criterion",
            "DES/ADR": "DES-001",
            "TASK": "TASK-001",
            "CR": "",
            "Commit/MR": "MR-001",
            "TC": "TC-001",
            "Test Execution/Evidence": "EVD-001",
            "Verification Result": "PASS",
            "BUG": "",
            "Defect Disposition": "",
            "REL": "REL-001",
            "Traceability Status": "COMPLETE",
            "Evidence Status": "VERIFIED",
            "Last Verified": "2026-08-22",
        }
        return row | overrides

    @staticmethod
    def _pass_gate_values(evidence: str) -> dict[str, str]:
        return {
            "Gate Status": "PASS",
            "Evaluation State": "DECIDED",
            "Baseline": "main@ab100598",
            "Evaluated At": "2026-08-22T19:12:05+08:00",
            "Evaluator Role": "tester",
            "Recorder": "recorder",
            "Criteria Result": "criteria evaluated",
            "Evidence IDs": evidence,
            "Rationale": "evidence-backed rationale",
            "Next Action": "archive the decision",
            "Owner": "owner",
            "Target Date": "2026-08-23",
        }

    @staticmethod
    def _write_evidence_document(root: Path, evidence_id: str):
        evidence = root / "docs" / "evidence" / f"{evidence_id}.md"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(f"- Record ID: {evidence_id}\n", encoding="utf-8")

    def _write_active_rtm(self, root: Path, rows: list[dict[str, str]]):
        rtm = root / "docs" / "03-requirements" / "requirement-traceability-matrix.md"
        lines = rtm.read_text(encoding="utf-8").splitlines()
        header, separator = next(
            (lines[index], lines[index + 1])
            for index, line in enumerate(lines[:-1])
            if line.startswith("|") and lines[index + 1].startswith("|")
        )
        rtm.write_text(
            "\n".join([header, separator, *(self._rtm_row_line(row) for row in rows)]) + "\n",
            encoding="utf-8",
        )
        self._write_evidence_document(root, "EVD-001")

    @staticmethod
    def _rtm_row_line(row: dict[str, str]) -> str:
        return "| " + " | ".join(row.values()) + " |"


class _TemporaryGovernanceRoot:
    def __init__(self, lifecycle_mode: str):
        self._directory = TemporaryDirectory()
        self._lifecycle_mode = lifecycle_mode

    def __enter__(self) -> Path:
        root = Path(self._directory.name) / "repo"
        root.mkdir()
        manifest = load_manifest(ROOT) | {"lifecycle_mode": self._lifecycle_mode}
        (root / "platform-manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        for relative_path in (
            Path("templates/gate-register-template.md"),
            Path("docs/03-requirements/requirement-traceability-matrix.md"),
        ):
            destination = root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative_path, destination)
        return root

    def __exit__(self, *unused):
        self._directory.cleanup()


if __name__ == "__main__":
    unittest.main()
