"""Phase 3 — baseline scoring components.

Interpretable, deterministic, CPU-only. No embeddings, no ML models.
Every constant is justified in docs/phase3_baseline_design.md against
Phase 2 EDA evidence (docs/phase2_eda_findings.md).

Formula:
    fit   = 0.40*career + 0.20*title + 0.20*skills + 0.10*experience + 0.10*location
    score = fit * penalties * behavioral_multiplier * honeypot_factor
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from src.template_evidence import career_evidence, lookup_stint

# --------------------------------------------------------------------------
# Regexes (recall + evidence). Career-text only for core evidence — summaries
# contain aspirations ("want to get serious about retrieval") regex can't
# distinguish from experience.
# --------------------------------------------------------------------------

# R1 recall: extended with search/reco/retrieval titles — Phase 2 showed the
# plain AI regex missed "Recommendation Systems Engineer".
RELEVANT_TITLE_RE = re.compile(
    r"(machine learning|\bml\b|\bai\b|data scien|nlp|deep learning|mlops|"
    r"recommendation|recommender|search|retrieval|information retrieval|"
    r"applied scientist)", re.I)  # Phase 4: title census showed 'Senior Applied
    # Scientist' (4 candidates) was the only relevant title the regex missed
ADJACENT_TITLE_RE = re.compile(
    r"(software engineer|backend|full stack|data engineer|platform engineer|sde)", re.I)
SENIOR_RE = re.compile(r"(senior|staff|lead|principal)", re.I)
JUNIOR_RE = re.compile(r"(junior|intern|trainee|associate)", re.I)

EVID_RETRIEVAL_RE = re.compile(
    r"(retriev|embedding|vector (search|database|db|index)|semantic search|faiss|"
    r"elasticsearch|opensearch|pinecone|weaviate|qdrant|milvus|bm25|information retrieval)", re.I)
EVID_RANK_EVAL_RE = re.compile(
    r"(ndcg|\bmrr\b|mean average precision|a/b test|ab test|offline.online|"
    r"offline metric|relevance (metric|evaluation)|ranking (metric|quality|model))", re.I)
EVID_RECO_SEARCH_RE = re.compile(
    r"(recommendation|recommender|search (system|engine|infra|quality|relevance|ranking)|"
    r"discovery feed|personali[sz]ation|learning.to.rank|lambdamart|xgboost rank)", re.I)
EVID_LTR_RE = re.compile(r"(learning.to.rank|\bltr\b|lambdamart|lambdarank)", re.I)
SHIPPING_RE = re.compile(r"(deploy|production|shipped|launched|serving|real.time|live traffic)", re.I)
CV_DOMAIN_RE = re.compile(r"(computer vision|image (classification|segmentation|detection)|"
                          r"speech recognition|robotics|object detection)", re.I)
NLP_IR_RE = re.compile(r"(nlp|text|language model|llm|retriev|search|ranking|embedding)", re.I)

# JD-core skill groups -> (keywords, group weight). Weights mirror must-have order.
SKILL_GROUPS: dict[str, tuple[list[str], float]] = {
    "embeddings_retrieval": (["embedding", "sentence transformers", "retrieval", "semantic search",
                              "vector search", "bge", "e5", "rag", "recommendation"], 0.35),
    "vector_db": (["pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch",
                   "faiss", "vespa", "lucene", "solr"], 0.25),
    "python": (["python"], 0.20),
    "ranking_eval": (["ndcg", "mrr", "a/b", "ab test", "evaluation", "experiment"], 0.20),
}
NICE_SKILLS = ["lora", "qlora", "peft", "fine-tuning", "xgboost", "learning to rank",
               "lightgbm", "pytorch", "hugging face"]

CONSULTING_FIRMS = ["tcs", "tata consultancy", "infosys", "wipro", "accenture", "cognizant",
                    "capgemini", "hcl", "tech mahindra", "mindtree", "lti", "mphasis",
                    "deloitte", "ibm global services"]
SERVICES_INDUSTRIES = {"it services", "consulting"}
PREFERRED_CITIES = ("pune", "noida")
WELCOME_CITIES = ("hyderabad", "mumbai", "delhi", "gurgaon", "gurugram", "ghaziabad",
                  "bangalore", "bengaluru")

DATASET_TODAY = date(2026, 6, 1)


def _regex_evidence(text: str) -> tuple[dict[str, float], bool]:
    """Phase 3 regex evidence, as fallback for stint texts not in the
    44-template table (config/template_evidence.yaml)."""
    conf: dict[str, float] = {}
    if EVID_RETRIEVAL_RE.search(text):
        conf["retrieval"] = 1.0
    if EVID_RANK_EVAL_RE.search(text):
        conf["rank_eval"] = 1.0
    if EVID_RECO_SEARCH_RE.search(text):
        conf["reco_search"] = 1.0
    if EVID_LTR_RE.search(text):
        conf["ltr"] = 1.0
    return conf, bool(SHIPPING_RE.search(text))


def _pd(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _months(d1: date, d2: date) -> int:
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def skill_trust(s: dict[str, Any], assess: dict[str, float]) -> float:
    """Trust in a skill claim: corroboration, not presence (Phase 2 finding C)."""
    t = 0.5 * min(s.get("endorsements", 0), 20) / 20 + 0.5 * min(s.get("duration_months", 0), 36) / 36
    a = assess.get(s.get("name", ""))
    if a is not None:
        if a >= 60:
            t = max(t, 0.9)
        elif a < 40:
            t *= 0.3
    return min(t, 1.0)


def honeypot_check(rec: dict[str, Any]) -> list[str]:
    """H1-H3 consistency checks, thresholds tuned toward the spec's ~80 target."""
    flags = []
    prof, career, skills = rec["profile"], rec["career_history"], rec["skills"]
    if sum(1 for s in skills if s.get("proficiency") == "expert"
           and s.get("duration_months", 0) <= 1) >= 2:
        flags.append("H1_expert_zero_duration")
    for st in career:
        sd = _pd(st.get("start_date"))
        ed = _pd(st.get("end_date")) or DATASET_TODAY
        if sd and abs(_months(sd, ed) - st.get("duration_months", 0)) > 6:
            flags.append("H2_stint_date_mismatch")
            break
    total_m = sum(st.get("duration_months", 0) for st in career)
    if prof.get("years_of_experience", 0) * 12 - total_m > 30:
        flags.append("H3_yoe_exceeds_history")
    # Phase 4 (H6): the inverse direction. 99,976/100,000 profiles have
    # |history - yoe| <= 6 months; the 24 sequential-stint outliers beyond that
    # are planted inconsistencies (verified by inspection — e.g. 2.9y claimed
    # over 74 months of employment). Threshold >12 for safety margin.
    if total_m - prof.get("years_of_experience", 0) * 12 > 12:
        flags.append("H6_history_exceeds_yoe")
    return flags


def score_candidate(rec: dict[str, Any]) -> dict[str, Any] | None:
    """Gate (recall) + score. Returns None if candidate is not recalled."""
    prof = rec["profile"]
    skills = rec["skills"]
    career = rec["career_history"]
    sig = rec["redrob_signals"]
    assess = sig.get("skill_assessment_scores", {}) or {}

    title = prof.get("current_title", "")
    career_text = " ".join(st.get("description", "") for st in career)
    skill_lower = [s.get("name", "").lower() for s in skills]

    # ---------------- recall gates (union) ----------------
    r1 = bool(RELEVANT_TITLE_RE.search(title))
    r2 = bool(EVID_RETRIEVAL_RE.search(career_text) or EVID_RECO_SEARCH_RE.search(career_text))
    corroborated_core = [
        s for s in skills
        if any(k in s.get("name", "").lower()
               for k in SKILL_GROUPS["embeddings_retrieval"][0] + SKILL_GROUPS["vector_db"][0])
        and (s.get("endorsements", 0) >= 5 or s.get("duration_months", 0) >= 18
             or s.get("name") in assess)
    ]
    r3 = len(corroborated_core) >= 2
    if not (r1 or r2 or r3):
        # Phase 7: template-aware recall — catches paraphrase-only profiles
        # (none exist in this dataset per Phase 6, but keeps the gate honest)
        if not any((e := lookup_stint(st.get("description", ""))) and e.get("categories")
                   for st in career):
            return None
        r2 = True

    # ---------------- A. career evidence (0.40) ----------------
    # Phase 7: exact md5 lookup against the human-labeled 44-template table
    # (config/template_evidence.yaml); Phase 3 regexes only for unknown texts.
    career_ev, cats, shipped, _unknown = career_evidence(career, _regex_evidence)

    # ---------------- B. title & seniority (0.20) ----------------
    if r1:
        title_sc = 1.0 if SENIOR_RE.search(title) else 0.85
    elif ADJACENT_TITLE_RE.search(title):
        title_sc = 0.5
    else:
        title_sc = 0.15
    if JUNIOR_RE.search(title):
        title_sc *= 0.5

    # ---------------- C. corroborated skills (0.20) ----------------
    skills_sc = 0.0
    for gname, (kws, w) in SKILL_GROUPS.items():
        matched = [s for s in skills if any(k in s.get("name", "").lower() for k in kws)]
        if matched:
            skills_sc += w * max(skill_trust(s, assess) for s in matched)
    nice = sum(1 for s in skill_lower if any(k in s for k in NICE_SKILLS))
    skills_sc = min(skills_sc + min(nice, 2) * 0.05, 1.0)

    # ---------------- D. experience fit (0.10) ----------------
    yoe = prof.get("years_of_experience", 0)
    if 6 <= yoe <= 8:
        exp_sc = 1.0
    elif 5 <= yoe <= 9:
        exp_sc = 0.9
    elif 4 <= yoe < 5 or 9 < yoe <= 12:
        exp_sc = 0.7
    elif 3 <= yoe < 4:
        exp_sc = 0.5
    elif yoe > 12:
        exp_sc = 0.5
    else:
        exp_sc = 0.2

    # ---------------- E. location (0.10) ----------------
    loc = prof.get("location", "").lower()
    if prof.get("country", "") == "India":
        if any(c in loc for c in PREFERRED_CITIES):
            loc_sc = 1.0
        elif any(c in loc for c in WELCOME_CITIES):
            loc_sc = 0.85
        else:
            loc_sc = 0.65 + (0.1 if sig.get("willing_to_relocate") else 0.0)
    else:
        # Phase 4: of 9 non-India candidates in the Phase 3 top-100, 6 were
        # unwilling to relocate or remote-only — effectively unavailable for a
        # hybrid Pune/Noida role with no visa sponsorship. Split hard on
        # willing_to_relocate; JD keeps them "case-by-case", so never 0.
        loc_sc = 0.35 if sig.get("willing_to_relocate") else 0.10

    fit = 0.40 * career_ev + 0.20 * title_sc + 0.20 * skills_sc + 0.10 * exp_sc + 0.10 * loc_sc

    # ---------------- penalties ----------------
    pen = 1.0
    pens = []
    is_consult = [any(f in st.get("company", "").lower() for f in CONSULTING_FIRMS)
                  or st.get("industry", "").lower() in SERVICES_INDUSTRIES for st in career]
    if career and all(is_consult):
        pen *= 0.30; pens.append("consulting-only x0.30")
    durs = sorted(st.get("duration_months", 0) for st in career)
    # Phase 8: x0.75 -> x0.85. Rationale is the JD's "plans to be here 3+ years"
    # retention concern, NOT the title-chaser rule — ladder analysis showed only
    # 2/536 penalized candidates actually climb titles across short stints.
    if len(career) >= 3 and durs[len(durs) // 2] < 20:
        pen *= 0.85; pens.append("job-hopper x0.85")
    if CV_DOMAIN_RE.search(career_text) and not NLP_IR_RE.search(career_text):
        pen *= 0.50; pens.append("cv/speech-only x0.50")
    core_durs = [s.get("duration_months", 0) for s in skills if any(
        k in s.get("name", "").lower() for k in SKILL_GROUPS["embeddings_retrieval"][0])]
    if core_durs and max(core_durs) < 12:
        pen *= 0.85; pens.append("ai-skills-all-recent x0.85")

    # ---------------- behavioral multiplier (floor 0.55) ----------------
    beh = 1.0
    la = _pd(sig.get("last_active_date"))
    days = (DATASET_TODAY - la).days if la else 999
    beh *= 1.0 if days <= 90 else (0.9 if days <= 180 else 0.7)
    rr = sig.get("recruiter_response_rate", 0)
    beh *= 1.0 if rr >= 0.5 else (0.9 if rr >= 0.2 else (0.8 if rr >= 0.05 else 0.6))
    beh *= 1.0 if sig.get("open_to_work_flag") else 0.95
    nt = sig.get("notice_period_days", 0)
    beh *= 1.0 if nt <= 30 else (0.95 if nt <= 60 else 0.9)
    beh *= 1.0 if sig.get("interview_completion_rate", 1.0) >= 0.8 else 0.93
    beh = max(beh, 0.55)

    flags = honeypot_check(rec)
    hp_factor = 0.05 if flags else 1.0

    return {
        "candidate_id": rec["candidate_id"],
        "score": round(fit * pen * beh * hp_factor, 6),
        "fit": round(fit, 4),
        "career_ev": round(career_ev, 3), "career_cats": cats, "shipped": shipped,
        "title_sc": title_sc, "skills_sc": round(skills_sc, 3),
        "exp_sc": exp_sc, "loc_sc": loc_sc,
        "penalties": pens, "behavioral": round(beh, 3),
        "honeypot_flags": flags,
        "recall": "".join(["T" if r1 else "-", "C" if r2 else "-", "S" if r3 else "-"]),
        "_title": prof.get("current_title", ""), "_yoe": yoe,
        "_loc": prof.get("location", ""), "_notice": nt, "_days_inactive": days, "_rr": rr,
    }
