# CuSelect-AI — Evidence-First Scientific Research Workbench

**Current release:** v0.2 — research workspace, notebooks 00–01 and retained Stage-1 Cu(100)/Cu–Ag geometry prototype.

This is a structured scientific software project. It is **not yet** a functioning catalyst discovery agent, a verified DFT/MLIP model, or a predictor of ethylene Faradaic efficiency.

## Project question

Can a mechanism-aware verification agent reduce unsupported advancement of Cu–Ag CO2RR catalyst proposals while controlling false rejections, abstentions and computational cost compared with simpler approaches?

## Begin here — macOS M4

1. Read [`docs/ENVIRONMENT_SETUP_MAC.md`](docs/ENVIRONMENT_SETUP_MAC.md) and unzip into `~/Projects/CuSelect-AI` (or a location of your choice).
2. From the project root, create a Conda environment and install the project:

   ```bash
   conda create -n cuselect python=3.11 pip -y
   conda activate cuselect
   python -m pip install -e ".[notebook,app,dev]"
   python -m ipykernel install --user --name cuselect --display-name "Python (CuSelect-AI)"
   python -m pytest -q
   python -m jupyter lab
   ```

3. Open `notebooks/00_Environment_and_Reproducibility.ipynb` first. **Run all**; ensure no errors and inspect `outputs/reports/00_environment_snapshot.json`.
4. Then open `notebooks/01_Research_Question_and_Protocol.ipynb`. **Run all**, check the scientific protocol and handoff report.

## Notebook story

We will use **10 numbered notebooks** (00–09) as described in [`docs/NOTEBOOK_ROADMAP.md`](docs/NOTEBOOK_ROADMAP.md). Only 00 and 01 are created now. We add later notebooks when the preceding scientific gate passes. Reusable functions live in `src/cuselect/`; tested behaviors in `tests/`.

## Research workspace

```bash
python -m streamlit run streamlit_app.py
```

The workspace opens four sections for the historical research case, local workflow,
scientific evidence and catalyst models. Literature discovery uses Crossref when requested.
The 3D viewer loads 3Dmol.js in the browser.

## Existing Stage-1 geometry application

```bash
python run_step1.py
python -m streamlit run app.py
```

This builds and displays an unrelaxed 3x3x4 Cu(100) slab and a periodic top-layer Ag substitution, with 36 atoms each. No energies, barriers, stability or CO2RR activity have been predicted.

## Files and conventions

- `configs/CU-001_protocol.json`: versioned study objective and evaluation protocol.
- `data/papers.csv`: seed bibliographic register; verify entries against sources before extraction.
- `data/evidence_template.csv`: empty scientific evidence schema.
- `src/cuselect/structures.py`: deterministic structural model functions from Stage 1.
- `src/cuselect/protocol.py`: typed protocol validation.
- `src/cuselect/project_checks.py`: minimal environment checks, without personal secrets.
- `outputs/`: reproducible, Git-ignored notebook/calculation results.
- `docs/RESEARCH_AUDIT.md` and `docs/SCIENTIFIC_SCOPE.md`: existing early research audit and scientific boundaries.
- `.github/workflows/tests.yml`: basic continuous-integration unit tests.

## Scientific safeguards

Unrelaxed structures are not stable structures. Adsorption descriptors are not ethylene FE. Different electrolytes, reactors and potentials are not directly comparable without conditions. Withheld evaluation DOI content must not enter RAG. Agent claims and numerical predictions require verification and provenance.

## Verification status

Notebook structure and Python source have been programmatically generated and statically checked in the authoring environment. End-to-end ASE/Jupyter execution requires dependencies in your local `cuselect` environment; the provided Mac instructions and pytest command are the acceptance check.
