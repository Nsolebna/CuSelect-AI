"""Run Stage 1: generate reference Cu and Cu–Ag surface geometries."""
from pathlib import Path
from cuselect.structures import export_geometries


def main() -> None:
    records = export_geometries(Path(__file__).resolve().parent / "outputs" / "structures")
    for item in records:
        print(f"{item['candidate_id']}: {item['chemical_formula']}, "
              f"{item['total_atoms']} atoms, state={item['geometry_status']}")
    print("Saved: outputs/structures/ (.extxyz and geometry_registry.json)")
    print("No energies or CO2RR selectivities have been predicted.")


if __name__ == "__main__":
    main()
