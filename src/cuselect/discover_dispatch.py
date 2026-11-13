"""Route Discover questions to local or global research."""

import re
from pathlib import Path

from dotenv import load_dotenv

from cuselect.research_router import route_question
from cuselect.research_controller import execute_research
from cuselect.hybrid_answer_controller import answer_research_question
from cuselect.scientific_query import interpret_query


def execute_discover_question(
    question,
    *,
    project_root=".",
    router=None,
    local_executor=None,
    hybrid_executor=None,
):
    question = str(question).strip()
    if not question:
        raise ValueError("Research question is required.")

    root = Path(project_root)
    load_dotenv(dotenv_path=root / ".env")

    router = router or route_question
    local_executor = local_executor or execute_research
    hybrid_executor = hybrid_executor or answer_research_question

    # Explicit local-benchmark questions use the candidate registry.
    # Worldwide research still uses the global literature pathway.
    q = question.lower()
    global_scope = any(
        term in q for term in (
            "worldwide", "state of the art",
            "latest", "world record", "so far",
        )
    )

    if "benchmark" in q and not global_scope:
        return answer_local_benchmarks(
            question, project_root=root
        )


    # LOCAL DATABASE ROUTING PRIORITY
    # Explicit internal-evidence questions do not require
    # an external literature search or an LLM router call.
    import re
    from types import SimpleNamespace

    q = question.lower()

    local_scope = bool(re.search(
        r"\b(my reviewed literature|my reviewed papers|"
        r"my reviewed database|my database|"
        r"my local evidence|my internal evidence|"
        r"in my reviewed literature)\b",
        q,
    ))

    global_scope = bool(re.search(
        r"\b(worldwide|globally|latest|"
        r"state.of.the.art|world record|so far)\b",
        q,
    ))

    if local_scope and not global_scope:
        local_route = SimpleNamespace(
            workflow="literature_research",
            research_goal=question,
            required_capabilities=[
                "verified_evidence_retrieval"
            ],
            missing_information=[],
            scientific_constraints=[],
            routing_reason="Explicit local evidence scope",
        )

        result = local_executor(
            question,
            project_root=root,
            router=lambda _question: local_route,
        )

        return {
            **result,
            "workflow": "local_literature_research",
        }

    # SCIENTIFIC QUERY UNDERSTANDING
    # Explicit local-evidence requests are handled above.
    query_context = interpret_query(question)

    if query_context["context_applied"]:
        response = hybrid_executor(
            query_context["search_question"],
            project_root=root,
            max_papers=5,
        )

        return {
            **response,
            "question": question,
            "interpreted_question": (
                query_context["search_question"]
            ),
            "query_context_note": (
                query_context["context_note"]
            ),
            "inferred_domain": query_context["domain"],
        }

    # SCIENTIFIC MECHANISM ROUTING
    # Explicit reviewed-database requests were handled above.
    # General Ag/Cu mechanism questions need literature research.
    mechanism_intent = bool(re.search(
        r"\b(why|how|mechanism|mechanistic|"
        r"role of|effect of|purpose of|benefit of)\b",
        q,
    ))

    ag_mentioned = bool(re.search(
        r"\b(ag|silver)\b", q
    ))

    cu_mentioned = bool(re.search(
        r"\b(cu|copper)\b", q
    ))

    if mechanism_intent and ag_mentioned and cu_mentioned:
        return hybrid_executor(
            question,
            project_root=root,
            max_papers=5,
        )

    route = router(question)
    workflow = getattr(route, "workflow", "")

    current_research = bool(re.search(
        r"\b(latest|recent|current|worldwide|"
        r"so far|state.of.the.art|highest reported|"
        r"world record)\b",
        question.lower(),
    ))

    use_global = (
        workflow == "literature_research"
        or bool(getattr(route, "needs_literature", False))
        or current_research
    )

    if use_global:
        return hybrid_executor(
            question,
            project_root=root,
            max_papers=5,
        )

    return local_executor(
        question,
        project_root=root,
        router=lambda _question: route,
    )


def answer_local_benchmarks(question, project_root="."):
    """Describe provisional measurements; never claim a ranking."""
    import re
    from cuselect.benchmark_comparison import compare_benchmarks

    q = question.lower()
    product = "ethylene" if re.search(
        r"ethylene|ethene|c2h4", q
    ) else None

    if product is None:
        return {
            "status": "benchmark_summary",
            "answer": (
                "The benchmark registry currently supports "
                "product-specific questions. Please specify "
                "ethylene or another available product."
            ),
            "citations": [],
        }

    result = compare_benchmarks(
        product, project_root=project_root
    )

    lines = [
        f"### {product.capitalize()} benchmark evidence",
        "",
    ]

    if not result["records"]:
        lines.append(
            "No eligible provisional benchmark records "
            "were found for this product."
        )
    else:
        lines.append(
            f"**{result['count']} provisional measurement(s) "
            "available.**"
        )

        for record in result["records"]:
            lines.extend([
                "",
                f"**{record['catalyst']}**",
                f"- Reported FE: "
                f"{record['faradaic_efficiency_percent']}%",
                f"- Cell: {record['cell_configuration'] or 'Unknown'}",
                f"- Electrolyte: "
                f"{record['electrolyte'] or 'Not confirmed'}",
                f"- Reported current density: "
                f"{record['reported_current_density_mA_cm2']} "
                "mA cm⁻² (definition requires checking)",
                f"- Potential: {record['potential_V_vs_RHE']} V vs RHE",
                f"- DOI: {record['doi']}",
                f"- Unresolved conditions: "
                f"{', '.join(record['missing_conditions']) or 'None flagged'}",
            ])

    if result.get("registry_errors"):
        lines.extend([
            "",
            "**Registry warning:** Some records failed validation."
        ])

    lines.extend([
        "",
        "**Interpretation:** These records are provisional. "
        "They do not establish a world record or a validated "
        "catalyst ranking. Different experimental conditions "
        "must be evaluated before quantitative comparison.",
    ])

    return {
        "status": "benchmark_summary",
        "answer": "\n".join(lines),
        "citations": [
            {"doi": r["doi"]}
            for r in result["records"]
        ],
        "execution_mode": "local_benchmark_description",
        "citation_audit_passed": False,
        "files_modified": False,
        "computation_executed": False,
    }
