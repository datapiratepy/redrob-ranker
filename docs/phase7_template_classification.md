# Phase 7 — Template Classification & Integration

## What was built

Phase 6 proved all 300,171 stint descriptions collapse to **44 unique templates**.
Phase 7 enumerates them (`outputs/templates_44.json`), classifies each
(`config/template_evidence.yaml`), and scores career evidence by **exact md5
lookup** with the Phase 3 regexes retained as fallback for unknown texts
(`src/template_evidence.py`, hooked into `src/scoring.py`). No embeddings, no
models — a 44-row table is the simplest mechanism the evidence supports.

## Classification summary (full labels + rationale in the YAML)

| Group | Templates | Treatment |
|---|---|---|
| Non-tech roles (sales, support, marketing, BA, design, mech, accounting, SEO, ops) | T01–T09 | No evidence categories |
| Generic engineering (devops, mobile, frontend, java, fullstack, QA, data-infra, backend) | T10–T19, T21 | No evidence categories |
| **T20 marketing-analytics DS (1,807 carriers)** | T20 | **rank_eval 0.3** — generic A/B experimentation, *not* ranking evaluation. The baseline regex gave this full credit (false positive); the table revokes it |
| ML-adjacent (fraud serving, CV, forecasting, churn, NLP classification, MLOps) | T22, T24–T27, T33 | No core categories (CV additionally hits the wrong-specialization penalty) |
| Reco/ranking, keyword-explicit | T23, T28–T39 | Categories at 0.5–1.0 confidence; e.g. T35 (RAG ranking @50M queries, NDCG/MRR) and T37 (BGE→Pinecone→XGBoost-LTR) carry all four categories at ~1.0 |
| **Paraphrase templates (invisible or partial to regex)** | T40, T42, T43, T44 | Categories at 0.3–0.9 confidence — real relevance work, confidence reduced for wording ambiguity. T40 ("systems that understand what users are looking for") was invisible to every regex |

Confidence values are deliberate: keyword-explicit shipped systems ≈ 1.0;
paraphrase ≈ 0.4–0.9 so that explicit evidence still outranks implied evidence
at equal everything-else.

## Scoring integration

Per stint: md5 → table entry → per-category confidence; per candidate:
max confidence per category across stints; `career_ev = Σ weight·conf` (same
weights as Phase 3: retrieval .35, eval .25, reco .25, LTR .15); the ×0.8
unshipped dampener now uses the template's `shipped` flag. Recall gains a
fourth gate (any stint with a category-bearing template), and the Phase 5
reasoning engine reads per-stint categories from the same table — reasoning
stays consistent with scoring.

## Before → after (Phase 5 top-100 vs template top-100)

| Metric | Before | After |
|---|---|---|
| Recalled pool | 3,968 | 5,138 (template gate) |
| Top-100 overlap | — | **88/100** |
| Honeypots in top-100 | 0 | 0 |
| Validator | PASS | PASS |
| Runtime (full 100K) | ~43s | ~42s (md5 lookup is cheaper than 4 regexes) |
| Cut-line score | 0.603 | 0.653 |

**Movements that prove the mechanism (all four named Phase 3/6 cases):**

| Candidate | Case | Before | After |
|---|---|---|---|
| CAND_0061257 | "ranking layer" paraphrase (T42) — audit case #93 | 90 | **43** |
| CAND_0068351 | T40 invisible-template carrier | 89 | **44** |
| CAND_0093193 | T40 carrier, career_ev was 0.0 | ~250 | **110** (ev 0→0.49; reduced confidence keeps implied evidence below explicit — by design) |
| CAND_0020708 | "query expansion" (T30, probe-predicted crosser) | 116 | **36** |

**Out (12):** thin-evidence and unavailable-non-India bubble members (Dubai/Seattle
no-relocate pairs, career_ev ≤0.25 entrants at ranks 95–100).
**In (12):** probe-predicted T30/T29 carriers and properly credited mid-pool
candidates. The top 5 are unchanged except #2↔#3 swapping.

## Honest limitations

1. Template hashing exploits a synthetic-data property; in production, free text
   requires the embedding layer this project deliberately rejected (Phase 6 has the
   evidence trail for that decision).
2. Confidence values are judgment calls validated only against the 25-candidate
   labeled set (`docs/phase7_evaluation.md`) — not against held-out ground truth,
   which doesn't exist on our side of the leaderboard.
3. The labels were drafted by an AI assistant and **must be reviewed candidate-by-
   candidate by the team before submission** — Stage 5 requires owning every number
   in this table.
