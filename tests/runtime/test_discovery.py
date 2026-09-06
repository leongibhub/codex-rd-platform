import unittest

from rd_platform.discovery import discover, freeze


class DiscoveryTests(unittest.TestCase):
    def test_empty_idea_is_rejected(self):
        with self.assertRaises(ValueError):
            discover("   ")

    def test_baseline_discovery_separates_facts_and_inferences(self):
        model = discover("Build a local inventory approval tool for warehouse staff")

        self.assertEqual("baseline_no_model", model["discovery_mode"])
        self.assertEqual("supported_later", model["host_enhancement"])
        self.assertLessEqual(len(model["questions"]), 3)
        self.assertTrue(model["facts"])
        self.assertTrue(model["inferences"])
        self.assertNotEqual(model["facts"], model["inferences"])
        self.assertEqual("NOT_APPROVED", model["approval_status"])
        for question in model["questions"]:
            self.assertTrue(question["suggestion"])
            self.assertTrue(question["why"])

    def test_freeze_requires_all_required_answers(self):
        model = discover("Collect customer support requests")

        with self.assertRaises(ValueError):
            freeze(model, {})

    def test_freeze_exports_draft_srs_and_partial_rtm_without_approval(self):
        model = discover("Collect customer support requests")
        answers = {question["id"]: "Use the proposed baseline." for question in model["questions"]}

        frozen = freeze(model, answers)

        self.assertEqual("DRAFT", frozen["srs"]["document_state"])
        self.assertTrue(frozen["srs"]["requirements"])
        self.assertEqual("PARTIAL", frozen["rtm"]["traceability_status"])
        self.assertEqual("NOT_APPROVED", frozen["approval_status"])

    def test_freeze_rejects_custom_question_schema_and_invalid_fact_type(self):
        model = discover("Collect customer support requests")
        answers = {question["id"]: "confirmed" for question in model["questions"]}
        malformed_questions = dict(model)
        malformed_questions["questions"] = [
            {"id": "Q-X", "question": "x", "suggestion": "x", "why": "x", "required": True}
        ]
        with self.assertRaises(ValueError):
            freeze(malformed_questions, {"Q-X": "forged"})

        malformed_facts = dict(model)
        malformed_facts["facts"] = "not a facts list"
        with self.assertRaises(ValueError):
            freeze(malformed_facts, answers)


if __name__ == "__main__":
    unittest.main()
