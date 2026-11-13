
from pathlib import Path
from datetime import datetime
import shutil
import ast

page = Path("app/pages/1_Multi_Agent_Design.py")

required = [
    Path("src/cuselect/agents/llm_question_interpreter.py"),
    Path("src/cuselect/agents/question_interpreter.py"),
    Path("src/cuselect/agents/objective_discovery.py"),
]

if not page.is_file() or not all(p.is_file() for p in required):
    raise SystemExit("STOP: Required files missing. No changes made.")

original = page.read_text()

start_marker = "# DISCOVERY EXECUTION"
end_marker = "# DISCOVERY RESULTS"

if original.count(start_marker) != 1 or original.count(end_marker) != 1:
    raise SystemExit("STOP: Unexpected page structure. No changes made.")

replacement = '''
# DISCOVERY EXECUTION — LLM + SCIENTIFIC CHECKS

if submitted:
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    src = str(root / "src")

    if src not in sys.path:
        sys.path.insert(0, src)

    from cuselect.agents.question_interpreter import interpret_request
    from cuselect.agents.llm_question_interpreter import (
        interpret_with_llm,
        validate_interpretation,
    )
    from cuselect.agents.objective_discovery import discover_for_request

    st.session_state.pop("discovery_result", None)
    st.session_state.pop("llm_interpretation", None)

    preliminary = interpret_request(objective, product)

    if preliminary["status"] != "ready":
        st.warning(preliminary["message"])

    else:
        try:
            with st.spinner("Understanding your research question..."):
                intent = interpret_with_llm(objective)

            validation = validate_interpretation(
                intent, product, preliminary
            )

            if validation["status"] != "ready":
                st.warning(validation["message"])

            else:
                st.session_state["llm_interpretation"] = (
                    validation["interpretation"]
                )

                st.session_state["discovery_request"] = {
                    "objective": objective.strip(),
                    "target_product": product,
                    "discovery_focus": focus,
                    "interpretation": validation["interpretation"],
                }

                with st.spinner("Reviewing approved evidence..."):
                    result = discover_for_request(
                        objective=objective,
                        target_product=product,
                        discovery_focus=focus,
                    )

                st.session_state["discovery_result"] = result

        except Exception as exc:
            st.error(
                "LLM-assisted discovery failed. "
                "No results were generated."
            )
            with st.expander("Technical error"):
                st.exception(exc)


# INTERPRETED QUESTION

interpretation = st.session_state.get("llm_interpretation")

if interpretation:
    with st.expander("Interpreted research question"):
        st.write("**Target product:**",
                 interpretation["target_product"])
        st.write("**Catalyst family:**",
                 interpretation["catalyst_family"])
        st.write("**Research goal:**",
                 interpretation["research_goal"])

        if interpretation.get("cell_configuration"):
            st.write("**Cell configuration:**",
                     interpretation["cell_configuration"])

        if interpretation.get("current_density_ma_cm2") is not None:
            st.write("**Current density:**",
                     interpretation["current_density_ma_cm2"],
                     "mA/cm²")

        if interpretation.get("constraints"):
            st.write("**Constraints:**",
                     interpretation["constraints"])

        st.caption(
            "LLM-extracted information; experimental "
            "conditions are not independently verified."
        )


'''

start = original.index(start_marker)
end = original.index(end_marker, start)

updated = original[:start] + replacement + original[end:]

ast.parse(updated)

backup_dir = Path("backups/discover")
backup_dir.mkdir(parents=True, exist_ok=True)

backup = backup_dir / (
    "discover_before_live_llm_"
    + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    + ".py"
)

shutil.copy2(page, backup)
page.write_text(updated)

print("SUCCESS: Live LLM connected to Discover.")
print("Existing scientific engine preserved.")
print("Backup:", backup)
