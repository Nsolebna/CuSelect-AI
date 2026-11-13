"""Compare registered atomistic models and inspect saved computational evidence."""

import hashlib
import json

import streamlit as st

from .i18n import t
import streamlit.components.v1 as components

from .geometry_store import load_geometry_registry
from .molecular_viewer import build_structure_html


def render_structures(root, candidate_ids):
    st.caption(
        "Unrelaxed periodic slabs, pending human visual review. "
        "These atomistic models represent substitutional Ag in Cu, while the historical "
        "experimental proposal concerns patterned Ag islands on Cu foil. "
        "Atom sizes and neighbour guides are illustrative."
    )
    for column, candidate_id in zip(st.columns(len(candidate_ids)), candidate_ids):
        with column:
            try:
                html, record = build_structure_html(root, candidate_id)
            except (OSError, ValueError) as error:
                st.error(f"Could not verify {candidate_id}: {error}")
                continue

            st.markdown(f"**{candidate_id}**")
            st.caption(
                f"Cu({record['facet']}) · {record['chemical_formula']} · "
                f"{record['atom_count']} atoms · "
                f"{record['motif'].replace('_', ' ')}"
            )
            separation = record.get("ag_ag_minimum_image_distance_A", "").strip()
            if separation:
                st.write(f"Ag–Ag minimum-image distance **{float(separation):.3f} Å**")
            else:
                st.write("Ag–Ag minimum-image distance · unavailable for this geometry")
            if hasattr(st, "iframe"):
                st.iframe(html, height=365, alt=f"Interactive atomic structure {candidate_id}")
            else:
                components.html(html, height=365, scrolling=False)
            with st.expander(f"Geometry provenance · {candidate_id}"):
                st.write("**Source method**", record["source_method"])
                st.write("**Supercell**", record["supercell_size"])
                st.write("**PBC (x, y, z)**", record["pbc_xyz"])
                st.write("**Geometry SHA-256**")
                st.code(record["geometry_sha256"])


def render_computational_evidence(root):
    processed = root / "data/processed"
    registry_path = processed / "16_computational_registry/computational_evidence_v2.json"
    critique_path = processed / "17_computational_critique/scientific_critique_v2.json"
    try:
        registry_bytes = registry_path.read_bytes()
        registry = json.loads(registry_bytes)
        critique = json.loads(critique_path.read_bytes())
        if hashlib.sha256(registry_bytes).hexdigest() != critique["registry_sha256"]:
            raise ValueError("Saved critique and registry fingerprints differ")
        comparisons = registry["comparisons"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        st.error(f"Computational evidence unavailable: {error}")
        return

    st.subheader("Saved clean-slab comparisons")
    st.caption(f"{registry['system']} · adjacent (NN) versus separated (SEP) Ag pair")
    st.write(critique["supported_conclusion"])

    reassessment = critique.get("cutoff_reassessment")
    if reassessment:
        st.markdown("### GPAW cutoff stability")
        st.metric(
            "Relative-energy change: 350 → 450 eV",
            f"{reassessment['cutoff_sensitivity_mev']:+.3f} meV",
        )
        st.caption(
            "Matched 6×6×1 GPAW/PBE calculations. "
            "Fixed MACE-relaxed geometries; numerical convergence "
            "and catalytic selectivity are not established."
        )
    st.warning(
        "Preliminary clean-slab calculations. Dense-grid cutoff convergence is incomplete, "
        "and GPAW-PBE evaluated MACE-relaxed geometries. These comparisons cannot "
        "establish reaction activity, ethylene selectivity or Faradaic efficiency."
    )
    st.dataframe([
        {
            "Method": row["method"],
            "Geometry": row["geometry"],
            "Run": row.get("run_id", ""),
            "SEP − NN (eV)": row["delta_sep_minus_nn_ev"],
            "Evidence status": row["evidence_status"].replace("_", " "),
        }
        for row in comparisons
    ], hide_index=True)
    with st.expander("Computational critique and source records"):
        for finding in critique["findings"]:
            st.write(f"**{finding['finding'].replace('_', ' ').capitalize()}** · {finding['details']}")
        st.caption("Human scientific review required.")
        st.write("**Saved registry SHA-256**")
        st.code(critique["registry_sha256"])
        st.download_button(
            "Download comparison registry", registry_bytes,
            registry_path.name, "application/json",
        )



def render_dft_convergence(root):
    """Display saved DFT results without executing calculations."""
    processed = root / "data/processed"

    configurations = [
        ("350 eV", "14_dft_kpoint_6x6", 350),
        ("450 eV", "19_dft_cutoff_450_6x6", 450),
    ]

    st.subheader("DFT cutoff convergence")
    st.caption(
        "GPAW/PBE · 6×6×1 k-points · MACE-relaxed geometries. "
        "Energy differences are per Ag₂Cu₃₄ simulation cell."
    )

    rows = []

    for label, folder, cutoff in configurations:
        energies = {}
        complete = True

        for candidate in ("nn", "sep"):
            filename = (
                f"{candidate}_pbe_{cutoff}ev_6x6x1.json"
            )
            path = processed / folder / filename

            if not path.is_file():
                complete = False
                continue

            try:
                record = json.loads(
                    path.read_text(encoding="utf-8")
                )
                if (
                    record.get("cutoff_ev") != cutoff
                    or record.get("kpoints") != [6, 6, 1]
                    or record.get("scf_completed_without_exception")
                    is not True
                ):
                    raise ValueError("Unexpected DFT result metadata")

                energies[candidate] = record["energy_ev"]

            except (OSError, ValueError, TypeError, KeyError):
                st.warning(
                    f"{candidate.upper()} at {cutoff} eV "
                    "could not be verified."
                )
                complete = False

        delta = (
            energies["sep"] - energies["nn"]
            if complete and len(energies) == 2
            else None
        )

        rows.append({
            "Cutoff": label,
            "NN energy (eV)": energies.get("nn"),
            "SEP energy (eV)": energies.get("sep"),
            "SEP − NN (eV)": delta,
            "Status": "Pair complete" if delta is not None
                      else "Incomplete",
        })

    st.dataframe(rows, hide_index=True)

    if all(row["Status"] == "Pair complete" for row in rows):
        difference = (
            rows[1]["SEP − NN (eV)"]
            - rows[0]["SEP − NN (eV)"]
        )
        st.metric(
            "Change in relative energy, 350 → 450 eV",
            f"{difference * 1000:+.3f} meV",
        )
    else:
        st.info(
            "The 450 eV comparison is incomplete. "
            "No convergence conclusion is available."
        )

    st.warning(
        "These are fixed-geometry clean-slab single-point results. "
        "Cutoff convergence, DFT geometry relaxation, "
        "and electrochemical selectivity remain unverified."
    )

def render_catalyst_explorer(root):
    st.title(t("catalyst.title"))
    view = st.radio(
        "Catalyst view", ["3D structures", "Computational evidence"],
        horizontal=True, label_visibility="collapsed",
    )
    if view == "Computational evidence":
        render_computational_evidence(root)
        render_dft_convergence(root)
        return

    try:
        registry = load_geometry_registry(root)
    except (OSError, ValueError) as error:
        st.error(f"Geometry registry verification failed: {error}")
        return

    options = {row["candidate_id"]: row for row in registry}

    def label(candidate_id):
        return candidate_id + " · " + options[candidate_id]["motif"].replace("_", " ")

    left, right = st.columns(2)
    primary = left.selectbox(
        t("catalyst.primary"), options, index=list(options).index("CU-001-100-AG2-NN"),
        format_func=label,
    )
    single = "Single structure"
    comparison = right.selectbox(
        t("catalyst.comparison"), [single, *options],
        index=list(options).index("CU-001-100-AG2-SEP") + 1,
        format_func=lambda candidate_id: label(candidate_id) if candidate_id != single else single,
    )
    candidates = [primary]
    if comparison not in (single, primary):
        candidates.append(comparison)
    render_structures(root, candidates)
