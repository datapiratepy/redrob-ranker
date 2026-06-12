"""Phase 8 — hopper-penalty investigation probe. READ-ONLY: ranking unchanged.

Questions:
1. Who is materially affected by the job-hopper penalty (>=3 stints, median <20mo)?
2. How do the top-100s differ under x0.75 (current) / x0.85 (weaker) / x1.00 (none)?
3. Are penalized candidates actually "title-chasers" per the JD (ascending title
   ladder across short stints), or does the detector over-fire on lateral movers?
4. Does hopping correlate with anything quality-relevant in this dataset
   (career evidence, behavioral signals, trap membership)?

Usage:  python -m src.hopper_probe --skip N --limit M --tag hX
        python -m src.hopper_probe --merge h1 h2 h3
"""

from __future__ import annotations

import argparse
import json
import re

from src.config import OUTPUTS_DIR
from src.data_loader import iter_candidates
from src.scoring import score_candidate

LEVEL = [
    (re.compile(r"principal|vp|director|head", re.I), 4),
    (re.compile(r"staff|lead", re.I), 3),
    (re.compile(r"senior|sr\.", re.I), 2),
    (re.compile(r"junior|intern|trainee", re.I), 0),
]


def title_level(title: str) -> int:
    for rx, lv in LEVEL:
        if rx.search(title):
            return lv
    return 1


def ladder_pattern(career: list[dict]) -> str:
    """Chronological title-seniority pattern: 'climbing' / 'lateral' / 'mixed'."""
    stints = sorted(career, key=lambda s: s.get("start_date") or "")
    levels = [title_level(s.get("title", "")) for s in stints]
    if len(levels) < 3:
        return "short"
    diffs = [b - a for a, b in zip(levels, levels[1:])]
    if all(d >= 0 for d in diffs) and sum(diffs) >= 2:
        return "climbing"
    if all(d == 0 for d in diffs):
        return "lateral"
    return "mixed"


def run(path: str | None, limit: int | None, skip: int, tag: str) -> None:
    pool, hoppers = [], []
    for rec in iter_candidates(path=path, limit=limit, skip=skip):
        b = score_candidate(rec)
        if b is None:
            continue
        is_hop = any("hopper" in p for p in b["penalties"])
        pool.append((b["candidate_id"], b["score"], int(is_hop), int(bool(b["honeypot_flags"]))))
        if is_hop:
            career = rec["career_history"]
            durs = sorted(s.get("duration_months", 0) for s in career)
            hoppers.append({
                "cid": b["candidate_id"], "title": b["_title"], "yoe": b["_yoe"],
                "score": b["score"], "fit": b["fit"], "career_ev": b["career_ev"],
                "behavioral": b["behavioral"], "hp": bool(b["honeypot_flags"]),
                "n_stints": len(career), "median_stint": durs[len(durs) // 2],
                "ladder": ladder_pattern(career), "rr": b["_rr"],
            })
    sfx = f"_{tag}" if tag else ""
    json.dump(pool, open(OUTPUTS_DIR / f"hopper_pool{sfx}.json", "w"))
    json.dump(hoppers, open(OUTPUTS_DIR / f"hopper_affected{sfx}.json", "w"))
    print(f"recalled {len(pool)}, hopper-penalized {len(hoppers)} (skip={skip})")


def merge(tags: list[str]) -> None:
    pool, hoppers = [], []
    for t in tags:
        pool += json.load(open(OUTPUTS_DIR / f"hopper_pool_{t}.json"))
        hoppers += json.load(open(OUTPUTS_DIR / f"hopper_affected_{t}.json"))
    json.dump(hoppers, open(OUTPUTS_DIR / "hopper_affected.json", "w"), indent=1)

    def top100(mult: float) -> list[str]:
        scored = [(s * (mult / 0.75) if h and not hp else s, cid)
                  for cid, s, h, hp in pool]
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [cid for _, cid in scored[:100]]

    t75, t85, t100 = top100(0.75), top100(0.85), top100(1.0)
    print(f"recalled: {len(pool)} | hopper-penalized: {len(hoppers)} "
          f"({100 * len(hoppers) / len(pool):.1f}% of pool)")
    print(f"top-100 overlap 0.75 vs 0.85: {len(set(t75) & set(t85))}")
    print(f"top-100 overlap 0.75 vs 1.00: {len(set(t75) & set(t100))}")
    print(f"enter at 0.85: {[c for c in t85 if c not in t75]}")
    print(f"enter at 1.00: {[c for c in t100 if c not in t75]}")
    print(f"exit  at 1.00: {[c for c in t75 if c not in t100]}")

    from collections import Counter
    print("\nhopper cohort ladder patterns:", Counter(h["ladder"] for h in hoppers))
    hi_ev = [h for h in hoppers if h["career_ev"] >= 0.8]
    print(f"hoppers with career_ev >= 0.8: {len(hi_ev)}")
    for h in sorted(hi_ev, key=lambda x: -x["score"])[:10]:
        print(f"  {h['cid']} {h['title'][:30]:30} ev={h['career_ev']} "
              f"stints={h['n_stints']} med={h['median_stint']}mo ladder={h['ladder']} score={h['score']:.4f}")
    n = len(hoppers)
    if n:
        print(f"\nhopper means: career_ev={sum(h['career_ev'] for h in hoppers)/n:.3f} "
              f"behavioral={sum(h['behavioral'] for h in hoppers)/n:.3f} "
              f"rr={sum(h['rr'] for h in hoppers)/n:.3f} "
              f"honeypot_rate={sum(h['hp'] for h in hoppers)/n:.3%}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--tag", default="")
    ap.add_argument("--merge", nargs="+", default=None)
    a = ap.parse_args()
    if a.merge:
        merge(a.merge)
    else:
        run(a.candidates, a.limit, a.skip, a.tag)


if __name__ == "__main__":
    main()
