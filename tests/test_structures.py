"""Scientific/structural regression tests, runnable with pytest."""
import numpy as np
from ase.io import read
from cuselect.structures import (
    make_cu100,
    make_substitutional_cuag,
    central_surface_atom_index,
    geometry_summary,
    export_geometries,
)


def test_reference_formula_and_periodicity():
    slab = make_cu100()
    assert len(slab) == 36
    assert slab.get_chemical_formula() == "Cu36"
    assert np.array_equal(slab.pbc, [True, True, False])
    assert np.count_nonzero(slab.get_tags() == 1) == 9
    assert slab.info["energy_status"] == "not_computed"


def test_ag_substitutes_one_top_layer_atom():
    slab = make_substitutional_cuag()
    ag = [atom for atom in slab if atom.symbol == "Ag"]
    assert len(ag) == 1
    assert len(slab) == 36
    assert slab.get_chemical_formula() == "AgCu35"
    assert ag[0].tag == 1
    assert slab.info["dopant_atom_index"] == central_surface_atom_index(slab)


def test_summary_does_not_invent_scientific_predictions():
    summary = geometry_summary(make_substitutional_cuag())
    assert summary["ag_fraction_top_layer"] == 0.1111
    assert summary["energy_status"] == "not_computed"
    assert summary["selectivity_status"] == "not_predicted"


def test_export_round_trip(tmp_path):
    results = export_geometries(tmp_path)
    assert len(results) == 2
    ag = read(tmp_path / "CU-001-AG1.extxyz")
    assert ag.get_chemical_symbols().count("Ag") == 1
    assert (tmp_path / "geometry_registry.json").exists()
