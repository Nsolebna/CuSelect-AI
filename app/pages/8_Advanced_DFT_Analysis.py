"""CuSelect-AI: read-only DFT relaxation analysis dashboard."""

from pathlib import Path
import json
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "data/processed/22_dft_relaxation_analysis"

st.set_page_config(
    page_title="CuSelect-AI | DFT Analysis",
    page_icon="⚛️",
    layout="wide",
)

st.title("⚛️ DFT Relaxation Analysis")
st.caption(
    "CuSelect-AI | Ag₂Cu₃₄ on Cu(100) | "
    "GPAW/PBE | Exploratory 9-atom fixed-layer protocol"
)

st.info(
    "This dashboard reads saved analysis reports only. "
    "It does not launch GPAW or access an active optimization trajectory."
)


def load_report(filename):
    path = ANALYSIS / filename
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def number(value, decimals=4, suffix=""):
    if value is None or isinstance(value, bool):
        return "Not available"
    try:
        return f"{float(value):.{decimals}f}{suffix}"
    except (TypeError, ValueError, OverflowError):
        return "Not available"


nn = load_report("nn_analysis.json")
sep = load_report("sep_analysis.json")
comparison = load_report("nn_sep_comparison.json")

st.subheader("Calculation overview")

left, right = st.columns(2)

for column, name, report in [
    (left, "NN — Adjacent Ag", nn),
    (right, "SEP — Separated Ag", sep),
]:
    with column:
        st.markdown(f"### {name}")

        if report is None:
            st.warning("Analysis report not generated yet.")
            continue

        status = report.get("analysis_status", "unknown")
        converged = report.get("verified_force_convergence") is True

        if converged:
            st.success("Force-convergence check passed")
        elif status == "complete":
            st.warning("Result available — not verified converged")
        elif status == "error":
            st.error("Analysis error")
        else:
            st.info("Awaiting completed GPAW result")

        st.write("Analysis status:", status)

        if report.get("reason"):
            st.caption(report["reason"])

        st.metric(
            "Total energy (eV)",
            number(report.get("final_energy_eV"), 6),
        )
        st.metric(
            "Maximum movable-atom force (eV/Å)",
            number(report.get("final_fmax_eV_per_A"), 4),
        )
        st.metric(
            "Maximum atomic displacement (Å)",
            number(report.get("max_displacement_A"), 4),
        )
        st.metric(
            "Ag–Ag distance (Å)",
            number(report.get("ag_ag_distance_A"), 4),
        )

        with st.expander("Scientific metadata"):
            st.json({
                "candidate": report.get("candidate"),
                "converged_flag": report.get("converged"),
                "verified_force_convergence": converged,
                "saved_trajectory_frames":
                    report.get("saved_trajectory_frames"),
                "fixed_indices": report.get("fixed_indices"),
                "manifest": report.get("manifest"),
            })

st.divider()
st.subheader("NN vs SEP — Relative stability")

if comparison is None:
    st.info("Comparison report not generated yet.")
else:
    status = comparison.get("status", "unknown")
    st.write("Comparison status:", status)

    delta = comparison.get("delta_energy_meV")

    if (
        status == "provisional_matched_relaxed_comparison"
        and delta is not None
    ):
        st.metric(
            "ΔE = E(SEP) − E(NN)",
            number(delta, 3, " meV"),
        )

        if delta < 0:
            st.write(
                "SEP has lower calculated total energy "
                "under the matched exploratory protocol."
            )
        elif delta > 0:
            st.write(
                "NN has lower calculated total energy "
                "under the matched exploratory protocol."
            )
        else:
            st.write("Both configurations have equal reported energies.")

        st.warning(
            "Provisional comparison: check numerical convergence, "
            "model assumptions and checkpoint integrity before "
            "making a scientific stability claim."
        )
    else:
        st.info(
            "A relaxed-energy comparison is not available yet. "
            "Both candidates must satisfy the analysis convergence "
            "and protocol-matching requirements."
        )

st.divider()
st.subheader("Scientific interpretation")

st.markdown("""
- **Total energy:** Compare configurations with identical composition
  and consistent computational settings.
- **Residual force:** Assess whether the atomic relaxation meets
  the target force criterion.
- **Atomic displacement:** Quantify changes from the input geometry.
- **Ag–Ag distance:** Track the arrangement of the Ag atoms.
- **Evidence status:** Incomplete or unconverged results must not
  be promoted into validated claims by the Scientific Critic.
""")

if st.button("Reload saved reports"):
    st.rerun()

st.caption(
    "Source: data/processed/22_dft_relaxation_analysis/ | "
    "Read-only research visualization"
)


# CUSELECT_DFT_LIVE_MONITOR_V1
import re

st.divider()
st.subheader("Live GPAW calculation monitor")

st.caption(
    "Read-only snapshot of the GPAW log. "
    "SCF energies are intermediate electronic energies, "
    "not final relaxed catalyst energies."
)

RUN_DIR = ROOT / "data/processed/21_dft_relaxation/runs"


def latest_scf(log_path):
    """Return the latest complete GPAW SCF iteration."""
    if not log_path.exists():
        return None

    try:
        lines = log_path.read_text(errors="replace").splitlines()
    except OSError:
        return None

    latest = None

    for line in lines:
        match = re.match(
            r"^\\|iter:\\s*(\\d+)\\s*\\|\\s*([^|]+)\\|"
            r"\\s*([-+]?\\d+(?:\\.\\d+)?)\\s*\\|",
            line,
        )

        if match is None:
            continue

        latest = {
            "iteration": int(match.group(1)),
            "time": match.group(2).strip(),
            "energy_eV": float(match.group(3)),
        }

    return latest


for candidate in ("NN", "SEP"):
    st.markdown(f"#### {candidate}")

    directory = RUN_DIR / candidate.lower()
    log = directory / "gpaw.log"
    result = directory / "result.json"

    if result.exists():
        st.success("Result file available — inspect analysis report")
    elif not log.exists():
        st.info("No GPAW calculation log available")
    else:
        scf = latest_scf(log)

        if scf is None:
            st.info("GPAW log exists; SCF iterations not yet reported")
        else:
            c1, c2, c3 = st.columns(3)

            c1.metric("Latest SCF iteration", scf["iteration"])
            c2.metric("SCF energy (eV)", f'{scf["energy_eV"]:.6f}')
            c3.metric("Iteration time", scf["time"])

            st.caption(
                "This is the latest recorded SCF iteration, "
                "not proof that the process is currently running "
                "or that the calculation has converged."
            )

if st.button("Refresh GPAW monitor"):
    st.rerun()


# CUSELECT_SCF_ENERGY_CHART_V1
import re as _scf_re

st.divider()
st.subheader("SCF energy convergence")

st.caption(
    "Read-only electronic energy history. "
    "Each new SCF cycle is separate from a BFGS geometry step."
)

def load_scf_history(candidate):
    log = (
        ROOT / "data/processed/21_dft_relaxation/runs"
        / candidate.lower() / "gpaw.log"
    )

    if not log.is_file():
        return []

    try:
        lines = log.read_text(errors="replace").splitlines()
    except OSError:
        return []

    records = []
    cycle = 0
    for line in lines:
        if line.strip() == "SCF iterations":
            cycle += 1
            continue

        match = _scf_re.match(
            r"^\\|iter:\\s*(\\d+)\\|\\s*([^|]+)\\|"
            r"\\s*([-+]?\\d+(?:\\.\\d+)?)\\s*\\|",
            line,
        )

        if match:
            records.append({
                "SCF cycle": cycle,
                "Iteration": int(match.group(1)),
                "Time": match.group(2).strip(),
                "Energy (eV)": float(match.group(3)),
            })

    return records


for _candidate in ("NN", "SEP"):
    st.markdown(f"#### {_candidate} SCF history")
    _history = load_scf_history(_candidate)

    if not _history:
        st.info("No SCF iteration data available.")
        continue

    # Show only the latest SCF cycle.
    _latest_cycle = max(r["SCF cycle"] for r in _history)
    _current = [
        r for r in _history
        if r["SCF cycle"] == _latest_cycle
    ]

    st.line_chart(
        {
            "SCF energy (eV)": [
                r["Energy (eV)"] for r in _current
            ]
        },
        x_label="SCF iteration index",
        y_label="Energy (eV)",
    )

    st.caption(
        f"Cycle {_latest_cycle} | "
        f"{len(_current)} recorded iterations | "
        "Latest energy: "
        f'{_current[-1]["Energy (eV)"]:.6f} eV'
    )

    with st.expander(f"{_candidate} SCF data"):
        st.dataframe(_current, width="stretch")

st.caption(
    "Intermediate SCF energies must not be interpreted "
    "as relaxed-structure energies or adsorption energies."
)
