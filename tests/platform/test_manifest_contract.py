import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
