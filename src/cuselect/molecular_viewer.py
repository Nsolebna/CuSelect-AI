# CuSelect-AI — Publication-inspired molecular viewer
#
# PSEUDOCODE
# 1. Validate the original atomic geometry registry.
# 2. Read the actual Cu and Ag atomic coordinates.
# 3. Identify nearby atom pairs for visual connectors.
# 4. Create a 3Dmol.js viewer using native shaded spheres.
# 5. Provide perspective, top and side orientations.
# 6. Preserve every scientific coordinate and metadata record.

import json
from pathlib import Path

import numpy as np
from ase.io import read

from .geometry_store import (
    GeometryIntegrityError,
    geometry_fingerprint,
    load_geometry_registry,
)


HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://3Dmol.org/build/3Dmol-min.js"></script>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont,
                 "Segoe UI", sans-serif;
    background: #f8fafc;
}

.panel {
    position: relative;
    width: 100%;
    height: 475px;
    overflow: hidden;
    border: 1px solid #e3e8ef;
    border-radius: 16px;
    background: #f8fafc;
}

#viewer {
    position: absolute;
    inset: 0;
}

.toolbar {
    position: absolute;
    z-index: 10;
    top: 12px;
    left: 12px;
    display: flex;
    gap: 6px;
}

button {
    border: 1px solid #d8e0e9;
    border-radius: 7px;
    padding: 7px 11px;
    background: rgba(255,255,255,0.96);
    color: #263445;
    cursor: pointer;
    font-size: 12px;
}

button:hover {
    background: #eaf0f7;
}

.legend {
    position: absolute;
    z-index: 10;
    left: 14px;
    bottom: 12px;
    display: flex;
    gap: 18px;
    padding: 8px 12px;
    border-radius: 8px;
    background: rgba(255,255,255,0.92);
    font-size: 12px;
    color: #334155;
}

.dot {
    display: inline-block;
    width: 11px;
    height: 11px;
    border-radius: 50%;
    margin-right: 5px;
    vertical-align: middle;
}

#error {
    display: none;
    position: absolute;
    top: 60px;
    left: 12px;
    color: #b91c1c;
    font-size: 13px;
}
</style>
</head>

<body>
<div class="panel">
    <div id="viewer"></div>

    <div class="toolbar">
        <button data-view="perspective">Perspective</button>
        <button data-view="top">Top</button>
        <button data-view="side">Side</button>
    </div>

    <div class="legend">
        <span>
            <i class="dot" style="background:#c78049"></i>Cu
        </span>
        <span>
            <i class="dot" style="background:#cbd5e1"></i>Ag
        </span>
    </div>

    <div id="error">
        Molecular renderer unavailable. Check network access
        to 3Dmol.org.
    </div>
</div>

<script>
(function () {
    // PSEUDOCODE
    // 1. Read only numeric validated atomic coordinates.
    // 2. Render Cu and Ag as real shaded WebGL spheres.
    // 3. Add narrow geometric nearest-neighbour guides.
    // 4. Allow rotation and fixed camera presets.

    if (!window.$3Dmol) {
        document.getElementById("error").style.display = "block";
        return;
    }

    const scene = __PAYLOAD__;

    const viewer = $3Dmol.createViewer(
        document.getElementById("viewer"),
        {
            backgroundColor: "#f8fafc",
            antialias: true,
            orthographic: true
        }
    );

    const model = viewer.addModel();
    model.addAtoms(scene.atoms);

    // Small spheres keep individual lattice sites visible.
    viewer.setStyle(
        {elem: "Cu"},
        {sphere: {radius: 0.67, color: "#c78049"}}
    );

    viewer.setStyle(
        {elem: "Ag"},
        {sphere: {radius: 0.75, color: "#cbd5e1"}}
    );

    // Rods are geometric guides, not formal chemical bonds.
    scene.guides.forEach(function (pair) {
        const a = scene.atoms[pair[0]];
        const b = scene.atoms[pair[1]];

        viewer.addCylinder({
            start: {x: a.x, y: a.y, z: a.z},
            end: {x: b.x, y: b.y, z: b.z},
            radius: 0.10,
            color: "#9ca9b7",
            opacity: 0.58,
            fromCap: 1,
            toCap: 1
        });
    });

    // Click an atom to inspect its source coordinates.
    let activeLabel = null;

    viewer.setClickable({}, true, function(atom) {
        if (activeLabel) {
            viewer.removeLabel(activeLabel);
        }

        const label = atom.elem + " #" + atom.serial +
            "  (" + atom.x.toFixed(2) + ", " +
            atom.y.toFixed(2) + ", " +
            atom.z.toFixed(2) + ") Å";

        activeLabel = viewer.addLabel(label, {
            position: {x: atom.x, y: atom.y, z: atom.z},
            fontSize: 11,
            fontColor: "#ffffff",
            backgroundColor: "#263445",
            backgroundOpacity: 0.9,
            inFront: true
        });

        viewer.render();
    });

    viewer.setProjection("orthographic");
    viewer.zoomTo();
    viewer.zoom(1.08);

    const originalView = viewer.getView();

    function showView(name) {
        viewer.setView(originalView);

        if (name === "perspective") {
            viewer.rotate(52, "x");
            viewer.rotate(-32, "z");
        } else if (name === "side") {
            viewer.rotate(85, "x");
        }

        viewer.render();
    }

    document.querySelectorAll("[data-view]").forEach(
        function(button) {
            button.addEventListener("click", function() {
                showView(button.dataset.view);
            });
        }
    );

    showView("perspective");
    window.addEventListener("resize", function() {
        viewer.resize();
        viewer.render();
    });
})();
</script>
</body>
</html>
"""


def build_structure_html(project_root, candidate_id):
    """Build a molecular viewer from an integrity-checked structure."""

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

    structure = read(path, format="extxyz")

    if geometry_fingerprint(structure) != record["geometry_sha256"]:
        raise GeometryIntegrityError("Geometry fingerprint mismatch")

    positions = structure.get_positions()
    symbols = structure.get_chemical_symbols()

    if any(symbol not in ("Cu", "Ag") for symbol in symbols):
        raise GeometryIntegrityError("Unexpected chemical element")

    atom_data = []

    for index, (symbol, position) in enumerate(
        zip(symbols, positions)
    ):
        atom_data.append({
            "elem": symbol,
            "x": float(position[0]),
            "y": float(position[1]),
            "z": float(position[2]),
            "serial": index + 1,
        })

    # Visual nearest-neighbour guides within the exported cell.
    # Do not infer bond order or draw unverified periodic bonds.
    guides = []

    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            distance = float(
                np.linalg.norm(positions[i] - positions[j])
            )

            if 2.30 <= distance <= 2.75:
                guides.append([i, j])

    payload = {
        "atoms": atom_data,
        "guides": guides,
    }

    html = HTML_TEMPLATE.replace(
        "__PAYLOAD__",
        json.dumps(payload, ensure_ascii=True),
    )

    return html, record
