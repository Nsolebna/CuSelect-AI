"""Create a versioned, additive Scientific Critic instruction set.

No changes to the production agent.
No model requests or DFT calculations.
"""

# PSEUDOCODE
# 1. Import the original Scientific Critic instructions.
# 2. Define a narrowly scoped mechanistic reasoning extension.
# 3. Distinguish mediation, source attribution and pathway.
# 4. Require discriminating experiments when relevant.
# 5. Preserve the original instructions and response schema.
# 6. Save a new version with source fingerprints.
# 7. Refuse to overwrite an existing version.

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.agents.llm_critic_agent import (
    CRITIC_INSTRUCTIONS,
)

OUTPUT = (
    ROOT / "data/benchmarks/critic_instructions_v2.json"
)

EXTENSION = """
ADDITIONAL MECHANISTIC EVIDENCE DISCIPLINE — VERSION 2

Apply these requirements when evaluating tandem catalysts,
CO-mediated mechanisms, carbon-source claims or intersite
transport. Do not force these mechanisms into unrelated cases.

1. SEPARATE THREE DISTINCT CLAIMS

A. CO mediation:
Does variation in CO availability contribute causally
to a measured reaction response?

B. Carbon-source attribution:
Is there evidence that carbon from a specified source,
such as Ag-generated CO, contributes to a Cu product?

C. Transport pathway:
Is the relevant species transported through a continuous
surface pathway, through the electrolyte, or through
the gas phase?

Evidence for one claim does not establish the others.

2. DISTINGUISH OBSERVATION FROM ATTRIBUTION

An increase in ethylene FE or production does not establish
Ag-to-Cu CO transfer.

A correlation with local CO availability does not uniquely
identify the source of that CO.

Isotopic carbon incorporation can support source attribution
under validated conditions but cannot alone establish
contact-dependent surface spillover.

3. DESIGN DISCRIMINATING EXPERIMENTS

When carbon origin is central to a proposed mechanism,
consider whether source-resolved isotope tracing or
an equivalent validated attribution strategy is feasible.

If suitable, specify what would be labeled, which products
would be measured, relevant controls, expected contrasting
outcomes and limitations of interpretation.

Consider isotope exchange, carbonate reservoirs, background
carbon sources, crossover, analytical sensitivity,
carbon balances and time-dependent responses.

Do not automatically require isotope experiments when
the evidence question can be answered more directly.

4. SEPARATE CONTACT DEPENDENCE FROM CO MEDIATION

Where appropriate, compare direct-contact and noncontact
architectures while considering changes in Cu state,
local CO availability, flow, pH and transport.

A response without contact challenges the necessity of
surface spillover but can remain compatible with
fluid-mediated tandem CO delivery.

5. EXPRESS FALSIFIABLE OUTCOMES

For each key mechanistic claim, identify the observation
that would challenge it.

State when a null result is inconclusive because of
insufficient sensitivity, incomplete controls or
unmatched operating conditions.

6. PRESERVE SCIENTIFIC UNCERTAINTY

Do not invent measurements, isotope results, literature
support or experimental feasibility.

Clearly distinguish supported findings, reasoned
hypotheses and unresolved questions.

Recommend experimental advancement only when the
supplied evidence and intended decision justify it.
""".strip()


def digest(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def build_instructions():
    if not isinstance(CRITIC_INSTRUCTIONS, str):
        raise TypeError("Original instructions must be text.")

    if not CRITIC_INSTRUCTIONS.strip():
        raise ValueError("Original instructions are empty.")

    combined = (
        CRITIC_INSTRUCTIONS.rstrip()
        + "\n\n"
        + EXTENSION
    )

    return {
        "schema_version": "1.0",
        "instruction_version": "2.0",
        "change_type": "additive_mechanistic_extension",
        "source_version": "production_critic_v1",
        "original_instructions_sha256": digest(
            CRITIC_INSTRUCTIONS
        ),
        "extension_sha256": digest(EXTENSION),
        "combined_instructions_sha256": digest(combined),
        "extension": EXTENSION,
        "combined_instructions": combined,
        "production_agent_modified": False,
        "evaluation_status": "not_evaluated",
        "human_scientific_approval": False,
        "scientific_reliability_established": False,
    }


def main():
    if OUTPUT.exists():
        raise SystemExit(
            f"Refusing to overwrite existing file: {OUTPUT}"
        )

    result = build_instructions()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("x", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")

    print("\nCUSELECT-AI — SCIENTIFIC CRITIC V2")
    print("=" * 60)
    print("Instruction version: 2.0")
    print("Original instructions preserved: Yes")
    print("Mechanistic extension: Added")
    print("Production agent modified: No")
    print("New model evaluations: 0")
    print("API requests: 0")
    print("Output:", OUTPUT)


if __name__ == "__main__":
    main()
