"""Test optimizer checkpoint recovery without running GPAW."""

import numpy as np

from ase.build import bulk
from ase.calculators.emt import EMT
from ase.constraints import FixAtoms
from ase.io.trajectory import Trajectory
from ase.optimize import BFGS


def test_bfgs_restart_preserves_constraints(tmp_path):
    trajectory = tmp_path / "relaxation.traj"
    checkpoint = tmp_path / "bfgs_restart.json"

    atoms = bulk("Cu", "fcc", a=3.6, cubic=True)
    atoms.positions[1, 2] += 0.4

    fixed_position = atoms.positions[0].copy()
    atoms.set_constraint(FixAtoms(indices=[0]))
    atoms.calc = EMT()

    # First optimization segment.
    optimizer = BFGS(
        atoms,
        trajectory=str(trajectory),
        restart=str(checkpoint),
        logfile=None,
    )
    optimizer.run(fmax=1e-8, steps=2)

    assert trajectory.is_file()
    assert checkpoint.is_file()

    with Trajectory(str(trajectory)) as frames:
        before = len(frames)
        recovered = frames[-1].copy()

    assert recovered.constraints
    assert np.allclose(recovered.positions[0], fixed_position)

    # Simulate restarting the program.
    recovered.calc = EMT()

    resumed = BFGS(
        recovered,
        trajectory=str(trajectory),
        restart=str(checkpoint),
        append_trajectory=True,
        logfile=None,
    )
    resumed.run(fmax=1e-8, steps=2)

    with Trajectory(str(trajectory)) as frames:
        after = len(frames)

    assert after > before
    assert np.allclose(recovered.positions[0], fixed_position)
