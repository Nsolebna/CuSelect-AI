
# CuSelect-AI — Phase II
# Module: src/cuselect/scientific_critic.py
#
# PSEUDOCODE
# 1. Accept a structured scientific assertion.
# 2. Reject unsupported scientific claim categories.
# 3. Load evidence and geometries through trusted loaders.
# 4. Validate cited evidence and candidate identities.
# 5. Compare reported FE, product, catalyst and potential
#    against the approved experimental record.
# 6. Permit registered geometries as hypotheses only.
# 7. Construct canonical responses from trusted records.
# 8. Abstain on fabricated, altered or unsupported claims.
# 9. Never grant modeling approval or alter source files.

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
import math
import re

from .evidence_store import load_verified_corpus
from .geometry_store import load_geometry_registry


ClaimKind = Literal[
    "reported_fe",
    "reported_ratio",
    "structure_hypothesis",
    "catalyst_superiority",
    "energy_prediction",
    "mechanistic_certainty",
    "durability_claim",
    "evaluation_claim",
    "instructions_as_evidence",
]

Decision = Literal[
    "evidence_only",
    "hypothesis_only",
    "abstain",
]


@dataclass(frozen=True)
class ScientificAssertion:
    assertion_id: str
    kind: ClaimKind
    evidence_ids: tuple[str, ...] = ()
    candidate_ids: tuple[str, ...] = ()
    catalyst: str = ""
    product: str = ""
    fe_percent: float | None = None
    potential_v_rhe: float | None = None
    statement: str = ""


@dataclass(frozen=True)
class CriticDecision:
    assertion_id: str
    decision: Decision
    reason_codes: tuple[str, ...]
    cited_ids: tuple[str, ...] = ()
    candidate_ids: tuple[str, ...] = ()
    canonical_response: str = ""
    scientific_modeling_approved: bool = False


SUPPORTED_TYPES = {
    "reported_fe",
    "reported_ratio",
    "structure_hypothesis",
}

BLOCKED_TYPES = {
    "catalyst_superiority",
    "energy_prediction",
    "mechanistic_certainty",
    "durability_claim",
    "evaluation_claim",
    "instructions_as_evidence",
}

MAX_CRITIC_CANDIDATES = 2


def text_key(text: str) -> str:
    """Normalize whitespace without rewriting scientific claims."""
    return " ".join(str(text).strip().split())


def extract_potential(conditions: str) -> float | None:
    """Extract a single explicitly reported potential vs RHE."""

    standardized = (
        str(conditions)
        .replace("−", "-")
        .replace("–", "-")
    )

    matches = re.findall(
        r"(?<![\w.])([+-]?\d+(?:\.\d+)?)\s*V\s*vs\s*RHE",
        standardized,
        flags=re.IGNORECASE,
    )

    return float(matches[0]) if len(matches) == 1 else None


def _abstain(
    assertion: ScientificAssertion,
    reason: str,
) -> CriticDecision:
    return CriticDecision(
        assertion_id=assertion.assertion_id,
        decision="abstain",
        reason_codes=(reason,),
    )


def _valid_ids(ids: object) -> bool:
    return (
        isinstance(ids, tuple)
        and all(
            isinstance(value, str) and bool(value.strip())
            for value in ids
        )
    )


def _finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def review_scientific_assertion(
    assertion: ScientificAssertion,
    *,
    project_root: str | Path = ".",
) -> CriticDecision:
    """Apply Notebook 08's narrow scientific falsification rules."""

    if not isinstance(assertion, ScientificAssertion):
        raise TypeError("Expected ScientificAssertion")

    if (
        not isinstance(assertion.assertion_id, str)
        or not assertion.assertion_id.strip()
    ):
        return _abstain(assertion, "missing_assertion_id")

    if assertion.kind in BLOCKED_TYPES:
        return _abstain(
            assertion,
            "unsupported_scientific_assertion_type",
        )

    if assertion.kind not in SUPPORTED_TYPES:
        return _abstain(assertion, "unknown_assertion_type")

    if (
        not _valid_ids(assertion.evidence_ids)
        or not _valid_ids(assertion.candidate_ids)
    ):
        return _abstain(assertion, "invalid_reference_format")

    if (
        len(set(assertion.evidence_ids)) != len(assertion.evidence_ids)
        or len(set(assertion.candidate_ids))
        != len(assertion.candidate_ids)
    ):
        return _abstain(assertion, "duplicate_reference_id")

    # These loaders raise integrity errors rather than silently
    # accepting altered evidence or geometry files.
    corpus = load_verified_corpus(project_root)
    registry = load_geometry_registry(project_root)

    evidence_by_id = {
        record["evidence_id"]: record
        for record in corpus
    }

    geometry_by_id = {
        record["candidate_id"]: record
        for record in registry
    }

    if not set(assertion.evidence_ids) <= set(evidence_by_id):
        return _abstain(
            assertion,
            "unapproved_or_fabricated_citation",
        )

    if not set(assertion.candidate_ids) <= set(geometry_by_id):
        return _abstain(assertion, "unknown_geometry")

    # Geometry hypotheses cannot become performance claims.
    if assertion.kind == "structure_hypothesis":
        if (
            assertion.evidence_ids
            or not (
                1 <= len(assertion.candidate_ids)
                <= MAX_CRITIC_CANDIDATES
            )
        ):
            return _abstain(
                assertion,
                "invalid_hypothesis_input",
            )

        blocked_language = (
            "best", "better", "superior", "stable",
            "selective", "predicted", "guaranteed",
            "higher fe",
        )

        if any(
            term in assertion.statement.lower()
            for term in blocked_language
        ):
            return _abstain(
                assertion,
                "performance_language_in_geometry_hypothesis",
            )

        for candidate_id in assertion.candidate_ids:
            record = geometry_by_id[candidate_id]

            if (
                record["geometry_status"] != "unrelaxed"
                or record["structure_review_status"]
                != "pending_visual_review"
                or record["approved_for_modeling"]
                .strip().lower() != "false"
            ):
                return _abstain(
                    assertion,
                    "unreviewed_geometry_not_eligible_for_approval",
                )

        return CriticDecision(
            assertion_id=assertion.assertion_id,
            decision="hypothesis_only",
            reason_codes=(
                "unrelaxed_geometry",
                "human_visual_review_and_reference_calculation_required",
            ),
            candidate_ids=assertion.candidate_ids,
            canonical_response=(
                "Registered Cu–Ag geometry hypothesis; "
                "no stability, energy, or selectivity claim."
            ),
        )

    # Experimental claims must cite exactly one reviewed record.
    if assertion.candidate_ids or len(assertion.evidence_ids) != 1:
        return _abstain(
            assertion,
            "exactly_one_evidence_id_required",
        )

    source = evidence_by_id[assertion.evidence_ids[0]]

    if (
        assertion.statement
        and text_key(assertion.statement)
        != text_key(source["claim_paraphrase"])
    ):
        return _abstain(
            assertion,
            "noncanonical_scientific_text_requires_review",
        )

    if source["review_status"] != "human_verified":
        return _abstain(
            assertion,
            "claim_not_human_verified",
        )

    if assertion.kind == "reported_fe":
        if not (
            source["fe_product"].strip()
            and source["faradaic_efficiency_percent"].strip()
        ):
            return _abstain(
                assertion,
                "not_a_structured_fe_measurement",
            )

        if assertion.catalyst.strip() != source["catalyst_system"].strip():
            return _abstain(
                assertion,
                "catalyst_identity_mismatch",
            )

        if (
            assertion.product.strip().upper()
            != source["fe_product"].strip().upper()
        ):
            return _abstain(assertion, "product_mismatch")

        source_potential = extract_potential(source["conditions"])

        if (
            source_potential is None
            or not _finite_number(assertion.fe_percent)
            or not _finite_number(assertion.potential_v_rhe)
        ):
            return _abstain(
                assertion,
                "required_numerical_metadata_missing",
            )

        if not math.isclose(
            assertion.fe_percent,
            float(source["faradaic_efficiency_percent"]),
            rel_tol=0,
            abs_tol=1e-9,
        ):
            return _abstain(
                assertion,
                "faradaic_efficiency_mismatch",
            )

        if not math.isclose(
            assertion.potential_v_rhe,
            source_potential,
            rel_tol=0,
            abs_tol=1e-9,
        ):
            return _abstain(assertion, "potential_mismatch")

        response = (
            f"{source['claim_paraphrase']} "
            f"[{source['evidence_id']}] "
            f"DOI: {source['doi']}; "
            f"source: {source['source_extent']}, "
            f"{source['source_location']}; "
            f"conditions: {source['conditions']}."
        )

        return CriticDecision(
            assertion_id=assertion.assertion_id,
            decision="evidence_only",
            reason_codes=(
                "exact_source_match",
                "reported_fe_not_prediction",
            ),
            cited_ids=assertion.evidence_ids,
            canonical_response=response,
        )

    # Product ratios are not structured FE measurements.
    if assertion.kind == "reported_ratio":
        if (
            source["fe_product"].strip()
            or source["faradaic_efficiency_percent"].strip()
        ):
            return _abstain(
                assertion,
                "ratio_not_a_faradaic_efficiency",
            )

        if "ratio" not in source["target_or_observation"].lower():
            return _abstain(
                assertion,
                "ratio_observation_mismatch",
            )

        if (
            assertion.fe_percent is not None
            or assertion.potential_v_rhe is not None
            or assertion.product.strip()
        ):
            return _abstain(
                assertion,
                "unstructured_ratio_cannot_gain_fe_or_potential",
            )

        if (
            assertion.catalyst
            and assertion.catalyst.strip()
            != source["catalyst_system"].strip()
        ):
            return _abstain(
                assertion,
                "catalyst_identity_mismatch",
            )

        response = (
            f"{source['claim_paraphrase']} "
            f"[{source['evidence_id']}] "
            f"DOI: {source['doi']}; "
            f"source: {source['source_extent']}, "
            f"{source['source_location']}. "
            "No structured FE or potential inferred."
        )

        return CriticDecision(
            assertion_id=assertion.assertion_id,
            decision="evidence_only",
            reason_codes=(
                "exact_reviewed_paraphrase",
                "ratio_not_fe",
            ),
            cited_ids=assertion.evidence_ids,
            canonical_response=response,
        )

    return _abstain(assertion, "fail_closed")
