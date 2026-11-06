# Scientific data layout

- `papers.csv`: Stage-1 **bibliographic seed register**, not evidence that every cited paper or numerical claim has been reverified in this new stage. Verify DOI/title/source before extraction.
- `evidence_template.csv`: an EMPTY schema for source-linked scientific claims; no real observations are filled in here yet.
- `raw/`: licensed source files and original downloads. Do not commit copyrighted papers or private industrial data.
- `interim/`: extracted text and candidate records awaiting validation. Git-ignored.
- `processed/`: curated data after QC and DOI-based split assignment. Git-ignored until approved for distribution.
- `references/`: supplementary small reference assets, licenses and data dictionaries.

Source provenance, units, reactor type, potential reference, extraction method and review status must always accompany observed numerical values.
