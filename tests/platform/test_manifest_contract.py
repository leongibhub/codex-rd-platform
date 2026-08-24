import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.platform_validation import (
    collect_agent_ids,
    collect_skill_ids,
    load_manifest,
    validate_manifest_contract,
)


ROOT = Path(__file__).resolve().parents[2]


class ManifestContractTests(unittest.TestCase):
    def test_manifest_matches_runtime_ids_and_declares_template_mode(self):
        manifest = load_manifest(ROOT)
        self.assertEqual(set(manifest["agents"]), collect_agent_ids(ROOT))
        self.assertEqual(set(manifest["skills"]), collect_skill_ids(ROOT))
        self.assertEqual(manifest["gates"], [f"G{i}" for i in range(12)])
        self.assertEqual(manifest["lifecycle_mode"], "template")
        self.assertEqual(validate_manifest_contract(ROOT), [])

    def test_collect_skill_ids_reads_only_frontmatter_and_unquotes_name(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_skill(
                root,
                "quoted",
                '---\nname: "quoted-skill"\n---\nname: body-fake\n',
            )
            self._write_skill(root, "body-only", "name: body-only-fake\n")
            self._write_skill(
                root,
                "frontmatter-without-name",
                "---\ndescription: example\n---\nname: body-fake\n",
            )

            self.assertEqual(collect_skill_ids(root), {"quoted-skill"})

    def test_agent_mismatch_returns_its_stable_error_code(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_contract_root(root, agents=["wrong-agent"])

            self.assertEqual(
                [issue.code for issue in validate_manifest_contract(root)],
                ["MANIFEST_AGENTS_MISMATCH"],
            )

    def test_skill_mismatch_returns_its_stable_error_code(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_contract_root(root, skills=["wrong-skill"])

            self.assertEqual(
                [issue.code for issue in validate_manifest_contract(root)],
                ["MANIFEST_SKILLS_MISMATCH"],
            )

    def test_gate_mismatch_returns_its_stable_error_code(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_contract_root(root, gates=["G0"])

            self.assertEqual(
                [issue.code for issue in validate_manifest_contract(root)],
                ["MANIFEST_GATES_INVALID"],
            )

    def test_lifecycle_mode_mismatch_returns_its_stable_error_code(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_contract_root(root, lifecycle_mode="unsupported")

            self.assertEqual(
                [issue.code for issue in validate_manifest_contract(root)],
                ["MANIFEST_LIFECYCLE_MODE_INVALID"],
            )

    def test_manifest_and_runtime_duplicate_identifiers_are_rejected_without_set_false_green(self):
        cases = (
            ("manifest agents", {"agents": ["agent", "agent"]}, "MANIFEST_AGENT_IDS_DUPLICATE"),
            ("manifest skills", {"skills": ["skill", "skill"]}, "MANIFEST_SKILL_IDS_DUPLICATE"),
        )
        for name, override, expected_code in cases:
            with self.subTest(name=name), TemporaryDirectory() as directory:
                root = Path(directory)
                self._write_contract_root(root, **override)
                self.assertEqual([issue.code for issue in validate_manifest_contract(root)], [expected_code])

        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_contract_root(root)
            (root / ".codex" / "agents" / "duplicate.toml").write_text('name = "agent"\n', encoding="utf-8")
            self.assertEqual([issue.code for issue in validate_manifest_contract(root)], ["RUNTIME_AGENT_IDS_DUPLICATE"])

        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_contract_root(root)
            self._write_skill(root, "duplicate", "---\nname: skill\n---\nname: body-is-not-frontmatter\n")
            self.assertEqual([issue.code for issue in validate_manifest_contract(root)], ["RUNTIME_SKILL_IDS_DUPLICATE"])

    def _write_contract_root(
        self,
        root: Path,
        *,
        agents: list[str] | None = None,
        skills: list[str] | None = None,
        gates: list[str] | None = None,
        lifecycle_mode: str = "template",
    ):
        (root / ".codex" / "agents").mkdir(parents=True)
        (root / ".codex" / "agents" / "agent.toml").write_text(
            'name = "agent"\n', encoding="utf-8"
        )
        self._write_skill(root, "skill", "---\nname: skill\n---\n")
        (root / "platform-manifest.json").write_text(
            json.dumps(
                {
                    "agents": agents or ["agent"],
                    "skills": skills or ["skill"],
                    "gates": gates or [f"G{i}" for i in range(12)],
                    "lifecycle_mode": lifecycle_mode,
                    "gate_register_template": "templates/gate-register-template.md",
                    "active_gate_register": "docs/08-project-management/gate-register.md",
                    "requirement_traceability_matrix": "docs/03-requirements/requirement-traceability-matrix.md",
                }
            ),
            encoding="utf-8",
        )

    def _write_skill(self, root: Path, skill_id: str, contents: str):
        skill_path = root / ".agents" / "skills" / skill_id
        skill_path.mkdir(parents=True, exist_ok=True)
        (skill_path / "SKILL.md").write_text(contents, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
