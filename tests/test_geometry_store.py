
# CuSelect-AI — Phase II
# File: tests/test_geometry_store.py
#
# PSEUDOCODE
# 1. Copy all eight structures, registry, and manifest to a
#    temporary project directory.
# 2. Confirm valid geometry exports are accepted.
# 3. Test modified atomic coordinates and fingerprints.
# 4. Test unauthorized scientific approval changes.
# 5. Test altered identities, counts, and missing structures.
# 6. Require every manipulated case to fail safely.
# 7. Never modify the original scientific structures.

import csv
import json
import shutil
import sys
from pathlib import Path

import pytest
from ase.io import read, write

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cuselect.geometry_store import (
    GeometryIntegrityError,
    load_geometry_registry,
)


FOLDER = Path("data/processed/04_structures")
REGISTRY = FOLDER / "04_structure_registry.csv"
MANIFEST = FOLDER / "04_structure_manifest.json"

CANDIDATE = "CU-001-100-AG2-NN"


@pytest.fixture
def geometry_copy(tmp_path):
    """Copy research exports into a disposable test directory."""

    destination = tmp_path / FOLDER
    destination.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        ROOT / FOLDER,
        destination,
    )

    return tmp_path


def change_registry_field(project, candidate_id, field, value):
    """Modify only the temporary registry."""

    path = project / REGISTRY

    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fields = reader.fieldnames
        rows = list(reader)

    matched = False

    for row in rows:
        if row["candidate_id"] == candidate_id:
            row[field] = value
            matched = True

    assert matched

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_valid_geometry_exports_are_accepted(geometry_copy):
    registry = load_geometry_registry(geometry_copy)

    assert len(registry) == 8
    assert len({
        row["geometry_sha256"]
        for row in registry
    }) == 8


def test_modified_atomic_position_is_rejected(geometry_copy):
    path = geometry_copy / FOLDER / f"{CANDIDATE}.extxyz"

    atoms = read(path, format="extxyz")
    atoms.positions[0, 0] += 0.05

    write(path, atoms, format="extxyz")

    with pytest.raises(GeometryIntegrityError):
        load_geometry_registry(geometry_copy)


def test_modified_registry_fingerprint_is_rejected(geometry_copy):
    change_registry_field(
        geometry_copy,
        CANDIDATE,
        "geometry_sha256",
        "0" * 64,
    )

    with pytest.raises(GeometryIntegrityError):
        load_geometry_registry(geometry_copy)


def test_unauthorized_modeling_approval_is_rejected(geometry_copy):
    change_registry_field(
        geometry_copy,
        CANDIDATE,
        "approved_for_modeling",
        "True",
    )

    with pytest.raises(GeometryIntegrityError):
        load_geometry_registry(geometry_copy)


def test_changed_visual_review_status_is_rejected(geometry_copy):
    change_registry_field(
        geometry_copy,
        CANDIDATE,
        "structure_review_status",
        "approved",
    )

    with pytest.raises(GeometryIntegrityError):
        load_geometry_registry(geometry_copy)


def test_missing_structure_file_is_rejected(geometry_copy):
    path = geometry_copy / FOLDER / f"{CANDIDATE}.extxyz"

    path.unlink()

    with pytest.raises(GeometryIntegrityError):
        load_geometry_registry(geometry_copy)


def test_duplicate_candidate_id_is_rejected(geometry_copy):
    path = geometry_copy / REGISTRY

    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fields = reader.fieldnames
        rows = list(reader)

    rows[1]["candidate_id"] = rows[0]["candidate_id"]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(GeometryIntegrityError):
        load_geometry_registry(geometry_copy)


def test_modified_structure_identity_is_rejected(geometry_copy):
    path = geometry_copy / FOLDER / f"{CANDIDATE}.extxyz"

    atoms = read(path, format="extxyz")
    atoms.info["candidate_id"] = "CU-FAKE-ID"

    write(path, atoms, format="extxyz")

    with pytest.raises(GeometryIntegrityError):
        load_geometry_registry(geometry_copy)


def test_manifest_modeling_approval_is_rejected(geometry_copy):
    path = geometry_copy / MANIFEST

    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["ml_approved"] = True

    path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(GeometryIntegrityError):
        load_geometry_registry(geometry_copy)


def test_incorrect_atom_count_is_rejected(geometry_copy):
    change_registry_field(
        geometry_copy,
        CANDIDATE,
        "atom_count",
        "35",
    )

    with pytest.raises(GeometryIntegrityError):
        load_geometry_registry(geometry_copy)


def test_unapproved_energy_status_change_is_rejected(geometry_copy):
    change_registry_field(
        geometry_copy,
        CANDIDATE,
        "energy_status",
        "computed",
    )

    with pytest.raises(GeometryIntegrityError):
        load_geometry_registry(geometry_copy)
