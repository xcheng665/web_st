"""Create deterministic clause manifests for the SCI study.

This script only selects clauses. It never creates gold labels and never edits the
production SQLite database.
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend" / "instance" / "specifications.db"
OUT_DIR = ROOT / "research" / "datasets"
SEED = 20260624


def chapter(clause_number: str) -> str:
    token = str(clause_number).strip().split(".")[0]
    return token or "unclassified"


def fetch(conn: sqlite3.Connection, prefix: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT a.id, s.code, s.name, a.clause_number, a.content
        FROM article a JOIN specification s ON s.id = a.spec_id
        WHERE s.code LIKE ?
        ORDER BY a.id
        """,
        (f"{prefix}%",),
    ).fetchall()
    return [
        {"article_id": row[0], "specification": row[1], "specification_name": row[2],
         "clause_number": row[3], "content": row[4]}
        for row in rows
    ]


def proportional_sample(records: list[dict], size: int, rng: random.Random) -> list[dict]:
    if size > len(records):
        raise ValueError(f"requested {size} records but only {len(records)} are available")
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[chapter(record["clause_number"])].append(record)
    quotas = {key: int(size * len(items) / len(records)) for key, items in groups.items()}
    remainder = size - sum(quotas.values())
    fractions = sorted(
        ((size * len(items) / len(records) - quotas[key], key) for key, items in groups.items()),
        reverse=True,
    )
    for _, key in fractions[:remainder]:
        quotas[key] += 1
    selected = []
    for key in sorted(groups):
        selected.extend(rng.sample(groups[key], quotas[key]))
    return sorted(selected, key=lambda item: item["article_id"])


def annotation_record(record: dict, split: str) -> dict:
    return {
        **record,
        "split": split,
        "annotation_status": "unannotated",
        "annotations": {
            "annotator_a": {"entities": [], "relations": [], "rules": []},
            "annotator_b": {"entities": [], "relations": [], "rules": []},
            "adjudicated": {"entities": [], "relations": [], "rules": []},
        },
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build(db_path: Path) -> tuple[Path, Path]:
    rng = random.Random(SEED)
    with sqlite3.connect(db_path) as conn:
        fire = fetch(conn, "GB50016")
        seismic = fetch(conn, "GB50011")
        residential = fetch(conn, "GB50096")
        accessibility = fetch(conn, "GB55019")
    if len(seismic) != 67:
        raise ValueError(f"GB50011 census expected 67 clauses, found {len(seismic)}")
    main = proportional_sample(fire, 253, rng) + seismic
    pilot = proportional_sample(residential, 40, rng) + proportional_sample(accessibility, 40, rng)
    main_path = OUT_DIR / "main_gold_seed.jsonl"
    pilot_path = OUT_DIR / "pilot_seed.jsonl"
    write_jsonl(main_path, [annotation_record(item, "main") for item in sorted(main, key=lambda r: r["article_id"])])
    write_jsonl(pilot_path, [annotation_record(item, "pilot") for item in sorted(pilot, key=lambda r: r["article_id"])])
    return main_path, pilot_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    main_path, pilot_path = build(args.database)
    print(f"wrote {main_path}")
    print(f"wrote {pilot_path}")
