"""Integrity tests for the CuSelect-AI agent pipeline."""

# PSEUDOCODE
# 1. Build pipeline using approved local evidence.
# 2. Check every candidate reaches the coordinator.
# 3. Check no predicted FE values are fabricated.
# 4. Check malformed IDs and unsupported evidence are rejected.
# 5. Confirm running in test mode does not change source files.

import copy
import hashlib
import unittest

from cuselect.agents.pipeline import (
    DATA,
    build_pipeline,
    run_pipeline,
    validate_pipeline,
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestAgentPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.outputs = run_pipeline(save=False)

    def test_all_five_stages(self):
        self.assertEqual(
            set(self.outputs),
            {
                "literature",
                "design",
                "critique",
                "scoring",
                "coordination",
            },
        )

    def test_candidate_consistency(self):
        self.assertTrue(validate_pipeline(self.outputs))

        designs = self.outputs["design"]["candidates"]
        coordinated = self.outputs["coordination"]["candidates"]

        self.assertEqual(len(designs), len(coordinated))

    def test_no_fabricated_predictions(self):
        for stage in ["design", "scoring", "coordination"]:
            for candidate in self.outputs[stage]["candidates"]:
                self.assertIsNone(
                    candidate["predicted_fe_percent"]
                )

    def test_evidence_traceability(self):
        evidence_ids = {
            item["measurement_id"]
            for item in self.outputs["literature"]["evidence"]
        }

        for candidate in self.outputs["design"]["candidates"]:
            self.assertTrue(
                set(candidate["evidence_measurement_ids"])
                <= evidence_ids
            )

    def test_duplicate_design_rejected(self):
        corrupted = copy.deepcopy(self.outputs)

        first = copy.deepcopy(
            corrupted["design"]["candidates"][0]
        )
        corrupted["design"]["candidates"].append(first)

        with self.assertRaises(ValueError):
            validate_pipeline(corrupted)

    def test_unsupported_prediction_rejected(self):
        corrupted = copy.deepcopy(self.outputs)

        corrupted["coordination"]["candidates"][0][
            "predicted_fe_percent"
        ] = 99.0

        with self.assertRaises(ValueError):
            validate_pipeline(corrupted)

    def test_source_files_unchanged(self):
        paths = [
            DATA / "approved_evidence.json",
            DATA / "conditions_review.json",
        ]

        before = {
            str(path): sha256(path)
            for path in paths if path.exists()
        }

        run_pipeline(save=False)

        after = {
            str(path): sha256(path)
            for path in paths if path.exists()
        }

        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
