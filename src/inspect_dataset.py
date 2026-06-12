"""Structural verification of candidates.jsonl — Phase 0 gate.

Run before anything else. Confirms the dataset matches the published schema
contract: record count, unique well-formed IDs, required keys, signal count.

Usage:
    python -m src.inspect_dataset                 # full scan (all 100K)
    python -m src.inspect_dataset --limit 5000    # quick pass
    python -m src.inspect_dataset --candidates /path/to/candidates.jsonl
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter

from src.config import EXPECTED_CANDIDATE_COUNT, resolve_candidates_path
from src.data_loader import iter_candidates, validate_record

MAX_PROBLEMS_SHOWN = 20


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates", default=None, help="path to candidates.jsonl(.gz)")
    ap.add_argument("--limit", type=int, default=None, help="scan only first N records")
    args = ap.parse_args()

    path = resolve_candidates_path(args.candidates)
    print(f"Dataset : {path}")
    print(f"Scan    : {'first ' + str(args.limit) if args.limit else 'FULL'}\n")

    t0 = time.time()
    n = 0
    ids: set[str] = set()
    duplicate_ids = 0
    problems: list[tuple[str, str]] = []  # (candidate_id, problem)
    title_counter: Counter[str] = Counter()

    for rec in iter_candidates(path=path, limit=args.limit):
        n += 1
        cid = rec.get("candidate_id", f"<line {n}>")

        if cid in ids:
            duplicate_ids += 1
            problems.append((cid, "duplicate candidate_id"))
        else:
            ids.add(cid)

        for p in validate_record(rec):
            problems.append((cid, p))

        title_counter[rec.get("profile", {}).get("current_title", "<missing>")] += 1

        if n % 20_000 == 0:
            print(f"  ... {n:,} records ({time.time() - t0:.0f}s)")

    elapsed = time.time() - t0

    print(f"\n{'=' * 60}")
    print(f"Records scanned      : {n:,}")
    if args.limit is None:
        status = "OK" if n == EXPECTED_CANDIDATE_COUNT else "MISMATCH"
        print(f"Expected count       : {EXPECTED_CANDIDATE_COUNT:,}  [{status}]")
    print(f"Unique candidate_ids : {len(ids):,}  (duplicates: {duplicate_ids})")
    print(f"Distinct job titles  : {len(title_counter):,}")
    print(f"Structural problems  : {len(problems)}")
    print(f"Scan time            : {elapsed:.1f}s")

    if problems:
        print(f"\nFirst {min(len(problems), MAX_PROBLEMS_SHOWN)} problems:")
        for cid, p in problems[:MAX_PROBLEMS_SHOWN]:
            print(f"  {cid}: {p}")

    print(f"\nTop 10 titles: {title_counter.most_common(10)}")

    ok = (len(problems) == 0) and (args.limit is not None or n == EXPECTED_CANDIDATE_COUNT)
    print(f"\nRESULT: {'PASS — dataset structure verified' if ok else 'FAIL — investigate problems above'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
