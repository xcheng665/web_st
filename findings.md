# Research findings

- SQLite currently contains five specifications and 962 clauses.
- The primary corpus is GB50016 (503 clauses) plus GB50011 (67 clauses).
- Existing graph records were produced by a local demonstration mechanism; the database has no reviewable LLM annotations.
- The compliance engine can return `pass`, `fail`, `pending`, and `advisory` results with a linked article where applicable.
- Deterministic manifests were generated and verified: 320 primary clauses (253 GB50016 and 67 GB50011) plus 80 pilot clauses (40 GB50096 and 40 GB55019).
- The 32 synthetic compliance scenarios pass against the current implementation with 96.875% linked-article availability. This is a regression result only because the expected labels were derived from the same implementation; it is not manuscript performance evidence.
- A 2021–2026 reference package was generated around BIM/automated code compliance checking, building-code knowledge graphs, NLP/LLM regulation interpretation, semantic web, and IFC/BIM rule checking. OpenAlex supplied 20 screened records; 4 openly downloadable PDFs were retrieved automatically. Several MDPI/ITcon/Nature links were advertised as open but command-line download was blocked by publisher 403/certificate behavior, so the package keeps DOI, OpenAlex, official PDF URL status, BibTeX, CSV/JSON metadata, and one Markdown note per paper instead of using unauthorized sources.
