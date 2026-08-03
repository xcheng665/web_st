# Reproducibility package

This directory contains the materials used to turn the application into an auditable research study. It deliberately separates research evidence from the production SQLite database.

## Directory map

- `protocol/`: ontology, annotation instructions, and frozen experiment configuration.
- `datasets/`: deterministic sample manifests; no gold labels are invented here.
- `cases/`: parameterized compliance scenarios with an explicit target check.
- `scripts/`: deterministic sampling and evaluation utilities.
- `manuscript/`: the English first draft and result-table templates.

## Data-status convention

`unannotated` means a clause is a sampling record only. It must not be used to report extraction performance. Gold annotations require two independent labelers and adjudication according to `protocol/annotation-guideline.md`.
