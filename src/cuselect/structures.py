"""Reproducible, *unrelaxed* Cu(100) slab and substitutional Cu-Ag geometry.

Scientific scope:
- These are initial geometries, NOT energy-minimized structures.
- A single substitutional Ag on a periodically repeated 3x3 Cu(100) slab is
  not a prediction of a stable or experimentally accessible single-atom alloy.
- No calculated activity, selectivity, adsorption energy or Faradaic efficiency.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from ase import Atoms
from ase.build import fcc100
from ase.io import write


@dataclass(frozen=True)
class GeometrySpec:
    element: str = "Cu"
    lattice_constant_angstrom: float = 3.615
    size: tuple[int, int, int] = (3, 3, 4)
    vacuum_angstrom: float = 12.0


def make_cu100(spec: GeometrySpec = GeometrySpec()) -> Atoms:
    """Construct an FCC(100) copper slab; periodic in x and y only."""
    if spec.element != "Cu":
        raise ValueError("The CU-001 protocol is intentionally Cu-only.")
    if any(n < 2 for n in spec.size):
        raise ValueError("Every supercell dimension must be >= 2.")
    if spec.vacuum_angstrom < 8:
        raise ValueError("Use at least 8 Å vacuum in this geometry-only prototype.")
    slab = fcc100(
        spec.element,
        size=spec.size,
        a=spec.lattice_constant_angstrom,
        vacuum=spec.vacuum_angstrom,
    )
    slab.info.update({
        "candidate_id": "CU-001-REF",
        "facet": "100",
        "geometry_status": "unrelaxed",
        "energy_status": "not_computed",
        "selectivity_status": "not_predicted",
    })
    return slab


def central_surface_atom_index(slab: Atoms) -> int:
    """Choose an atom from the topmost layer, nearest the XY cell center.

    ASE slab builder tags top layer as 1; this selection avoids relying on
    atom order, making the construction reproducible.
    """
    tags = np.asarray(slab.get_tags())
    top = np.flatnonzero(tags == 1)
    if len(top) == 0:
        raise ValueError("ASE slab tags do not identify a top layer.")
    center_xy = 0.5 * (np.asarray(slab.cell[0, :2]) + np.asarray(slab.cell[1, :2]))
    d2 = ((slab.positions[top, :2] - center_xy) ** 2).sum(axis=1)
    return int(top[int(np.argmin(d2))])


def make_substitutional_cuag(spec: GeometrySpec = GeometrySpec()) -> Atoms:
    """Replace one top-layer Cu atom by Ag in a periodic Cu(100) model."""
    slab = make_cu100(spec)
    index = central_surface_atom_index(slab)
    slab[index].symbol = "Ag"
    slab.info.update({
        "candidate_id": "CU-001-AG1",
        "dopant": "Ag",
        "dopant_atom_index": index,
        "dopant_site": "substitutional_top_layer",
        "geometry_status": "unrelaxed",
        "energy_status": "not_computed",
        "selectivity_status": "not_predicted",
    })
    return slab


def geometry_summary(atoms: Atoms) -> dict:
    """Report only values that follow directly from the input geometry."""
    symbols = atoms.get_chemical_symbols()
    top_indices = np.flatnonzero(np.asarray(atoms.get_tags()) == 1)
    dopant_count = symbols.count("Ag")
    return {
        "candidate_id": atoms.info["candidate_id"],
        "chemical_formula": atoms.get_chemical_formula(),
        "total_atoms": len(atoms),
        "top_layer_atoms": len(top_indices),
        "ag_atoms": dopant_count,
        "ag_fraction_top_layer": round(dopant_count / len(top_indices), 4),
        "periodic_xyz": [bool(x) for x in atoms.pbc],
        "geometry_status": atoms.info["geometry_status"],
        "energy_status": "not_computed",
        "selectivity_status": "not_predicted",
    }


def export_geometries(output_dir: str | Path) -> list[dict]:
    """Save two ASE Extended XYZ files plus provenance-friendly summaries."""
    import json
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for atoms in (make_cu100(), make_substitutional_cuag()):
        candidate_id = atoms.info["candidate_id"]
        write(folder / f"{candidate_id}.extxyz", atoms, format="extxyz")
        records.append(geometry_summary(atoms))
    (folder / "geometry_registry.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )
    return records
