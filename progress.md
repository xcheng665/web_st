# Progress log

## 2026-06-24

- Created the seven-day SCI manuscript sprint workspace.
- Began protocol, sample-manifest, compliance-case, and manuscript preparation.
- Added ontology, annotation guide, experiment protocol, 32-case regression suite, and first English manuscript draft.
- Generated and verified deterministic manifests; syntax-checked all research scripts; reran the compliance regression suite successfully.
- Created and visually checked a Python-generated SVG/PDF/PNG flowchart style board with linear, evidence-loop, and traceability-swimlane alternatives.
- Produced a Chinese manuscript version aligned with the English draft and the same evidence/placeholder restrictions.

## 2026-06-25

- Added `research/scripts/collect_references.py` to search recent ACC/BIM/KG/LLM literature, collect metadata, download advertised open-access PDFs when accessible, and generate CSV/JSON/BibTeX/Markdown outputs.
- Semantic Scholar API returned HTTP 429, so the search was switched to OpenAlex. This avoided repeated rate-limit failures.
- MDPI official PDF links returned HTTP 403 in command-line access; ITcon downloads needed certificate-tolerant handling. No unauthorized full-text sources were used.
- Added `research/scripts/package_reference_notes.py` to generate one Markdown reference note per paper and refresh the reference zip package.
- Generated and verified `research/references/building_code_compliance_references_2021_2026.zip`: 20 papers, 20 paper notes, 4 automatically downloaded open PDFs, 29 files total, approximately 5.6 MB.
