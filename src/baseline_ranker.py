"""Phase 3 — baseline ranker CLI.

Streams candidates.jsonl, applies recall gates + interpretable scoring
(src/scoring.py), and produces a submission-format top-100 CSV.

Usage:
  python -m src.baseline_ranker                          # full run
  python -m src.baseline_ranker --skip 0 --limit 34000 --tag c1   # chunked
  python -m src.baseline_ranker --merge c1 c2 c3         # merge chunk shortlists
  python -m src.baseline_ranker --explain CAND_0000031 CAND_0000074

Outputs:
  outputs/baseline_top100.csv      submission format (candidate_id,rank,score,reasoning)
  outputs/baseline_shortlist.csv   top-500 with full component breakdown (debug)
"""

from __future__ import annotations

import argparse
import ast
import csv
import time

from src.config import OUTPUTS_DIR
from src.data_loader import iter_candidates
from src.scoring import score_candidate

DEBUG_COLS = ["candidate_id", "score", "fit", "career_ev", "career_cats", "shipped",
              "title_sc", "skills_sc", "exp_sc", "loc_sc", "penalties", "behavioral",
              "honeypot_flags", "recall", "_title", "_yoe", "_loc"]


def brief_reasoning(b: dict) -> str:
    """Factual placeholder reasoning from the breakdown (Phase 5 replaces this)."""
    parts = [f"{b['_title']}, {b['_yoe']}y, {b['_loc'].split(',')[0]}"]
    if b["career_cats"]:
        parts.append("career evidence: " + "/".join(b["career_cats"]))
    if b["penalties"]:
        parts.append("concerns: " + "; ".join(p.split(" x")[0] for p in b["penalties"]))
    if b["_notice"] > 60:
        parts.append(f"notice {b['_notice']}d")
    if b["_days_inactive"] > 180:
        parts.append(f"inactive {b['_days_inactive']}d")
    return ". ".join(parts)


def rank(path: str | None, limit: int | None, skip: int = 0, tag: str = "") -> None:
    t0 = time.time()
    scored = []
    n = 0
    for rec in iter_candidates(path=path, limit=limit, skip=skip):
        n += 1
        b = score_candidate(rec)
        if b:
            scored.append(b)
    scored.sort(key=lambda b: (-b["score"], b["candidate_id"]))
    sfx = f"_{tag}" if tag else ""
    OUTPUTS_DIR.mkdir(exist_ok=True)
    keep = scored[:500]
    with open(OUTPUTS_DIR / f"baseline_shortlist{sfx}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(DEBUG_COLS + ["_notice", "_days_inactive", "_rr"])
        for b in keep:
            w.writerow([b[c] for c in DEBUG_COLS] + [b["_notice"], b["_days_inactive"], b["_rr"]])
    print(f"Scanned {n:,} | recalled {len(scored):,} | kept top {len(keep)} "
          f"| {time.time()-t0:.1f}s -> baseline_shortlist{sfx}.csv")
    if not tag:
        _write_top100(keep)


def _write_top100(shortlist: list[dict]) -> None:
    with open(OUTPUTS_DIR / "baseline_top100.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "rank", "score", "reasoning"])
        for i, b in enumerate(shortlist[:100], start=1):
            w.writerow([b["candidate_id"], i, f"{b['score']:.6f}", brief_reasoning(b)])
    print("Top-100 -> outputs/baseline_top100.csv")


def merge(tags: list[str]) -> None:
    rows: list[dict] = []
    for tag in tags:
        with open(OUTPUTS_DIR / f"baseline_shortlist_{tag}.csv", encoding="utf-8", newline="") as f:
            rows.extend(csv.DictReader(f))
    for r in rows:
        r["score"] = float(r["score"])
        r["_notice"] = int(r["_notice"])
        r["_days_inactive"] = int(r["_days_inactive"])
        r["career_cats"] = ast.literal_eval(r["career_cats"]) if r["career_cats"].startswith("[") else []
        r["penalties"] = ast.literal_eval(r["penalties"]) if r["penalties"].startswith("[") else []
        r["_yoe"] = float(r["_yoe"])
    rows.sort(key=lambda b: (-b["score"], b["candidate_id"]))
    with open(OUTPUTS_DIR / "baseline_shortlist.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        cols = list(rows[0].keys())
        w.writerow(cols)
        for r in rows[:500]:
            w.writerow([r[c] for c in cols])
    _write_top100(rows)
    print(f"Merged {len(tags)} chunks ({len(rows)} shortlisted candidates)")


def explain(ids: list[str], path: str | None) -> None:
    targets = set(ids)
    for rec in iter_candidates(path=path):
        if rec["candidate_id"] in targets:
            b = score_candidate(rec)
            print("=" * 72)
            if b is None:
                print(rec["candidate_id"], "| NOT RECALLED (fails all three gates)")
                p = rec["profile"]
                print(f"  {p['current_title']} | {p['years_of_experience']}y | {p['location']}")
            else:
                print(f"{b['candidate_id']} | {b['_title']} | {b['_yoe']}y | {b['_loc']}")
                print(f"  recall gates [Title/CareerText/Skills]: {b['recall']}")
                print(f"  career_ev={b['career_ev']} ({', '.join(b['career_cats']) or 'none'}; "
                      f"shipped={b['shipped']}) title={b['title_sc']} skills={b['skills_sc']} "
                      f"exp={b['exp_sc']} loc={b['loc_sc']}")
                print(f"  fit={b['fit']} | penalties: {b['penalties'] or 'none'} | "
                      f"behavioral={b['behavioral']} | honeypot: {b['honeypot_flags'] or 'clean'}")
                print(f"  FINAL SCORE = {b['score']}")
            targets.discard(rec["candidate_id"])
            if not targets:
                return
    for t in targets:
        print(f"{t}: not found in dataset")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--tag", default="")
    ap.add_argument("--merge", nargs="+", default=None)
    ap.add_argument("--explain", nargs="+", default=None)
    a = ap.parse_args()
    if a.explain:
        explain(a.explain, a.candidates)
    elif a.merge:
        merge(a.merge)
    else:
        rank(a.candidates, a.limit, skip=a.skip, tag=a.tag)


if __name__ == "__main__":
    main()
