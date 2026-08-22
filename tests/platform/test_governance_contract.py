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

    @staticmethod
    def _codes(issues):
        return [issue.code for issue in issues]

    def _temporary_governance_root(self, lifecycle_mode: str = "template"):
        return _TemporaryGovernanceRoot(lifecycle_mode)


class _TemporaryGovernanceRoot:
    def __init__(self, lifecycle_mode: str):
        self._directory = TemporaryDirectory()
        self._lifecycle_mode = lifecycle_mode

    def __enter__(self) -> Path:
        root = Path(self._directory.name)
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
