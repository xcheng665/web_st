"""Build a small, evidence-first Semantica context graph from local standards.

This is an integration practice, not an extraction benchmark.  It uses the
repository's CSV standards as source evidence, creates a deterministic graph,
and records a two-step decision chain so Semantica's context/decision APIs are
exercised without inventing annotations or metrics.

The Semantica dependency is intentionally optional.  Use ``--semantica-path``
when validating against an isolated install, for example:

    python research/scripts/practice_semantica.py \
        --semantica-path C:/path/to/semantica/site-packages
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk", "gb2312")
REQUIRED_TERMS = ("必须", "应", "不应", "严禁", "不得")


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-dir", type=Path, default=root / "规范数据集", help="CSV directory"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "research" / "artifacts" / "semantica_building_code_graph.json",
        help="JSON artifact path",
    )
    parser.add_argument(
        "--sample-per-spec",
        type=int,
        default=6,
        help="Maximum number of source clauses retained per CSV",
    )
    parser.add_argument(
        "--semantica-path",
        type=Path,
        help="Optional site-packages directory containing semantica",
    )
    return parser.parse_args()


def load_context_graph(semantica_path: Path | None):
    if semantica_path:
        sys.path.insert(0, str(semantica_path.resolve()))
    try:
        import semantica
        from semantica.context import ContextGraph
    except ImportError as exc:  # pragma: no cover - exercised by the CLI user
        raise SystemExit(
            "Semantica is not available. Install it in an isolated environment "
            "with research/requirements-semantica.txt, or pass --semantica-path."
        ) from exc
    return semantica, ContextGraph


def choose_encoding(raw: bytes) -> tuple[str, str]:
    """Return the first lossless decoding and its text."""
    failures: list[str] = []
    for encoding in ENCODINGS:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError as exc:
            failures.append(f"{encoding}: {exc}")
            continue
        if "�" not in text:
            return encoding, text
    raise ValueError("Unable to decode CSV without replacement characters: " + "; ".join(failures))


def normalize_code(value: str) -> str:
    match = re.search(r"GB\d{5}", value.upper())
    return match.group(0) if match else value.strip()


def safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "_", value).strip("_")


def read_csv(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    encoding, text = choose_encoding(raw)
    rows = [row for row in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in row)]
    if not rows:
        raise ValueError(f"Empty CSV: {path}")

    first = [cell.strip().lower() for cell in rows[0]]
    header_tokens = {"规范", "规范名称", "标准名称", "条文", "条文号", "条文内容", "内容"}
    has_header = any(cell in header_tokens for cell in first)
    data_rows = rows[1:] if has_header else rows
    if has_header:
        header = rows[0]
        positions = {cell.strip(): index for index, cell in enumerate(header)}
        code_index = next((positions[key] for key in positions if "规范" in key or "标准" in key), 0)
        clause_index = next((positions[key] for key in positions if "条文" in key or "条款" in key), 1)
        content_index = next((positions[key] for key in positions if "内容" in key or "正文" in key), 2)
    else:
        code_index, clause_index, content_index = 0, 1, 2

    records: list[dict[str, str]] = []
    for row_number, row in enumerate(data_rows, start=2 if has_header else 1):
        if len(row) <= max(code_index, clause_index, content_index):
            continue
        code = row[code_index].strip()
        clause = row[clause_index].strip()
        content = row[content_index].strip()
        if code and clause and content:
            records.append({"code": code, "clause": clause, "content": content, "row": str(row_number)})

    return {
        "path": str(path),
        "filename": path.name,
        "encoding": encoding,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "records": records,
    }


def iter_source_files(dataset_dir: Path) -> Iterable[Path]:
    yield from sorted(dataset_dir.glob("*.csv"), key=lambda item: item.name)


def pick_evidence(records_by_code: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    """Prefer clauses used by the existing local compliance service."""
    preferred = {
        "GB50096": ("5.1.2", "5.2.1", "5.5.2", "6.4.1"),
        "GB50011": ("1.0.2", "3.3.2"),
        "GB50016": ("3.7.6", "3.3.3"),
    }
    selected: list[dict[str, str]] = []
    for code, clauses in preferred.items():
        for wanted in clauses:
            match = next((item for item in records_by_code.get(code, []) if item["clause"].startswith(wanted)), None)
            if match:
                selected.append(match)
    return selected


def build_graph(files: list[dict[str, Any]], sample_per_spec: int, ContextGraph):
    # Keep the practice deterministic and lightweight; advanced analytics can
    # be enabled later in a separate experiment without changing this corpus.
    graph = ContextGraph(advanced_analytics=False, extract_entities=False, extract_relationships=False)
    all_records: list[dict[str, Any]] = []
    records_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_summary: list[dict[str, Any]] = []

    for source in files:
        records = source["records"]
        code = normalize_code(records[0]["code"] if records else source["filename"])
        selected = records[:sample_per_spec]
        source["code"] = code
        source["selected_records"] = len(selected)
        source_summary.append({key: source[key] for key in ("filename", "code", "encoding", "sha256", "selected_records")})
        for item in selected:
            enriched = {**item, "code": code, "source": source}
            all_records.append(enriched)
            records_by_code[code].append(enriched)

        spec_id = f"spec:{safe_id(code)}"
        graph.add_node(
            spec_id,
            "Specification",
            content=code,
            source_file=source["filename"],
            source_encoding=source["encoding"],
            source_sha256=source["sha256"],
        )
        for item in selected:
            clause_key = f"{code}:{item['clause']}:{hashlib.sha1(item['content'].encode('utf-8')).hexdigest()[:10]}"
            clause_id = f"clause:{safe_id(clause_key)}"
            item["node_id"] = clause_id
            # ``records_by_code`` stores shallow copies so the preferred
            # evidence selector can keep provenance and the graph node ID
            # together.
            for record in records_by_code[code]:
                if record["row"] == item["row"] and record["clause"] == item["clause"]:
                    record["node_id"] = clause_id
            graph.add_node(
                clause_id,
                "Clause",
                content=item["content"],
                specification=code,
                clause_number=item["clause"],
                source_file=source["filename"],
                source_row=item["row"],
                source_encoding=source["encoding"],
                source_sha256=source["sha256"],
                evidence_uri=f"csv://{source['filename']}#row={item['row']}",
            )
            graph.add_edge(
                spec_id,
                clause_id,
                edge_type="contains_clause",
                source_file=source["filename"],
                clause_number=item["clause"],
            )
            if any(term in item["content"] for term in REQUIRED_TERMS):
                requirement_id = f"requirement:{safe_id(clause_key)}"
                graph.add_node(
                    requirement_id,
                    "Requirement",
                    content=item["content"],
                    specification=code,
                    clause_number=item["clause"],
                    source_file=source["filename"],
                    source_row=item["row"],
                    source_sha256=source["sha256"],
                )
                graph.add_edge(clause_id, requirement_id, edge_type="states_requirement")

    preferred = pick_evidence(records_by_code)
    evidence_ids = [item["node_id"] for item in preferred if "node_id" in item]
    spec_ids = sorted({f"spec:{safe_id(item['code'])}" for item in all_records})
    decision_metadata = {
        "source_policy": "local deterministic practice; no LLM extraction",
        "evidence_clause_ids": evidence_ids,
        "gold_labels_used": False,
        "evaluation_metric": None,
    }
    precheck_id = graph.record_decision(
        category="building_code_precheck",
        scenario="用本地建筑规范条文构建可追溯的合规预检查上下文",
        reasoning="只把 CSV 条文作为证据节点，并保留规范文件、编码、行号和 SHA-256；本步骤不声称完成规范符合性判定。",
        outcome="requires_human_review",
        confidence=1.0,
        entities=spec_ids,
        decision_maker="deterministic_practice",
        metadata=decision_metadata,
        # Explicit timestamps make the causal trace deterministic instead of
        # depending on wall-clock resolution when two records are adjacent.
        timestamp=1.0,
    )
    review_id = graph.record_decision(
        category="building_code_review",
        scenario="对建筑规范预检查结果进行人工复核",
        reasoning="研究规范要求将未标注条文与 gold evaluation 分开；因此实践输出保持待复核，不生成性能结论。",
        outcome="pending_signoff",
        confidence=1.0,
        entities=spec_ids,
        decision_maker="human_reviewer",
        metadata={**decision_metadata, "review_of": precheck_id},
        timestamp=2.0,
    )
    graph.add_causal_relationship(precheck_id, review_id, relationship_type="CAUSED")
    for clause_id in evidence_ids:
        graph.add_edge(precheck_id, clause_id, edge_type="supported_by", evidence_role="source_clause")

    result = {
        "artifact_type": "semantica_context_graph_practice",
        "not_evaluation": True,
        "gold_labels_used": False,
        "performance_metrics": None,
        "source_summary": source_summary,
        "selected_clause_count": len(all_records),
        "preferred_evidence_count": len(evidence_ids),
        "decision_ids": {"precheck": precheck_id, "review": review_id},
        "decision_trace": graph.trace_decision_chain(review_id),
        "decision_impact": graph.analyze_decision_impact(precheck_id),
        "similar_decisions": graph.find_similar_decisions("建筑规范 条文 预检查", max_results=5, min_similarity=0.0),
        "graph_summary": graph.get_graph_summary(),
        "graph": graph.to_dict(),
    }
    return result


def main() -> None:
    args = parse_args()
    if args.sample_per_spec < 1:
        raise SystemExit("--sample-per-spec must be at least 1")
    if not args.dataset_dir.is_dir():
        raise SystemExit(f"Dataset directory not found: {args.dataset_dir}")

    semantica, ContextGraph = load_context_graph(args.semantica_path)
    files = [read_csv(path) for path in iter_source_files(args.dataset_dir)]
    if not files:
        raise SystemExit(f"No CSV files found in {args.dataset_dir}")
    result = build_graph(files, args.sample_per_spec, ContextGraph)
    result["semantica_version"] = getattr(semantica, "__version__", "unknown")
    result["encoding_counts"] = dict(Counter(item["encoding"] for item in result["source_summary"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "semantica_version": result["semantica_version"],
        "graph_summary": result["graph_summary"],
        "selected_clause_count": result["selected_clause_count"],
        "preferred_evidence_count": result["preferred_evidence_count"],
        "not_evaluation": result["not_evaluation"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
