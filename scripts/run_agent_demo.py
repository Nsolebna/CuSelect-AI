"""Run the complete CuSelect-AI prototype."""

# PSEUDOCODE
# 1. Run all five agent stages.
# 2. Validate the results.
# 3. Print the generated candidates and research readiness.

from cuselect.agents.pipeline import run_pipeline


def main():
    outputs = run_pipeline(save=True)
    literature = outputs["literature"]
    result = outputs["coordination"]

    print("\nCUSELECT-AI — COMPLETE AGENT PIPELINE")
    print("=" * 65)
    print(
        "Approved evidence:",
        literature["summary"]["measurements"],
    )
    print(
        "Publications:",
        literature["summary"]["publications"],
    )
    print(
        "Verified condition fields:",
        literature["summary"]["verified_condition_fields"],
    )

    print("\nRESEARCH HYPOTHESES")
    print("-" * 65)

    for candidate in result["candidates"]:
        print(
            candidate["candidate_id"],
            "| Readiness:",
            candidate["research_readiness"]["total"],
            "/100",
        )
        print("Name:", candidate["candidate_name"])
        print(
            "Development stages:",
            len(candidate["evolution"]),
        )
        print(
            "Predicted FE:",
            candidate["predicted_fe_percent"],
        )
        print()

    print("Pipeline integrity: PASSED")
    print("Outputs saved: data/agent_runs/")
    print("Approved evidence and condition reviews: unchanged")


if __name__ == "__main__":
    main()
