
# CuSelect-AI — Phase II
# Module: src/cuselect/geometry_store.py
#
# PSEUDOCODE
# 1. Load the registered geometry metadata and manifest.
# 2. Verify candidate counts, filenames, and unique IDs.
# 3. Independently reload each exported ASE structure.
# 4. Reconstruct the exact Notebook 04 geometry fingerprint.
# 5. Check chemistry, atomic counts, PBC, and layer metadata.
# 6. Require all modeling and review restrictions to remain intact.
# 7. Reject inconsistent structures without modifying any files.
# 8. Return validated registry records to the Design Agent.

import csv
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from ase.io import read


class GeometryIntegrityError(ValueError):
    """Raised when registered geometry data fail validation."""


def geometry_fingerprint(atoms) -> str:
    """Reproduce the canonical SHA-256 fingerprint from Notebook 04."""

    payload = {
        "atomic_numbers": atoms.get_atomic_numbers().astype(int).tolist(),
        "positions_A": np.round(atoms.positions, 8).tolist(),
        "cell_vectors_A": np.round(atoms.cell.array, 8).tolist(),
        "layer_tags": atoms.get_tags().astype(int).tolist(),
        "periodic_xyz": [bool(value) for value in atoms.pbc],
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def _registry_integer(row: dict, field: str) -> int:
    try:
        return int(row[field])
    except (KeyError, ValueError, TypeError) as exc:
        raise GeometryIntegrityError(
            f"Invalid registry field {field}: "
            f"{row.get('candidate_id', 'unknown')}"
        ) from exc


def load_geometry_registry(
    project_root: str | Path = ".",
) -> list[dict]:
    """Load and validate the eight registered CuSelect-AI geometries."""

    folder = (
        Path(project_root)
        / "data/processed/04_structures"
    )

    registry_path = folder / "04_structure_registry.csv"
    manifest_path = folder / "04_structure_manifest.json"

    with registry_path.open(
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)
        required = {
            "candidate_id",
            "facet",
            "chemical_formula",
            "atom_count",
            "ag_count",
            "ag_top_layer_count",
            "ag_subsurface_count",
            "top_layer_site_count",
            "pbc_xyz",
            "geometry_status",
            "energy_status",
            "selectivity_status",
            "structure_review_status",
            "approved_for_modeling",
            "geometry_sha256",
        }

        if not required.issubset(reader.fieldnames or []):
            raise GeometryIntegrityError(
                "Required geometry registry columns are missing"
            )

        registry = list(reader)

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    if (
        manifest.get("campaign_id") != "CU-001"
        or manifest.get("candidate_count") != 8
        or len(registry) != 8
        or manifest.get("ml_approved") is not False
        or manifest.get("geometry_status") != "unrelaxed"
        or manifest.get("human_review_status")
        != "pending_visual_review"
    ):
        raise GeometryIntegrityError(
            "Geometry manifest or registry violates expected scope"
        )

    ids = [row["candidate_id"] for row in registry]

    if len(set(ids)) != len(ids):
        raise GeometryIntegrityError(
            "Duplicate geometry candidate IDs"
        )

    for candidate_id in ids:
        if not re.fullmatch(
            r"CU-001-[A-Z0-9-]+",
            candidate_id,
        ):
            raise GeometryIntegrityError(
                "Invalid geometry candidate identifier"
            )

    expected_files = {
        f"{candidate_id}.extxyz"
        for candidate_id in ids
    }

    if (
        not isinstance(manifest.get("files"), list)
        or len(manifest["files"]) != len(expected_files)
        or set(manifest["files"]) != expected_files
    ):
        raise GeometryIntegrityError(
            "Manifest file list does not match registry"
        )

    actual_files = {
        path.name
        for path in folder.glob("*.extxyz")
    }

    if actual_files != expected_files:
        raise GeometryIntegrityError(
            "Exported structure files do not match registry"
        )

    fingerprints = set()

    for row in registry:
        candidate_id = row["candidate_id"]

        structure_path = folder / f"{candidate_id}.extxyz"

        try:
            atoms = read(
                structure_path,
                format="extxyz",
            )
        except Exception as exc:
            raise GeometryIntegrityError(
                f"Cannot read geometry: {candidate_id}"
            ) from exc

        if (
            not np.isfinite(atoms.positions).all()
            or not np.isfinite(atoms.cell.array).all()
        ):
            raise GeometryIntegrityError(
                f"Non-finite atomic geometry: {candidate_id}"
            )

        actual_hash = geometry_fingerprint(atoms)

        if actual_hash != row["geometry_sha256"]:
            raise GeometryIntegrityError(
                f"Geometry fingerprint mismatch: {candidate_id}"
            )

        if actual_hash in fingerprints:
            raise GeometryIntegrityError(
                "Duplicate atomic geometry fingerprint"
            )

        fingerprints.add(actual_hash)

        if (
            atoms.info.get("candidate_id") != candidate_id
            or str(atoms.info.get("facet")) != row["facet"]
            or atoms.get_chemical_formula()
            != row["chemical_formula"]
        ):
            raise GeometryIntegrityError(
                f"Geometry identity mismatch: {candidate_id}"
            )

        atomic_numbers = atoms.get_atomic_numbers()
        tags = atoms.get_tags()

        ag_count = int(np.count_nonzero(atomic_numbers == 47))
        top_layer_tag = int(np.min(tags))
        top_layer_mask = tags == top_layer_tag

        ag_top_count = int(np.count_nonzero(
            (atomic_numbers == 47) & top_layer_mask
        ))

        counts_match = (
            len(atoms) == _registry_integer(row, "atom_count")
            and ag_count == _registry_integer(row, "ag_count")
            and ag_top_count
            == _registry_integer(row, "ag_top_layer_count")
            and ag_count - ag_top_count
            == _registry_integer(row, "ag_subsurface_count")
            and int(np.count_nonzero(top_layer_mask))
            == _registry_integer(row, "top_layer_site_count")
        )

        if not counts_match:
            raise GeometryIntegrityError(
                f"Atomic composition or layer mismatch: {candidate_id}"
            )

        pbc_from_registry = [
            value.strip().lower() == "true"
            for value in row["pbc_xyz"].split(",")
        ]

        if (
            len(pbc_from_registry) != 3
            or pbc_from_registry
            != [bool(value) for value in atoms.pbc]
        ):
            raise GeometryIntegrityError(
                f"Periodic boundary mismatch: {candidate_id}"
            )

        required_states = {
            "geometry_status": "unrelaxed",
            "energy_status": "not_computed",
            "selectivity_status": "not_predicted",
        }

        for field, expected in required_states.items():
            if (
                row[field] != expected
                or atoms.info.get(field) != expected
            ):
                raise GeometryIntegrityError(
                    f"Invalid {field}: {candidate_id}"
                )

        if (
            row["structure_review_status"]
            != "pending_visual_review"
            or row["approved_for_modeling"].strip().lower()
            != "false"
        ):
            raise GeometryIntegrityError(
                f"Unapproved geometry state changed: {candidate_id}"
            )

    return registry
