"""Offline tests for the CuSelect-AI LLM cycle."""

import copy
import unittest

from cuselect.agents.llm_cycle_validation import (
    FILES,
    load_json,
    validate_cycle,
)


class TestLLMCycle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.saved = {
            name: load_json(path)
            for name, path in FILES.items()
        }

    def check(self, data, check_files=False):
        return validate_cycle(
            data["evidence"],
            data["design"],
            data["critic"],
            data["revision"],
            file_paths=FILES if check_files else None,
        )

    def fresh_data(self):
        return copy.deepcopy(self.saved)

    def test_complete_cycle(self):
        result = self.check(self.fresh_data(), True)
        self.assertEqual(
            result["evidence_identity_checks"], "PASSED"
        )
        self.assertEqual(
            result["provenance_checks"], "PASSED"
        )

    def test_design_candidate_consistency(self):
        data = self.fresh_data()
        data["critic"]["candidate_name"] = "Different catalyst"
        with self.assertRaises(ValueError):
            self.check(data)

    def test_reject_unknown_design_reference(self):
        data = self.fresh_data()
        data["design"]["proposal"][
            "supporting_evidence"
        ][0]["measurement_id"] = "fabricated-id"
        with self.assertRaises(ValueError):
            self.check(data)

    def test_reject_unknown_critic_reference(self):
        data = self.fresh_data()
        data["critic"]["critique"][
            "scientific_findings"
        ][0]["linked_measurement_ids"] = ["fabricated-id"]
        with self.assertRaises(ValueError):
            self.check(data)

    def test_reject_missing_critic_response(self):
        data = self.fresh_data()
        data["revision"]["revision"][
            "finding_responses"
        ].pop()
        with self.assertRaises(ValueError):
            self.check(data)

    def test_reject_fabricated_fe_prediction(self):
        data = self.fresh_data()
        data["revision"]["predicted_fe_percent"] = 90.0
        with self.assertRaises(ValueError):
            self.check(data)

    def test_reject_missing_falsification(self):
        data = self.fresh_data()
        data["revision"]["revision"][
            "controlled_experiments"
        ][0]["outcome_challenging_hypothesis"] = ""
        with self.assertRaises(ValueError):
            self.check(data)


if __name__ == "__main__":
    unittest.main()
