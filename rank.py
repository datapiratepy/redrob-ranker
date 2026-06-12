"""Single-command submission reproduction (submission_spec.md §10.3).

    python rank.py --candidates ../candidates.jsonl --out ./submission.csv

Two streaming passes over the candidate pool, CPU-only, no network:
  pass 1 — score all candidates (recall gates + interpretable scoring)
  pass 2 — fetch full records of the top 100 and generate verified reasoning

Measured runtime on the full 100K pool: ~60s total, well inside the
5-minute / 16 GB challenge budget. Deterministic: identical input produces a
byte-identical CSV (template choices are keyed on candidate_id checksums).
"""

from __future__ import annotations

import argparse
import csv
import time

from src.data_loader import iter_candidates
from src.reasoning_engine import compose, extract_facts, verify
from src.scoring import score_candidate


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates", required=True, help="path to candidates.jsonl(.gz)")
    ap.add_argument("--out", default="./submission.csv")
    a = ap.parse_args()

    # ---- pass 1: score everything ----
    t0 = time.time()
    scored: list[tuple[float, str]] = []
    n = 0
    for rec in iter_candidates(path=a.candidates):
        n += 1
        b = score_candidate(rec)
        if b:
            scored.append((b["score"], b["candidate_id"]))
    scored.sort(key=lambda x: (-x[0], x[1]))  # spec tie-break: candidate_id asc
    top = scored[:100]
    ranks = {cid: i for i, (_, cid) in enumerate(top, start=1)}
    print(f"pass 1: scored {n:,} candidates, recalled {len(scored):,} "
          f"({time.time() - t0:.0f}s)")

    # ---- pass 2: reasoning for the top 100 ----
    t1 = time.time()
    records: dict[str, dict] = {}
    for rec in iter_candidates(path=a.candidates):
        if rec["candidate_id"] in ranks:
            records[rec["candidate_id"]] = rec
            if len(records) == 100:
                break
    reasonings = {}
    for cid, rank in ranks.items():
        b = score_candidate(records[cid])
        reasonings[cid] = compose(rank, extract_facts(records[cid], b))
    problems = verify(reasonings, records)
    if problems:
        raise SystemExit("reasoning verification failed:\n" + "\n".join(problems))
    print(f"pass 2: reasoning for 100 candidates, verification clean "
          f"({time.time() - t1:.0f}s)")

    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "rank", "score", "reasoning"])
        for score, cid in top:
            w.writerow([cid, ranks[cid], f"{score:.6f}", reasonings[cid]])
    print(f"wrote {a.out} | total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
