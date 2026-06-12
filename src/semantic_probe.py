"""Phase 6 — semantic-miss investigation probe. READ-ONLY: the ranker is frozen.

Question: how many candidates describe retrieval/ranking/search/reco work in
career text WITHOUT the exact keywords the baseline credits, and what would
happen if such paraphrases were credited (at 0.7 confidence)?

Method: a paraphrase lexicon (L1-L4) deliberately disjoint from the baseline's
EVID_* regexes. For every candidate we record paraphrase hits per category the
baseline did NOT credit, then compute a counterfactual score:
    fit'   = fit + 0.40 * 0.7 * (weights of newly credited categories)
    score' = score * fit'/fit          (multipliers unchanged)
Cohort A = recalled by baseline (counterfactual is exact).
Cohort B = not recalled at all (score estimated conservatively; skills term
dropped, behavioral multiplier approximated at 0.85 — flagged as estimate).

Usage:  python -m src.semantic_probe --skip N --limit M --tag cX
        python -m src.semantic_probe --merge c1 c2 c3
"""

from __future__ import annotations

import argparse
import csv
import json
import re

from src.config import OUTPUTS_DIR
from src.data_loader import iter_candidates
from src.scoring import (ADJACENT_TITLE_RE, JUNIOR_RE, RELEVANT_TITLE_RE,
                         SENIOR_RE, score_candidate)

# Paraphrase lexicon — phrases implying the JD's core domains, none of which
# are matched by the baseline EVID_* regexes.
LEX = {
    "L1_ranking_infra": (re.compile(
        r"(ranking (layer|pipeline|service|logic|stack|function|infrastructure)|"
        r"\bre-?rank|rank(ed|ing) (results|items|candidates|documents)|"
        r"ordering of (results|items|content))", re.I), "reco/search-system", 0.25),
    "L2_reco_paraphrase": (re.compile(
        r"(collaborative filtering|content-based filtering|two-tower|user-item|"
        r"item similarity|cold.start|suggest\w* (items|products|content|jobs|candidates)|"
        r"personali[sz]ed (feed|results|recommendations|content|suggestions)|"
        r"discovery (surface|page|experience|feed))", re.I), "reco/search-system", 0.25),
    "L3_search_paraphrase": (re.compile(
        r"(query (understanding|expansion|rewriting|parsing)|autocomplete|typeahead|"
        r"search results|result relevance|relevance (tuning|scoring|signals|engineering)|"
        r"candidate generation|recall stage|surfac\w+ (the right|relevant))", re.I),
        "reco/search-system", 0.25),
    "L4_ir_infra": (re.compile(
        r"(inverted index|tf-?idf|document scoring|matching (engine|algorithm)|"
        r"match score|nearest.neighbou?r|\bhnsw\b|\bann\b index)", re.I),
        "retrieval/embeddings", 0.35),
}


def probe_one(rec: dict) -> dict | None:
    career_text = " ".join(st.get("description", "") for st in rec["career_history"])
    hits = {}
    for name, (rx, cat, w) in LEX.items():
        m = rx.search(career_text)
        if m:
            hits[name] = (m.group(0)[:40], cat, w)
    b = score_candidate(rec)

    if b is None and not hits:
        return None
    prof = rec["profile"]
    row = {"cid": rec["candidate_id"], "title": prof["current_title"],
           "yoe": prof["years_of_experience"], "country": prof["country"],
           "hits": {k: v[0] for k, v in hits.items()}}

    if b is not None:
        row["cohort"] = "A"
        row["score"] = b["score"]
        new_cats = {(cat, w) for _, (frag, cat, w) in
                    ((k, v) for k, v in hits.items()) if cat not in b["career_cats"]}
        delta_ev = 0.7 * sum(w for _, w in new_cats)
        delta_ev = min(delta_ev, 1.0 - b["career_ev"])
        if b["fit"] > 0 and delta_ev > 0:
            fit_new = b["fit"] + 0.40 * delta_ev
            row["score_new"] = round(b["score"] * fit_new / b["fit"], 6)
        else:
            row["score_new"] = b["score"]
        return row if (hits or b) else None

    # Cohort B — not recalled; conservative estimate (no skills credit, beh≈0.85)
    if not hits:
        return None
    row["cohort"] = "B"
    title = prof["current_title"]
    if RELEVANT_TITLE_RE.search(title):
        t = 1.0 if SENIOR_RE.search(title) else 0.85
    elif ADJACENT_TITLE_RE.search(title):
        t = 0.5
    else:
        t = 0.15
    if JUNIOR_RE.search(title):
        t *= 0.5
    yoe = prof["years_of_experience"]
    exp = 1.0 if 6 <= yoe <= 8 else (0.9 if 5 <= yoe <= 9 else 0.6)
    loc = 0.8 if prof["country"] == "India" else 0.2
    ev = 0.7 * sum(w for _, (_, _, w) in hits.items())
    row["score"] = 0.0
    row["score_new"] = round((0.40 * min(ev, 1.0) + 0.20 * t + 0.10 * exp + 0.10 * loc) * 0.85, 6)
    row["est"] = True
    return row


def run(path: str | None, limit: int | None, skip: int, tag: str) -> None:
    rows, all_scores = [], []
    for rec in iter_candidates(path=path, limit=limit, skip=skip):
        r = probe_one(rec)
        if r is not None:
            if r["cohort"] == "A":
                all_scores.append(r["score"])
            if r["hits"]:
                rows.append(r)
    sfx = f"_{tag}" if tag else ""
    with open(OUTPUTS_DIR / f"semantic_probe{sfx}.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    with open(OUTPUTS_DIR / f"semantic_scores{sfx}.json", "w", encoding="utf-8") as f:
        json.dump(all_scores, f)
    print(f"probed: {len(rows)} lexicon-hit rows, {len(all_scores)} recalled scores (skip={skip})")


def merge(tags: list[str]) -> None:
    rows, scores = [], []
    for t in tags:
        with open(OUTPUTS_DIR / f"semantic_probe_{t}.jsonl", encoding="utf-8") as f:
            rows += [json.loads(l) for l in f]
        with open(OUTPUTS_DIR / f"semantic_scores_{t}.json", encoding="utf-8") as f:
            scores += json.load(f)
    scores.sort(reverse=True)
    cut500 = scores[499] if len(scores) >= 500 else 0
    cut100 = scores[99]
    with open(OUTPUTS_DIR / "semantic_probe.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    a = [r for r in rows if r["cohort"] == "A"]
    bb = [r for r in rows if r["cohort"] == "B"]
    boosted = [r for r in a if r.get("score_new", r["score"]) > r["score"]]
    cross100 = [r for r in boosted if r["score"] <= cut100 < r["score_new"]]
    cross500 = [r for r in boosted if r["score"] <= cut500 < r["score_new"]]
    b_500 = [r for r in bb if r["score_new"] > cut500]
    b_100 = [r for r in bb if r["score_new"] > cut100]
    print(f"recalled pool: {len(scores)} | cut100={cut100:.4f} cut500={cut500:.4f}")
    print(f"Cohort A lexicon-hit: {len(a)} | boosted: {len(boosted)} | "
          f"would cross top-100: {len(cross100)} | cross top-500: {len(cross500)}")
    print(f"Cohort B (not recalled, paraphrase-only): {len(bb)} | est above cut500: "
          f"{len(b_500)} | est above cut100: {len(b_100)}")


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
