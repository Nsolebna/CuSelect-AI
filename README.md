# CuSelect-AI
### Evidence-First Scientific AI for CO₂ Electroreduction Research

**CuSelect-AI** is a Python-based scientific research workbench for investigating Cu-based catalysts for electrochemical CO₂ reduction, particularly the production of ethylene (C₂H₄).

It integrates scientific literature retrieval, retrieval-augmented generation (RAG), AI-assisted scientific interpretation, experimental evidence assessment, exploratory computational results, and research decision support.

> **Project status:** Research prototype. CuSelect-AI does not yet provide autonomous, experimentally validated catalyst discovery or reliable predictions of ethylene Faradaic efficiency.

## The Problem

Experimental studies of CO₂ electroreduction use different catalysts, electrolytes, reactors, potentials, and current densities. These differences make scientific comparison challenging.

General-purpose AI tools may also produce unsupported mechanistic claims or overlook contradictory research.

CuSelect-AI investigates how evidence-grounded AI can support scientific reasoning while preserving provenance, uncertainty, and human scientific review.

### Research question

Can a mechanism-aware verification agent reduce unsupported advancement of Cu–Ag CO₂RR catalyst proposals while controlling false rejections, abstentions, and computational cost compared with simpler approaches?

This remains a research question, not a demonstrated outcome.

## Research Workflow

### 1. Discover — Investigate the Literature

- Retrieve scientific publications and local evidence.
- Combine local RAG with external literature search.
- Interpret reported observations and competing mechanisms.
- Identify uncertainties and contradictory findings.
- Register provisional research hypotheses for further assessment.

### 2. Validate — Assess Scientific Evidence

- Review experimental benchmarks and source information.
- Compare reported Faradaic efficiencies with explicit limitations.
- Identify missing experimental conditions.
- Save evidence assessments for supported research cases.
- Explore saved EMT, MACE, and GPAW computational results.

Computational results are exploratory and must not be interpreted as validated predictions of electrocatalytic performance.

### 3. Decide — Identify the Next Research Action

- Select existing benchmark candidates.
- Examine unresolved scientific evidence.
- Generate evidence-aware recommendations for further verification, experimentation, or computation.

Full automatic integration of new discoveries through Discover, Validate, and Decide remains under development.

## Technical Architecture

| Component | Role |
|---|---|
| Python | Research services and application logic |
| Streamlit | Interactive user interface |
| RAG | Local scientific evidence retrieval |
| Sentence Transformers | Semantic retrieval and embeddings |
| OpenAI integration | LLM-assisted scientific interpretation |
| Crossref / OpenAlex | External scientific publication discovery |
| Pandas / NumPy | Scientific data processing |
| ASE | Atomistic structure construction |
| EMT / MACE / GPAW | Exploratory computational workflows |
| JSON registries | Research-case and evidence records |
| Pytest | Automated software testing |

The application combines AI-assisted interpretation, rule-based logic, scientific data processing, and previously saved computational results. These components should not be confused with a trained, validated ethylene-selectivity prediction model.

## Installation

### Requirements

- Python 3.11 or 3.12
- Git
- Internet access for live literature retrieval
- API credentials for features requiring external LLM services

Clone the repository after it is published, enter its root directory, and create a Python environment.

Example using Conda:

```bash
conda create -n cuselect python=3.11 pip -y
conda activate cuselect
python -m pip install -e ".[notebook,app,dev]"
```

Optional local text-generation dependencies:

```bash
python -m pip install -e ".[local_generation]"
```

GPAW and MACE are not included in the standard installation. Reproducing their computational workflows requires separately configured scientific environments.

### Run CuSelect-AI

```bash
python -m streamlit run app/streamlit_app.py --server.port 8501
```

Open `http://localhost:8501`.

Some research features require API configuration. Keep credentials in local environment variables or private Streamlit secrets, never in committed source files.

## Example Research Question

> How does Ag influence CO availability and C–C coupling during CO₂ electroreduction on Cu–Ag catalysts, and what evidence challenges the assumption that more Cu–Ag interface improves ethylene formation?

The Discover workflow can retrieve literature, synthesize provisional interpretations, identify competing mechanistic explanations, and propose further scientific investigation.

Retrieved abstracts and publications are not automatically treated as independently verified experimental results.

## Jupyter Research Notebooks

The repository contains ten notebooks:

| Notebook | Focus |
|---|---|
| 00 | Environment and reproducibility |
| 01 | Research question and protocol |
| 02 | Literature and evidence |
| 03 | Data audit and curation |
| 04 | Catalyst structures |
| 05 | Scientific ML and baselines |
| 06 | RAG and evidence quality |
| 07 | Multi-agent workflow |
| 08 | Scientific critic and active learning |
| 09 | Benchmarking and reporting |

The presence of these notebooks does not guarantee that every notebook has passed an end-to-end execution test.

## Testing

Run the automated test suite:

```bash
python -m pytest -q
```

**Latest development-environment result (13 November 2026):**

- 482 tests passed
- 49 warnings
- No test failures

These tests evaluate implemented software behavior. They do not establish independent validation of scientific predictions or full reproducibility in a fresh environment.

## Scientific Safeguards

CuSelect-AI follows an evidence-first approach:

1. Maintain traceability to scientific sources.
2. Distinguish provisional claims from reviewed evidence.
3. Avoid unsupported rankings across unmatched experimental conditions.
4. Distinguish C₂+ selectivity from ethylene-specific selectivity.
5. Treat proposed reaction mechanisms as hypotheses unless adequately supported.
6. Avoid equating exploratory computational energies with electrochemical performance.
7. Require human scientific review for consequential research conclusions.

## Current Limitations

- End-to-end integration of newly discovered research cases across all three main sections is incomplete.
- Some experimental evidence records require verification-status reconciliation.
- Scientific interpretation depends on the quality and coverage of retrieved sources.
- Computational results require additional convergence and scientific validation.
- No validated ethylene Faradaic-efficiency prediction model is provided.
- Autonomous catalyst optimization has not been demonstrated.
- A fresh-environment installation and deployment test remains to be completed.

## Development Roadmap

- Connect persistent cases across Discover, Validate, and Decide.
- Improve provenance and evidence-review consistency.
- Develop structured, evidence-grounded hypothesis generation.
- Strengthen scientific benchmarking and computational assessment.
- Improve deployment, reproducibility, and research reporting.

## Project Philosophy

**Discover what is known. Validate what is supported. Decide what to investigate next.**

CuSelect-AI is designed to support scientific judgment, not replace experimental verification or expert review.
