# Add Notebook 02 to an existing CuSelect-AI workspace (Mac mini)

## What to copy

If you already completed Notebooks 00 and 01, **use `CuSelect-AI_Notebook02_Update.zip`**, not the full workspace archive. Extract its contents directly *inside your existing `CuSelect-AI` root* so the paths below are created:

- `notebooks/02_Literature_and_Evidence.ipynb`
- `src/cuselect/evidence.py`
- `tests/test_evidence.py`
- `docs/LITERATURE_REVIEW_PROTOCOL.md`
- `data/references/02_human_reviewed_claims.csv` (empty template)

This update adds new files and does not replace notebooks 00 or 01.

## First run

1. Open your existing VS Code project folder `CuSelect-AI`.
2. In the VS Code Terminal verify `(cuselect)`; otherwise run `conda activate cuselect`.
3. Optional: `python -m pip install -e ".[notebook,app,dev]"` from the project root (your prior editable install usually already works).
4. Run `python -m pytest -q` and review any errors.
5. Open `notebooks/02_Literature_and_Evidence.ipynb`, select **Python (CuSelect-AI)**.
6. Use **Restart Kernel → Run All**. The notebook detects the root automatically even though VS Code starts it inside `notebooks/`.
7. It initially runs **offline**: it performs syntax checks but does not query Crossref. The report must say `metadata_online_lookup_enabled: false` and `human_verified_claims: 0`.
8. To fetch live bibliographic metadata on your Mac, edit `RUN_LIVE_CROSSREF_LOOKUP = True` in Section 2.3. Network errors are reported, not marked as verified. Verify returned titles/years manually.
9. Read and inspect papers; enter source-checked claims in `data/references/02_human_reviewed_claims.csv` using the draft schema. Rerun the export cell.

## Expected outputs

- `data/interim/02_metadata_audit.csv`
- `data/interim/02_search_plan.csv` (searches are **planned**, not secretly executed)
- `data/interim/02_source_review_queue.csv`
- `data/interim/02_draft_claims.csv`
- `data/processed/02_verified_claims.csv` (header only until human approval)
- `outputs/reports/02_evidence_readiness.json`

No DFT or ethylene FE calculations are performed. The scientific step is complete only after the claims relevant to the next notebook have been reviewed against their source locations.
