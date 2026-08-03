# Gold-annotation guideline

## Unit and independence

The annotation unit is one imported clause. Two annotators work independently and may not inspect model output before completing their first pass. A third reviewer resolves disagreements. Record the final adjudicated label and the reason for each changed item.

## What to label

1. **Entities**: explicit building objects, parts, performance indicators, numerical values, standards, actions, and conditions.
2. **Relations**: only relations stated in the clause, using the controlled vocabulary in `ontology.yaml`.
3. **Rules**: a rule must contain an applicability condition when one is stated, plus the subject and required/prohibited/threshold expression.
4. **Evidence**: every item must quote one continuous substring from the clause. Do not normalize, paraphrase, or join discontinuous spans.

## Exclusions

- Do not infer a missing design condition from domain knowledge.
- Do not label examples, explanatory notes, or cross-references as rules unless they impose a requirement.
- Do not create a `pass` or `fail` judgment from an incomplete condition. Use `pending` in case evaluation.

## Agreement and adjudication

Calculate agreement before adjudication. Treat an item as matching only when its normalized semantic fields and evidence span agree. If agreement is below 0.70, revise the guideline, re-label disputed categories, and retain both original passes for audit.
