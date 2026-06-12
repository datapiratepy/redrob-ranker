"""Phase 2 - single-pass streaming EDA scanner.

Computes, in ONE pass over candidates.jsonl (no full load into memory):
  A. population stats        (titles, YoE, location, industry, company size)
  B. AI/ML relevance Venn    (title vs skills vs career-text evidence)
  C. skill stats             (frequency, trust corroboration per JD skill)
  D. career stats            (stints, hops, consulting-only, product exposure)
  E. behavioral signal dists (response rate, recency, notice, assessments...)
  F. honeypot suspect flags  (5 consistency checks, per-record)
  G. JD-signal prevalence    (each Phase 1 must-have / negative, measured)

Outputs: outputs/eda_stats.json, outputs/honeypot_suspects.csv

Usage (single run):   python -m src.eda_scan [--limit N]
Usage (chunked, for time-boxed environments):
  python -m src.eda_scan --skip 0     --limit 34000 --tag c1
  python -m src.eda_scan --skip 34000 --limit 33000 --tag c2
  python -m src.eda_scan --skip 67000               --tag c3
  python -m src.eda_scan --merge c1 c2 c3

Keyword lists come from config/jd_signals.yaml (Phase 1 contract), so EDA
measures exactly the signals the ranker will later use.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from collections import Counter
from datetime import date, datetime
from typing import Any

import yaml

from src.config import CONFIG_DIR, OUTPUTS_DIR
from src.data_loader import iter_candidates

AI_TITLE_RE = re.compile(
    r"(machine learning|\bml\b|\bai\b|data scien|nlp|deep learning|mlops|computer vision|research (scientist|engineer))",
    re.I,
)
NONTECH_TITLE_RE = re.compile(
    r"(hr |human resource|marketing|sales|account|content writer|customer support|"
    r"operations manager|graphic designer|civil engineer|mechanical engineer|recruiter|business analyst|project manager)",
    re.I,
)
ARCHITECT_DRIFT_RE = re.compile(
    r"(architect|head of|director|vp |vice president|chief|engineering manager)", re.I
)
CORE_EVIDENCE_RE = re.compile(
    r"(recommendation|recommender|ranking|retrieval|search (system|engine|infra|quality|relevance)|"
    r"embedding|vector (search|database|db|index)|semantic search|learning.to.rank|ndcg|information retrieval|bm25|faiss|elasticsearch)",
    re.I,
)
ML_EVIDENCE_RE = re.compile(
    r"(machine learning|ml model|nlp|deep learning|llm|transformer|fine.?tun|pytorch|tensorflow|"
    r"scikit|xgboost|classification model|predictive model|mlops)",
    re.I,
)
SHIPPING_RE = re.compile(
    r"(deploy|production|shipped|launched|serving|real.time|scaled?|latency|pipeline)", re.I
)


def _load_jd_skill_keywords() -> dict[str, list[str]]:
    with open(CONFIG_DIR / "jd_signals.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    out: dict[str, list[str]] = {}
    for group in ("must_have", "nice_to_have"):
        for sig in cfg["positive_signals"][group]:
            kws = sig.get("evidence_keywords")
            if kws:
                out[sig["id"]] = [k.lower() for k in kws]
    consulting = cfg["negative_signals"]["strong_negatives"]
    firms = next(s for s in consulting if s["id"] == "consulting_firms_only")
    out["_consulting_firms"] = [c.lower() for c in firms["consulting_companies"]]
    return out


SERVICES_INDUSTRIES = {"it services", "consulting"}
PRODUCT_INDUSTRIES = {
    "software", "fintech", "e-commerce", "edtech", "saas", "gaming", "ai/ml",
    "food delivery", "healthtech", "adtech", "conversational ai", "healthtech ai",
    "ai services", "insurance tech", "transportation",
}

DATASET_TODAY = date(2026, 6, 1)


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _months_between(d1: date, d2: date) -> int:
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def _bucket(value: float, edges: list[float]) -> str:
    for e in edges:
        if value <= e:
            return f"<={e}"
    return f">{edges[-1]}"


def honeypot_flags(rec: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    skills = rec.get("skills", [])
    career = rec.get("career_history", [])
    prof = rec.get("profile", {})
    signals = rec.get("redrob_signals", {})

    # H1: "expert" proficiency with ~zero usage time
    zero_dur_experts = sum(
        1 for s in skills
        if s.get("proficiency") == "expert" and s.get("duration_months", 0) <= 1
    )
    if zero_dur_experts >= 3:
        flags.append(f"H1_expert_zero_duration({zero_dur_experts})")

    # H2: stint date math broken - duration_months vs start/end dates
    bad_stints = 0
    for st in career:
        sd = _parse_date(st.get("start_date"))
        ed = _parse_date(st.get("end_date")) or DATASET_TODAY
        if sd:
            implied = _months_between(sd, ed)
            if abs(implied - st.get("duration_months", 0)) > 9:
                bad_stints += 1
    if bad_stints:
        flags.append(f"H2_stint_date_mismatch({bad_stints})")

    # H3: claimed YoE vs career history math
    yoe = prof.get("years_of_experience", 0)
    total_career_months = sum(st.get("duration_months", 0) for st in career)
    if yoe * 12 - total_career_months > 42:
        flags.append(f"H3_yoe_exceeds_history({yoe}y_vs_{total_career_months}m)")

    # H4: keyword-stuffer shape - non-tech title, many expert/advanced skills
    if NONTECH_TITLE_RE.search(prof.get("current_title", "")):
        n_hi = sum(1 for s in skills if s.get("proficiency") in ("expert", "advanced"))
        if n_hi >= 8:
            flags.append(f"H4_nontech_title_many_adv_skills({n_hi})")

    # H5: expert claim contradicted by own assessment score
    assess = signals.get("skill_assessment_scores", {}) or {}
    contradicted = sum(
        1 for s in skills
        if s.get("proficiency") == "expert" and assess.get(s.get("name", ""), 100) < 40
    )
    if contradicted >= 2:
        flags.append(f"H5_assessment_contradiction({contradicted})")

    return flags


def run_scan(path: str | None, limit: int | None, skip: int = 0, tag: str = "") -> None:
    jd_kw = _load_jd_skill_keywords()
    consulting_firms = jd_kw.pop("_consulting_firms")

    S: dict[str, Any] = {
        "n": 0,
        "titles": Counter(), "industries": Counter(), "countries": Counter(),
        "cities": Counter(), "company_sizes": Counter(),
        "yoe_buckets": Counter(),
        "venn": Counter(),  # key TSCM: Title/Skills/CoreText/MlText membership
        "skill_freq": Counter(),
        "jd_skill_stats": {sig: {"cand": 0, "endors": 0, "dur": 0, "assessed": 0, "n_sk": 0} for sig in jd_kw},
        "stint_counts": Counter(), "stint_median_buckets": Counter(),
        "job_hoppers": 0, "consulting_only": 0, "consulting_any": 0,
        "product_any": 0, "architect_drift_ai": 0,
        "resp_rate_buckets": Counter(), "recency_buckets": Counter(),
        "open_to_work": 0, "notice_buckets": Counter(),
        "assess_count_buckets": Counter(), "github_none": 0, "offer_none": 0,
        "last_active_max": "1970-01-01",
        "hp_flag_counts": Counter(), "hp_multi": Counter(),
        "jd_career_evidence": Counter(),
    }
    suspects: list[tuple[str, str, str]] = []

    t0 = time.time()
    for rec in iter_candidates(path=path, limit=limit, skip=skip):
        S["n"] += 1
        prof = rec.get("profile", {})
        skills = rec.get("skills", [])
        career = rec.get("career_history", [])
        sig = rec.get("redrob_signals", {})

        # A. population
        title = prof.get("current_title", "?")
        S["titles"][title] += 1
        S["industries"][prof.get("current_industry", "?")] += 1
        S["countries"][prof.get("country", "?")] += 1
        S["cities"][(prof.get("location", "?").split(",")[0]).strip()] += 1
        S["company_sizes"][prof.get("current_company_size", "?")] += 1
        S["yoe_buckets"][_bucket(prof.get("years_of_experience", 0), [2, 4, 5, 7, 9, 12])] += 1

        # B. relevance venn
        career_text = " ".join(st.get("description", "") for st in career)
        full_lower = (career_text + " " + prof.get("summary", "") + " " + prof.get("headline", "")).lower()
        skill_names = " | ".join(s.get("name", "").lower() for s in skills)

        has_title = bool(AI_TITLE_RE.search(title))
        n_jd_skills = sum(
            1 for kws in (jd_kw["embeddings_retrieval_production"], jd_kw["vector_db_or_hybrid_search"])
            for k in kws if k in skill_names
        )
        has_skills = n_jd_skills >= 2
        has_core = bool(CORE_EVIDENCE_RE.search(career_text))
        has_ml = bool(ML_EVIDENCE_RE.search(career_text))
        key = "".join(["T" if has_title else "-", "S" if has_skills else "-",
                       "C" if has_core else "-", "M" if has_ml else "-"])
        S["venn"][key] += 1

        # C. skills
        for s in skills:
            S["skill_freq"][s.get("name", "?")] += 1
        assess = sig.get("skill_assessment_scores", {}) or {}
        for sid, kws in jd_kw.items():
            matched = [s for s in skills if any(k in s.get("name", "").lower() for k in kws)]
            if matched:
                st_ = S["jd_skill_stats"][sid]
                st_["cand"] += 1
                st_["n_sk"] += len(matched)
                st_["endors"] += sum(m.get("endorsements", 0) for m in matched)
                st_["dur"] += sum(m.get("duration_months", 0) for m in matched)
                st_["assessed"] += sum(1 for m in matched if m.get("name") in assess)

        # D. careers
        n_st = len(career)
        S["stint_counts"][min(n_st, 8)] += 1
        durs = sorted(st.get("duration_months", 0) for st in career)
        med = durs[len(durs) // 2] if durs else 0
        S["stint_median_buckets"][_bucket(med, [12, 20, 30, 48])] += 1
        if n_st >= 3 and med < 20:
            S["job_hoppers"] += 1
        comps = [st.get("company", "").lower() for st in career]
        inds = [st.get("industry", "").lower() for st in career]
        is_consult = [
            any(f in c for f in consulting_firms) or i in SERVICES_INDUSTRIES
            for c, i in zip(comps, inds)
        ]
        if any(is_consult):
            S["consulting_any"] += 1
            if all(is_consult):
                S["consulting_only"] += 1
        if any(i in PRODUCT_INDUSTRIES for i in inds):
            S["product_any"] += 1
        if has_title and ARCHITECT_DRIFT_RE.search(title):
            S["architect_drift_ai"] += 1

        # E. behavioral
        S["resp_rate_buckets"][_bucket(sig.get("recruiter_response_rate", 0), [0.1, 0.3, 0.5, 0.7, 0.9])] += 1
        la = _parse_date(sig.get("last_active_date"))
        if la:
            days = (DATASET_TODAY - la).days
            S["recency_buckets"][_bucket(days, [7, 30, 90, 180, 365])] += 1
            if sig["last_active_date"] > S["last_active_max"]:
                S["last_active_max"] = sig["last_active_date"]
        if sig.get("open_to_work_flag"):
            S["open_to_work"] += 1
        S["notice_buckets"][_bucket(sig.get("notice_period_days", 0), [0, 15, 30, 60, 90])] += 1
        S["assess_count_buckets"][_bucket(len(assess), [0, 2, 5, 10])] += 1
        if sig.get("github_activity_score", 0) == -1:
            S["github_none"] += 1
        if sig.get("offer_acceptance_rate", 0) == -1:
            S["offer_none"] += 1

        # F. honeypots
        flags = honeypot_flags(rec)
        for fl in flags:
            S["hp_flag_counts"][fl.split("(")[0]] += 1
        if flags:
            S["hp_multi"][min(len(flags), 4)] += 1
            suspects.append((rec["candidate_id"], ";".join(f.split("(")[0] for f in flags), ";".join(flags)))

        # G. JD alignment
        for sid, kws in jd_kw.items():
            if any(k in full_lower for k in kws):
                S["jd_career_evidence"][sid] += 1
        if SHIPPING_RE.search(career_text) and has_ml:
            S["jd_career_evidence"]["ml_plus_shipping_language"] += 1

    S["scan_seconds"] = round(time.time() - t0, 1)

    out = {
        k: (dict(v.most_common()) if isinstance(v, Counter) else v)
        for k, v in S.items()
    }
    out["skill_freq"] = dict(Counter(S["skill_freq"]).most_common(200))
    OUTPUTS_DIR.mkdir(exist_ok=True)
    sfx = f"_{tag}" if tag else ""
    with open(OUTPUTS_DIR / f"eda_stats{sfx}.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    with open(OUTPUTS_DIR / f"honeypot_suspects{sfx}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "flags", "detail"])
        w.writerows(suspects)

    print(f"Scanned {S['n']:,} records in {S['scan_seconds']}s (skip={skip})")
    print(f"Honeypot suspects: {len(suspects):,} -> outputs/honeypot_suspects{sfx}.csv")


def _merge_dicts(a: Any, b: Any) -> Any:
    """Recursively sum numeric leaves; union dicts; max for *_max strings."""
    if isinstance(a, dict) and isinstance(b, dict):
        return {k: _merge_dicts(a.get(k), b.get(k)) for k in set(a) | set(b)}
    if a is None:
        return b
    if b is None:
        return a
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + b
    if isinstance(a, str) and isinstance(b, str):
        return max(a, b)  # used for last_active_max date strings
    return b


def merge_chunks(tags: list[str]) -> None:
    merged: dict[str, Any] | None = None
    rows: list[list[str]] = []
    for tag in tags:
        with open(OUTPUTS_DIR / f"eda_stats_{tag}.json", encoding="utf-8") as f:
            chunk = json.load(f)
        merged = chunk if merged is None else _merge_dicts(merged, chunk)
        with open(OUTPUTS_DIR / f"honeypot_suspects_{tag}.csv", encoding="utf-8", newline="") as f:
            r = list(csv.reader(f))
            rows.extend(r[1:])
    assert merged is not None, "no chunks given"
    with open(OUTPUTS_DIR / "eda_stats.json", "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=1)
    with open(OUTPUTS_DIR / "honeypot_suspects.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "flags", "detail"])
        w.writerows(rows)
    print(f"Merged {len(tags)} chunks: n={merged['n']:,}, suspects={len(rows):,}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--tag", default="", help="suffix for chunked output files")
    ap.add_argument("--merge", nargs="+", default=None, help="merge chunk tags")
    a = ap.parse_args()
    if a.merge:
        merge_chunks(a.merge)
    else:
        run_scan(a.candidates, a.limit, skip=a.skip, tag=a.tag)


if __name__ == "__main__":
    main()
