# A Traceability-Aware Knowledge Graph Framework for Building Code Compliance Checking Using Large Language Models

**Anonymous Author(s)**  
**Target area:** engineering informatics, BIM, and automated compliance checking  
**Draft status:** first draft; citations and all numerical experimental findings remain to be verified.

## Abstract

Building-code compliance assessment is knowledge intensive because normative requirements are distributed across heterogeneous clauses, depend on applicability conditions, and often combine qualitative obligations with numerical thresholds. Existing keyword retrieval and rule-based approaches provide limited semantic coverage, whereas direct large language model (LLM) extraction can produce unsupported or non-auditable statements. This study proposes a traceability-aware framework that combines evidence-constrained LLM extraction, human review, a building-code knowledge graph, and rule-based project assessment. The framework requires every extracted entity, relation, and rule to cite a continuous span in its source clause; unreviewed LLM output is retained as an auditable annotation rather than being written directly into the graph. A project assessment layer links design parameters to reviewed rules and returns four states: pass, fail, pending, and advisory. The evaluation protocol uses a manually adjudicated corpus sampled from Chinese fire-protection and seismic-design codes, alongside an independently reviewed compliance-case set. It compares a pattern baseline, unconstrained JSON extraction, and the proposed evidence-constrained workflow using extraction F1, evidence locatability, assessment accuracy, macro F1, and improper-certainty rate. **[Insert verified experimental results and confidence intervals here.]** The study contributes an evidence-first approach to reducing hallucinated normative claims and making automated compliance outputs inspectable by engineering professionals.

**Keywords:** building code compliance; knowledge graph; large language model; information extraction; traceability; building information modelling.

## 1. Introduction

Design compliance checking is a persistent bottleneck in building delivery. A single design decision may be governed by several clauses whose meaning depends on occupancy, height, seismic intensity, fire risk, building component, or an exception stated elsewhere in a code. In practice, engineers must identify applicable clauses, translate them into project-specific conditions, and retain a defensible explanation for every conclusion. This work is repetitive but cannot be reduced safely to naïve text search because the applicability conditions are as important as the numerical requirements. **[CIT-AEC-COMPLIANCE]**

Knowledge graphs have been adopted in architecture, engineering, and construction research to connect building objects, regulations, and design data. Their value is strongest when graph facts can be traced to authoritative sources and when their semantics can be evaluated rather than merely visualised. However, manual graph construction is expensive, while automatically extracted graphs may inherit extraction errors or omit contextual qualifications. **[CIT-KG-AEC] [CIT-RULE-CHECKING]**

LLMs offer a practical means of structuring long-form regulatory text. They can identify candidate entities and formulate candidate relationships from clauses that are difficult to cover using hand-built patterns alone. Yet their fluent output creates a particular risk in the regulatory domain: a response may appear plausible without being justified by the clause under review. A reliable engineering workflow must therefore distinguish a candidate extraction from a reviewed knowledge assertion, preserve the original textual evidence, and decline binary conclusions when the project information or rule context is incomplete. **[CIT-LLM-REGULATION] [CIT-EXPLAINABLE-AI]**

This paper addresses that gap with a traceability-aware framework for building-code knowledge extraction and compliance checking. Rather than positioning an LLM as an autonomous compliance authority, the framework uses the LLM to propose structured, evidence-bound annotations that are reviewed before graph insertion. The resulting graph supports project assessments in which each decision is linked to a reviewed rule and, where available, to its originating clause. The research asks: (RQ1) does evidence-constrained extraction improve the reliability and auditability of extracted code knowledge; (RQ2) how does human review affect the quality of graph assertions and correction effort; and (RQ3) can a parameter-to-rule-to-clause chain produce appropriately calibrated compliance states?

The contributions are fourfold. First, the paper defines a lightweight ontology that represents building objects, conditions, numerical values, relations, constraints, source clauses, and review states. Second, it introduces an evidence constraint requiring continuous clause spans for every LLM-produced assertion. Third, it separates pending, reviewed, accepted, and rejected annotations so that model output is never mistaken for approved regulatory knowledge. Finally, it provides a reproducible evaluation protocol for extraction quality, evidence locatability, and uncertainty-aware project assessment.

## 2. Related Work

### 2.1 Automated building-code compliance checking

Prior work on automated compliance checking has combined BIM data, rule languages, and domain ontologies to test selected regulatory requirements. These methods can be precise when a rule has been formalised, but they require costly rule engineering and may struggle with textual clauses whose applicability conditions are implicit or dispersed. The final manuscript will compare the proposed method with these approaches, distinguishing code retrieval, rule formalisation, and end-to-end assessment. **[CIT-BIM-RULE-1] [CIT-BIM-RULE-2]**

### 2.2 Knowledge graphs for the built environment

Construction knowledge graphs model building concepts and their relations across design, construction, and operation. For compliance work, source provenance is central: a graph edge without a clause-level origin cannot provide an auditable basis for a regulatory judgment. The proposed framework therefore treats provenance and review status as first-class graph attributes rather than interface metadata. **[CIT-KG-PROVENANCE]**

### 2.3 LLM-based information extraction and trustworthy AI

Recent LLM research has shown strong performance in structured extraction but also demonstrates sensitivity to prompt wording, model version, and source ambiguity. In high-consequence domains, evidence grounding and human-in-the-loop review are common safeguards. This study evaluates those safeguards in the narrower setting of building-code clauses and reports both semantic extraction metrics and evidence-specific metrics. **[CIT-LLM-IE] [CIT-HUMAN-LOOP]**

## 3. Traceability-Aware Framework

### 3.1 Overview

The framework contains five stages: (1) code ingestion and clause segmentation; (2) candidate extraction; (3) evidence validation and human review; (4) knowledge-graph construction; and (5) project compliance assessment. The implementation currently imports CSV, spreadsheet, PDF, and Word sources into a SQLite-backed code repository. Its available corpus contains five Chinese building-code datasets and 962 imported clauses. The primary evaluation corpus comprises GB50016 fire-protection clauses and GB50011 seismic-design clauses; the remaining codes are reserved for pilot and transferability studies.

### 3.2 Ontology and evidence constraint

The ontology represents building objects, building parts, performance indicators, numerical values, standards, actions, and applicability conditions. Relations include `applies_to`, `has_attribute`, `requires`, `prohibits`, threshold relations, and containment relations. A rule records its subject, applicability condition, operator, threshold or required action, source standard, clause number, evidence span, and review status.

For every output item, the evidence must be a non-empty continuous substring of the source clause. If the proposed evidence cannot be located exactly, the item is rejected or returned for revision. This constraint does not guarantee that an interpretation is correct, but it prevents a candidate assertion from being detached from its regulatory source.

### 3.3 Candidate extraction and review

The LLM is prompted to return JSON arrays for entities, relations, and rules. Each array item includes a confidence value and evidence span. A deterministic parser validates JSON shape, controlled relation types, and exact evidence matching. Valid candidate output is stored as a pending annotation. Reviewers can accept, reject, or revise candidate items after reading the source clause; only accepted information is added to the knowledge graph. The paper will report the model identifier, access date, prompt version, temperature, output limit, and retry policy for every experiment.

### 3.4 Compliance assessment and uncertainty states

Project data are stored as structured parameters. A reviewed rule is evaluated only when its applicability conditions and required inputs are available. A `pass` means that complete inputs satisfy an applicable computable rule, whereas a `fail` means they violate one. `Pending` is used for incomplete project conditions, incomplete rule semantics, or unavailable evidence. `Advisory` records a reviewed but non-triggered condition or a professional attention item. Each returned result preserves the project input, expected value, explanation, linked clause, and run identifier.

## 4. Dataset and Experimental Design

The main corpus contains 320 clauses: all 67 imported GB50011 clauses and a stratified random sample of 253 GB50016 clauses. GB50016 sampling is stratified by leading clause chapter using seed 20260624. The pilot corpus contains 40 GB50096 clauses and 40 GB55019 clauses and is not used for the primary test results.

Two annotators independently create entities, relations, rules, applicability conditions, and continuous evidence spans. A third reviewer adjudicates disagreements. Agreement is calculated before adjudication; if the relevant agreement measure is below 0.70, the annotation instruction is revised and disputed categories are relabelled. The adjudicated corpus is the sole gold standard for extraction metrics.

Three methods are compared: a pattern baseline, unconstrained LLM JSON extraction, and evidence-constrained LLM extraction. Precision, recall, and F1 are computed separately for entities, relations, and rules. Evidence locatability is the share of output items whose cited text can be found as a continuous span in the source clause. Results are reported per code, as a macro average, and with 95% bootstrap confidence intervals.

The compliance layer is evaluated with 32 parameterised scenarios covering pass, fail, pending, and advisory states. The current set is a software regression suite that confirms implementation behaviour. Before publication, it will be independently reviewed by domain experts and any scenario whose expected outcome cannot be justified by its cited clause will be removed or corrected. Assessment metrics include accuracy, macro F1, linked-article locatability, and improper-certainty rate, defined as a `pass` or `fail` prediction for a scenario whose expert reference status is `pending`.

## 5. Results

### 5.1 Extraction quality

**Table 1. Extraction quality by method and code.**

| Method | Code | Entity F1 | Relation F1 | Rule F1 | Evidence locatability |
| --- | --- | ---: | ---: | ---: | ---: |
| Pattern baseline | GB50016 | [TBD] | [TBD] | [TBD] | [TBD] |
| Vanilla LLM | GB50016 | [TBD] | [TBD] | [TBD] | [TBD] |
| Proposed method | GB50016 | [TBD] | [TBD] | [TBD] | [TBD] |
| Pattern baseline | GB50011 | [TBD] | [TBD] | [TBD] | [TBD] |
| Vanilla LLM | GB50011 | [TBD] | [TBD] | [TBD] | [TBD] |
| Proposed method | GB50011 | [TBD] | [TBD] | [TBD] | [TBD] |

The final version will describe only statistically supported differences. In particular, it will separate improvement in semantic matching from improvement in evidence locatability.

### 5.2 Review burden and error analysis

**[Insert adjudicated acceptance rate, correction counts, reviewer time, and error taxonomy.]** Error categories will include unsupported evidence, incomplete applicability conditions, incorrect relation direction, numerical-threshold mismatch, and over-generalised rule statements.

### 5.3 Compliance assessment

**Table 2. Compliance assessment against independently reviewed cases.**

| Metric | Value |
| --- | ---: |
| Accuracy | [TBD] |
| Macro F1 | [TBD] |
| Article locatability | [TBD] |
| Improper-certainty rate | [TBD] |

The present 32-case suite is retained as a regression artefact and must not be presented as an independent performance result because its expected labels mirror the implemented rules.

## 6. Discussion and Threats to Validity

The framework is designed to support, rather than replace, professional judgment. Evidence tracing limits unsupported claims but does not resolve legal validity, edition applicability, cross-clause interactions, or domain-specific interpretation. The corpus is limited to selected Chinese codes, and its rule distribution may differ from other standards. LLM results can change with model updates; reporting model metadata, prompts, and raw outputs is therefore necessary but may not guarantee future replication. Finally, a reviewed graph may still omit relevant rules, so a `pending` output should be treated as calibrated uncertainty rather than a defect to be suppressed.

## 7. Conclusion

This paper presents a traceability-aware framework for converting building-code clauses into reviewable graph knowledge and for using that knowledge in uncertainty-aware compliance assessments. The key design choice is to bind every candidate assertion to a continuous source span and to require review before graph insertion. The completed study will quantify how that constraint affects extraction quality, auditability, reviewer effort, and compliance decision calibration. Future work will connect reviewed rules with BIM parameters, extend version-aware code comparison, and evaluate cross-jurisdictional transfer.

## Required figures

1. End-to-end architecture: ingestion, extraction, review, graph, and assessment.
2. Evidence-constrained annotation and approval workflow.
3. Project parameter → reviewed rule → source clause → result chain.
4. A representative reviewed subgraph and assessment trace.

## References

Replace every `[CIT-*]` marker with a verified reference before circulation. Do not retain placeholder citations in the submitted manuscript.
