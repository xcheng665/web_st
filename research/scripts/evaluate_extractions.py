"""Score extraction predictions against adjudicated JSONL annotations.

Expected prediction rows contain article_id plus entities, relations, and rules.
Gold rows use the adjudicated section of the manifest format created by
build_manifests.py. Empty adjudicated records are rejected.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical(item: dict, kind: str) -> tuple:
    if kind == "entities":
        return tuple(str(item.get(key, "")).strip() for key in ("name", "type", "evidence"))
    if kind == "relations":
        return tuple(str(item.get(key, "")).strip() for key in ("source", "predicate", "target", "evidence"))
    return tuple(str(item.get(key, "")).strip() for key in ("name", "rule_type", "content", "evidence"))


def counts(gold: list[dict], predictions: dict[int, dict], kind: str) -> tuple[int, int, int]:
    tp = fp = fn = 0
    for row in gold:
        gold_items = {canonical(item, kind) for item in row["annotations"]["adjudicated"][kind]}
        predicted_items = {canonical(item, kind) for item in predictions.get(row["article_id"], {}).get(kind, [])}
        tp += len(gold_items & predicted_items)
        fp += len(predicted_items - gold_items)
        fn += len(gold_items - predicted_items)
    return tp, fp, fn


def metric(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0, "tp": tp, "fp": fp, "fn": fn}


def main(gold_path: Path, prediction_path: Path, output_path: Path) -> None:
    gold = read_jsonl(gold_path)
    if any(row["annotation_status"] != "adjudicated" for row in gold):
        raise ValueError("all gold rows must be adjudicated before scoring")
    predictions = {row["article_id"]: row for row in read_jsonl(prediction_path)}
    report = {kind: metric(*counts(gold, predictions, kind)) for kind in ("entities", "relations", "rules")}
    report["article_count"] = len(gold)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.gold, args.predictions, args.output)
