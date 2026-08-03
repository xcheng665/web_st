"""Execute the fixed compliance case suite without changing application data."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app import create_app  # noqa: E402
from compliance_service import run_checks  # noqa: E402


def evaluate(case_path: Path) -> dict:
    suite = json.loads(case_path.read_text(encoding="utf-8"))
    app = create_app()
    rows = []
    with app.app_context():
        for case in suite["cases"]:
            result = next((item for item in run_checks(case["parameters"]) if item.title == case["target_check_title"]), None)
            actual = result.status if result else "missing"
            evidence_locatable = bool(result and result.article and getattr(result.article, "content", ""))
            rows.append({
                "id": case["id"], "expected": case["expected_status"], "actual": actual,
                "correct": actual == case["expected_status"],
                "evidence_locatable": evidence_locatable,
                "improper_certainty": case["expected_status"] == "pending" and actual in {"pass", "fail"},
            })
    labels = ["pass", "fail", "pending", "advisory"]
    per_label = {}
    for label in labels:
        tp = sum(row["expected"] == label and row["actual"] == label for row in rows)
        fp = sum(row["expected"] != label and row["actual"] == label for row in rows)
        fn = sum(row["expected"] == label and row["actual"] != label for row in rows)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        per_label[label] = {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}
    return {
        "case_count": len(rows),
        "status_counts": Counter(row["expected"] for row in rows),
        "accuracy": sum(row["correct"] for row in rows) / len(rows),
        "macro_f1": sum(metric["f1"] for metric in per_label.values()) / len(per_label),
        "article_locatability": sum(row["evidence_locatable"] for row in rows) / len(rows),
        "improper_certainty_rate": sum(row["improper_certainty"] for row in rows) / len(rows),
        "per_label": per_label,
        "rows": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=ROOT / "research" / "cases" / "compliance_cases.json")
    parser.add_argument("--output", type=Path, default=ROOT / "research" / "results" / "compliance_case_results.json")
    args = parser.parse_args()
    result = evaluate(args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, ensure_ascii=False, indent=2))
