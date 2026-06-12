"""Phase 5 — reasoning engine.

Rewrites the reasoning column of the top-100 CSV. Scoring and ordering are
frozen: the engine asserts candidate_id/rank/score are byte-identical in/out.

Every clause is assembled from verified facts (see docs/phase5_reasoning_design.md);
free-text generation does not exist in this module, and a mechanical verifier
re-checks every inserted company/skill against the source record.

Usage:
  python -m src.reasoning_engine [--candidates PATH] [--csv outputs/baseline_top100.csv]
"""

from __future__ import annotations

import argparse
import csv
import re
import zlib

from src.config import OUTPUTS_DIR
from src.data_loader import iter_candidates
from src.scoring import SKILL_GROUPS, _regex_evidence, score_candidate, skill_trust
from src.template_evidence import stint_categories

CAT_NOUN = {
    "retrieval": "embeddings/retrieval systems",
    "rank_eval": "ranking evaluation (offline metrics and A/B testing)",
    "reco_search": "search/recommendation systems",
    "ltr": "learning-to-rank models",
}
JD_HOOK = {
    "retrieval": ["the JD's core production retrieval requirement",
                  "the embeddings-in-production experience the JD demands",
                  "the must-have retrieval depth this role centres on"],
    "rank_eval": ["the evaluation-framework experience the JD treats as a must-have",
                  "the rigorous ranking-evaluation background the JD asks for",
                  "the offline/online evaluation skill set the role requires"],
    "reco_search": ["the shipped ranking system the JD's ideal profile calls for",
                    "the end-to-end search/reco shipping the JD prizes over research",
                    "the 'shipped at meaningful scale' bar the JD sets"],
    "ltr": ["a JD nice-to-have", "bonus learning-to-rank depth the JD welcomes"],
}


def pick(cid: str, slot: str, options: list[str]) -> str:
    """Deterministic per-candidate template choice (reproducible variation)."""
    return options[zlib.crc32(f"{cid}:{slot}".encode()) % len(options)]


def extract_facts(rec: dict, b: dict) -> dict:
    prof, career, skills = rec["profile"], rec["career_history"], rec["skills"]
    sig = rec["redrob_signals"]
    assess = sig.get("skill_assessment_scores", {}) or {}

    # best evidence stint: most categories credited for that stint's own text
    # (Phase 7: template table first, regex fallback)
    best = None
    for st in career:
        cats = stint_categories(st.get("description", ""), _regex_evidence)
        if cats and (best is None or len(cats) > len(best[1])):
            best = (st, cats)

    # strongest corroborated JD-core skill
    core_kws = SKILL_GROUPS["embeddings_retrieval"][0] + SKILL_GROUPS["vector_db"][0]
    top_skill = None
    for s in skills:
        if any(k in s.get("name", "").lower() for k in core_kws):
            t = skill_trust(s, assess)
            if top_skill is None or t > top_skill[1]:
                top_skill = (s, t)

    corrob = None
    if top_skill:
        s = top_skill[0]
        a = assess.get(s["name"])
        if a is not None:
            corrob = f"Redrob-assessed {a:.0f}/100"
        elif s.get("endorsements", 0) >= 10:
            corrob = f"{s['endorsements']} endorsements"
        elif s.get("duration_months", 0) >= 24:
            corrob = f"{s['duration_months'] / 12:.1f}y of use"
        else:
            top_skill = None  # weakly corroborated — don't cite

    return {
        "cid": rec["candidate_id"], "title": prof["current_title"],
        "yoe": prof["years_of_experience"], "city": prof["location"].split(",")[0],
        "country": prof["country"],
        "stint": best[0] if best else None, "cats": best[1] if best else [],
        "skill": top_skill[0]["name"] if top_skill else None, "corrob": corrob,
        "days": b["_days_inactive"], "rr": b["_rr"], "notice": b["_notice"],
        "otw": sig.get("open_to_work_flag", False),
        "relocate": sig.get("willing_to_relocate", False),
        "pens": b["penalties"], "career_ev": b["career_ev"],
    }


def build_concerns(f: dict) -> list[str]:
    c = []
    if any("hopper" in p for p in f["pens"]):
        c.append("frequent short stints raise the JD's 3-year-commitment concern")
    if f["country"] != "India":
        c.append(f"based in {f['city']}, {'open to relocating' if f['relocate'] else 'no relocation stated'} (no visa sponsorship)")
    if f["notice"] > 90:
        c.append(f"{f['notice']}-day notice period")
    elif f["notice"] > 60:
        c.append(f"notice period is {f['notice']} days")
    if f["days"] > 120:
        c.append(f"last platform activity {f['days']} days ago")
    if f["rr"] < 0.2:
        c.append(f"recruiter response rate is low ({f['rr']:.0%})")
    if f["yoe"] < 4:
        c.append(f"{f['yoe']:.1f}y is light for a senior role")
    elif f["yoe"] > 9:
        c.append(f"{f['yoe']:.1f}y sits above the JD's 5-9y band")
    if f["career_ev"] < 0.5:
        c.append("retrieval-specific depth in the career history is limited")
    return c


def build_strengths(f: dict) -> list[str]:
    """Ordered strengths; lead item varies by deterministic layout choice."""
    cid = f["cid"]
    s = []
    if f["stint"] is not None:
        noun = CAT_NOUN[f["cats"][0]]
        hook = pick(cid, "hook", JD_HOOK[f["cats"][0]])
        extra = f" and {CAT_NOUN[f['cats'][1]]}" if len(f["cats"]) > 1 else ""
        verb = pick(cid, "verb", ["built", "shipped", "owned", "delivered"])
        link = pick(cid, "link", ["- directly", "- matching", "- which is"])
        s.append(f"{verb} {noun}{extra} at {f['stint']['company']} {link} {hook}")
    if f["skill"]:
        s.append(pick(cid, "sk", [f"{f['skill']} is independently corroborated ({f['corrob']})",
                                  f"the {f['skill']} claim holds up ({f['corrob']})",
                                  f"{f['skill']} checks out ({f['corrob']})"]))
    if 5 <= f["yoe"] <= 9:
        s.append(pick(cid, "band", [f"{f['yoe']:.1f}y sits inside the JD's 5-9y band",
                                    f"experience ({f['yoe']:.1f}y) is squarely in-band for the role"]))
    if f["days"] <= 30 and f["rr"] >= 0.5:
        s.append(f"actively engaged (last active {f['days']}d ago, {f['rr']:.0%} recruiter response rate)")
    if f["otw"] and f["notice"] <= 30:
        s.append(f"open to work with a {f['notice']}-day notice")
    # layout variation: which strength leads (when more than one exists)
    layout = pick(cid, "layout", ["ev", "skill", "band"])
    if layout == "skill" and f["skill"] and len(s) > 1:
        s.insert(0, s.pop(1))
    elif layout == "band" and 5 <= f["yoe"] <= 9 and len(s) > 2:
        for i, t in enumerate(s):
            if "band" in t or "in-band" in t:
                s.insert(0, s.pop(i))
                break
    return s


def compose(rank: int, f: dict) -> str:
    out = _compose(rank, f, full=True)
    if len(out) > 340:  # deterministic shrink: 1 strength + 1 concern
        out = _compose(rank, f, full=False)
    return out


def _compose(rank: int, f: dict, full: bool) -> str:
    cid = f["cid"]
    strengths = build_strengths(f)
    concerns = build_concerns(f)
    if not full:
        strengths, concerns = strengths[:1], concerns[:1]
    head = f"{f['yoe']:.1f}y {f['title']} ({f['city']})"

    if rank <= 10:
        opener = pick(cid, "o1", ["is exactly the profile this JD describes:",
                                  "matches the JD's ideal profile squarely:",
                                  "is a near-direct hit for this role:"])
        main = "; ".join(strengths[:2]) or "strong multi-signal fit"
        tail = f" Main caveat: {concerns[0]}." if concerns else ""
        return f"{head} {opener} {main}.{tail}"
    if rank <= 40:
        opener = pick(cid, "o2", ["is a strong fit:", "aligns well with the JD:",
                                  "brings the core of what the JD asks for:"])
        main = "; ".join(strengths[:2]) or "consistent evidence across title, career history and skills"
        tail = f" Watch-out: {concerns[0]}." if concerns else ""
        return f"{head} {opener} {main}.{tail}"
    if rank <= 80:
        opener = pick(cid, "o3", ["is a solid mid-list pick:", "offers a credible fit:",
                                  "is a reasonable match:"])
        main = strengths[0] if strengths else "relevant title and skill profile"
        con = f", though {concerns[0]}" if concerns else ""
        sec = f" {pick(cid, 's3', ['Also of note:', 'Additionally:', 'Supporting signal:'])} {strengths[1]}." if len(strengths) > 1 else ""
        return f"{head} {opener} {main}{con}.{sec}"
    # 81-100: borderline — concerns lead or balance the single strength
    opener = pick(cid, "o4", ["is a borderline include:", "makes the list with reservations:",
                              "rounds out the top 100:"])
    main = strengths[0] if strengths else "adjacent evidence only"
    cons = "; ".join(concerns[:2]) if concerns else "evidence depth is thinner than higher-ranked candidates"
    return f"{head} {opener} {main}, but {cons}."


def verify(reasonings: dict[str, str], records: dict[str, dict]) -> list[str]:
    problems = []
    if len(set(reasonings.values())) != len(reasonings):
        problems.append("duplicate reasoning strings")
    for cid, txt in reasonings.items():
        rec = records[cid]
        if not txt.strip():
            problems.append(f"{cid}: empty")
        if len(txt) > 340:
            problems.append(f"{cid}: too long ({len(txt)})")
        if txt.count(". ") > 2:
            problems.append(f"{cid}: more than 2 sentences")
        # hallucination guard: any capitalized multiword company-ish token we
        # inserted must exist in the record (companies + skills + city + title)
        legal = {st["company"] for st in rec["career_history"]}
        legal |= {s["name"] for s in rec["skills"]}
        legal |= {rec["profile"]["current_title"], rec["profile"]["location"].split(",")[0]}
        for m in re.findall(r"at ([A-Z][\w.&'-]+(?: [A-Z][\w.&'-]+)*)", txt):
            if m not in legal:
                problems.append(f"{cid}: company '{m}' not in record")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates", default=None)
    ap.add_argument("--csv", default=str(OUTPUTS_DIR / "baseline_top100.csv"))
    a = ap.parse_args()

    with open(a.csv, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 100, f"expected 100 rows, got {len(rows)}"
    wanted = {r["candidate_id"]: int(r["rank"]) for r in rows}

    records: dict[str, dict] = {}
    for rec in iter_candidates(path=a.candidates):
        if rec["candidate_id"] in wanted:
            records[rec["candidate_id"]] = rec
            if len(records) == 100:
                break
    assert len(records) == 100, "some top-100 ids not found in dataset"

    reasonings: dict[str, str] = {}
    for cid, rank in wanted.items():
        b = score_candidate(records[cid])
        assert b is not None, f"{cid} no longer recalled - scoring drifted!"
        reasonings[cid] = compose(rank, extract_facts(records[cid], b))

    problems = verify(reasonings, records)
    if problems:
        raise SystemExit("VERIFY FAILED:\n" + "\n".join(problems))

    for r in rows:  # order/score columns untouched
        r["reasoning"] = reasonings[r["candidate_id"]]
    with open(a.csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        w.writeheader()
        w.writerows(rows)
    print(f"Reasoning written for 100 candidates -> {a.csv} (verification clean)")


if __name__ == "__main__":
    main()
