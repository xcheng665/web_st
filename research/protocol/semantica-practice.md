# Semantica practice protocol

This practice adapts the repository's local building-code corpus to Semantica's
context-graph and decision-intelligence APIs. It is intentionally separate from
the manuscript evaluation data.

## Mapping

| Local evidence | Semantica node | Required provenance |
| --- | --- | --- |
| One CSV specification | `Specification` | filename, detected encoding, SHA-256 |
| One clause row | `Clause` | clause number, source row, filename, SHA-256 |
| Clause containing an imperative term | `Requirement` | source clause and source row |
| Deterministic pre-check/review record | `Decision` | evidence clause IDs, reviewer role, no gold labels |

The graph records `contains_clause`, `states_requirement`, and `supported_by`
edges. It also records a `CAUSED` edge from the deterministic pre-check to the
human-review decision, so `trace_decision_chain()` and
`analyze_decision_impact()` can be exercised.

## Reproducibility boundary

The script reads the CSV files directly, detects UTF-8/GB18030-compatible
encodings, and writes a JSON artifact. It does not call an LLM, create gold
annotations, or report extraction/compliance performance. Existing demo graph
records and the research gold-label workflow remain untouched.

Run it in an isolated environment because Semantica 0.6.5 has a NumPy 2.x
requirement:

```powershell
python -m pip install -r research/requirements-semantica.txt
python research/scripts/practice_semantica.py --sample-per-spec 6
```
