# CuSelect-AI — Interactive catalyst visualization
#
# PSEUDOCODE
# 1. Validate the registered atomic structures.
# 2. Find the requested catalyst candidate.
# 3. Read its actual atomic coordinates from EXTXYZ.
# 4. Verify that its geometry fingerprint matches.
# 5. Represent copper and silver atoms separately.
# 6. Create a rotatable 3D Plotly figure.
# 7. Return the figure without modifying atomic structures.

from pathlib import Path

import plotly.graph_objects as go
from ase.io import read

from .geometry_store import (
    GeometryIntegrityError,
    geometry_fingerprint,
    load_geometry_registry,
)


def build_structure_figure(project_root, candidate_id):
    root = Path(project_root)

    # Validate all eight registered structures first.
    registry = load_geometry_registry(root)

    record = next(
        (
            row for row in registry
            if row["candidate_id"] == candidate_id
        ),
        None,
    )

    if record is None:
        raise ValueError("Unknown registered catalyst candidate")

    path = (
        root
        / "data"
        / "processed"
        / "04_structures"
        / f"{candidate_id}.extxyz"
    )

    atoms = read(path, format="extxyz")

    if geometry_fingerprint(atoms) != record["geometry_sha256"]:
        raise GeometryIntegrityError(
            "Geometry fingerprint mismatch"
        )

    symbols = atoms.get_chemical_symbols()
    positions = atoms.get_positions()
    tags = atoms.get_tags()

    figure = go.Figure()

    # Colors distinguish chemical elements, not performance.
    elements = {
        "Cu": ("Copper", "#B87333", 10),
        "Ag": ("Silver", "#C0C0C0", 13),
    }

    for symbol, (name, color, size) in elements.items():
        indices = [
            i for i, element in enumerate(symbols)
            if element == symbol
        ]

        if not indices:
            continue

        figure.add_trace(
            go.Scatter3d(
                x=[float(positions[i, 0]) for i in indices],
                y=[float(positions[i, 1]) for i in indices],
                z=[float(positions[i, 2]) for i in indices],
                mode="markers",
                name=name,
                text=[
                    f"Atom {i + 1}; layer tag {int(tags[i])}"
                    for i in indices
                ],
                hovertemplate=(
                    "%{text}"
                    "<br>x: %{x:.2f} Å"
                    "<br>y: %{y:.2f} Å"
                    "<br>z: %{z:.2f} Å"
                    "<extra></extra>"
                ),
                marker=dict(
                    size=size,
                    color=color,
                    opacity=1.0,
                    line=dict(color="#444444", width=0.5),
                ),
            )
        )

    figure.update_layout(
        height=450,
        margin=dict(l=0, r=0, t=20, b=0),
        scene=dict(
            xaxis_title="x (Å)",
            yaxis_title="y (Å)",
            zaxis_title="z (Å)",
            aspectmode="data",
        ),
        legend=dict(orientation="h"),
    )

    return figure, record
