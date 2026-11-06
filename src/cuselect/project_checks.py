"""Reproducible, privacy-preserving environment metadata and project checks."""
from __future__ import annotations
from importlib import metadata
from pathlib import Path
import platform
import sys

def require_project_root(root: str | Path) -> Path:
    root = Path(root).resolve()
    expected = ["pyproject.toml", "configs/CU-001_protocol.json", "notebooks"]
    missing = [name for name in expected if not (root / name).exists()]
    if missing:
        raise RuntimeError(
            "Launch Jupyter from the CuSelect-AI project root. Missing: " + ", ".join(missing)
        )
    return root

def environment_snapshot() -> dict:
    """Do not collect username, hostname, serial number, environment variables or API keys."""
    packages = ["ase", "numpy", "pandas", "pydantic", "jupyterlab", "ipykernel", "streamlit", "pytest"]
    versions = {}
    for p in packages:
        try:
            versions[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            versions[p] = "not_installed"
    return {
        "python": platform.python_version(),
        "platform_system": platform.system(),
        "machine_architecture": platform.machine(),
        "python_executable_within_conda": bool(sys.prefix != sys.base_prefix or "conda" in sys.prefix.lower()),
        "packages": versions,
    }
