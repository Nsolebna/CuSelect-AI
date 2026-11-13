# CuSelect-AI — Metallic 3D atomic sphere renderer
#
# PSEUDOCODE
# 1. Validate the registered atomic geometry.
# 2. Read the original Cu and Ag atom coordinates.
# 3. Build a smooth triangulated sphere for every atom.
# 4. Apply metallic-looking lighting and material colors.
# 5. Hide scientific plotting grids and axes.
# 6. Provide perspective, top and side camera views.
# 7. Never change atomic coordinates or scientific status.

from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from ase.io import read

from .geometry_store import (
    GeometryIntegrityError,
    geometry_fingerprint,
    load_geometry_registry,
)


def sphere_mesh(center, radius, rings=15, segments=28):
    """Create a triangulated 3D sphere at an atomic position."""

    theta = np.linspace(0, np.pi, rings)
    phi = np.linspace(
        0, 2 * np.pi, segments, endpoint=False
    )

    t, p = np.meshgrid(theta, phi, indexing="ij")

    x = center[0] + radius * np.sin(t) * np.cos(p)
    y = center[1] + radius * np.sin(t) * np.sin(p)
    z = center[2] + radius * np.cos(t)

    triangles_i = []
    triangles_j = []
    triangles_k = []

    for row in range(rings - 1):
        for col in range(segments):
            next_col = (col + 1) % segments

            a = row * segments + col
            b = row * segments + next_col
            c = (row + 1) * segments + col
            d = (row + 1) * segments + next_col

            triangles_i.extend([a, b])
            triangles_j.extend([c, c])
            triangles_k.extend([b, d])

    return (
        x.ravel(),
        y.ravel(),
        z.ravel(),
        triangles_i,
        triangles_j,
        triangles_k,
    )


def camera_views():
    return {
        "Perspective": dict(
            eye=dict(x=1.5, y=-1.7, z=1.1),
            up=dict(x=0, y=0, z=1),
            projection=dict(type="orthographic"),
        ),
        "Top": dict(
            eye=dict(x=0, y=0, z=2.5),
            up=dict(x=0, y=1, z=0),
            projection=dict(type="orthographic"),
        ),
        "Side": dict(
            eye=dict(x=0, y=-2.5, z=0.2),
            up=dict(x=0, y=0, z=1),
            projection=dict(type="orthographic"),
        ),
    }


def build_structure_figure(project_root, candidate_id):
    """Create a shaded sphere model from verified EXTXYZ data."""

    root = Path(project_root)
    registry = load_geometry_registry(root)

    record = next(
        (
            row for row in registry
            if row["candidate_id"] == candidate_id
        ),
        None,
    )

    if record is None:
        raise ValueError("Unknown registered candidate")

    path = (
        root
        / "data/processed/04_structures"
        / f"{candidate_id}.extxyz"
    )

    atoms = read(path, format="extxyz")

    if geometry_fingerprint(atoms) != record["geometry_sha256"]:
        raise GeometryIntegrityError("Geometry mismatch")

    positions = atoms.get_positions()
    symbols = atoms.get_chemical_symbols()

    figure = go.Figure()

    # Visual radii are illustrative, not physical ionic radii.
    materials = {
        "Cu": {
            "color": "#CC8149",
            "radius": 1.10,
        },
        "Ag": {
            "color": "#D9E2ED",
            "radius": 1.20,
        },
    }

    for index, (symbol, position) in enumerate(
        zip(symbols, positions)
    ):
        if symbol not in materials:
            raise GeometryIntegrityError(
                "Unexpected element in Cu–Ag structure"
            )

        material = materials[symbol]

        x, y, z, i, j, k = sphere_mesh(
            position,
            material["radius"],
        )

        figure.add_trace(
            go.Mesh3d(
                x=x,
                y=y,
                z=z,
                i=i,
                j=j,
                k=k,
                color=material["color"],
                opacity=1,
                flatshading=False,
                lighting=dict(
                    ambient=0.55,
                    diffuse=0.85,
                    specular=0.9,
                    roughness=0.16,
                    fresnel=0.18,
                ),
                lightposition=dict(
                    x=-80,
                    y=-120,
                    z=200,
                ),
                hovertext=(
                    f"{symbol} atom {index + 1}"
                    f"<br>Position: "
                    f"({position[0]:.2f}, "
                    f"{position[1]:.2f}, "
                    f"{position[2]:.2f}) Å"
                ),
                hoverinfo="text",
                showlegend=False,
                name=symbol,
            )
        )

    views = camera_views()

    figure.update_layout(
        height=580,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=0, r=0, t=65, b=0),
        scene=dict(
            bgcolor="#FFFFFF",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            aspectmode="data",
            camera=views["Perspective"],
        ),
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                buttons=[
                    dict(
                        label=label,
                        method="relayout",
                        args=[{"scene.camera": camera}],
                    )
                    for label, camera in views.items()
                ],
                showactive=True,
                x=0.02,
                y=1.09,
                xanchor="left",
                yanchor="top",
                bgcolor="#F1F3F7",
            )
        ],
        showlegend=False,
        uirevision=candidate_id,
    )

    return figure, record
