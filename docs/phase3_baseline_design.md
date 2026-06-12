# Phase 3 — Baseline Ranker Design

Implementation: `src/scoring.py` (components) + `src/baseline_ranker.py` (CLI).
Every constant below cites `docs/phase2_eda_findings.md`. No embeddings, no ML
models, no network — pure interpretable feature scoring.

## Recall: union of three gates (any passes → scored; else score 0)

| Gate | Rule | Phase 2 evidence |
|---|---|---|
| R1 Title | AI/ML/DS/NLP/MLOps **+ search/reco/retrieval/IR** title regex | Plain AI regex missed "Recommendation Systems Engineer"; 1,126 AI-titled |
| R2 Career text | Core retrieval/ranking/search language in `career_history` descriptions only (NOT summary — summaries contain aspirations) | 503-candidate cohort; 52 Tier-5s enter only here |
| R3 Skills | ≥2 JD-core skills each corroborated (endorsements ≥5 OR duration ≥18mo OR assessed) | 8,672 uncorroborated skill-only profiles are the stuffer surface; corroboration keeps the gate honest |

Measured recall: 3,968 of 100,000 (4.0%).

## Scoring: fit = 0.40·career + 0.20·title + 0.20·skills + 0.10·exp + 0.10·loc

| Component | Construction | Evidence anchor |
|---|---|---|
| Career evidence (0.40) | Category hits in career text: retrieval/embeddings 0.35, ranking-eval 0.25, reco/search-system 0.25, LTR 0.15; ×0.8 if no shipping language; cap 1.0 | Hardest to fake; scarce (852/1,766/1,969 profiles); maps to JD must-haves 1, 2, 4 |
| Title (0.20) | Senior+relevant 1.0; relevant 0.85; adjacent eng 0.5; other 0.15; junior ×0.5 | T∩C=451 defensible core; title confirms, never selects |
| Skills (0.20) | Per group (embeddings .35 / vector-db .25 / python .20 / eval .20): max skill_trust, where trust = ½·endorse/20 + ½·duration/36; assessment ≥60 lifts to 0.9, <40 crushes ×0.3; nice-to-haves ≤ +0.10 | JD-core skills have the worst corroboration in the pool (6.5 endors, 6% assessed) — presence is worthless |
| Experience (0.10) | 1.0 at 6–8y, 0.9 at 5–9, 0.7 at 4–5/9–12, 0.5 >12 or 3–4, 0.2 <3; never 0 | 34K in band — confirms only; JD says band is soft |
| Location (0.10) | Pune/Noida 1.0; JD-named cities 0.85; other India 0.65 (+0.1 relocate); non-India 0.25 | Cities uniform ~4.2K each; JD: no visa sponsorship |

## Penalties (multiplicative)

| Penalty | Factor | JD rule / EDA count |
|---|---|---|
| Consulting/services-only career | ×0.30 | Strong negative; 9,745 profiles |
| Job-hopper (≥3 stints, median <20mo) | ×0.75 | Title-chaser rule; 7,148 |
| CV/speech/robotics text without NLP/IR | ×0.50 | Explicit don't-want |
| All matched core skills <12mo | ×0.85 | Weak proxy for LangChain-only disqualifier (known gap) |

## Behavioral multiplier (floor 0.55 — modifier, never the fit itself)

recency ≤90d 1.0 / ≤180d 0.9 / >180d 0.7 (JD 6-month anchor; splits pool 80/20) ·
response_rate ≥.5 1.0 → <.05 0.6 (JD 5% anchor) · open_to_work 1.0/0.95 ·
notice ≤30d 1.0 / ≤60 0.95 / >60 0.9 (only 13.8% ≤30) · interview_completion ≥.8 1.0 / 0.93.
Sentinels (-1 github/offer) ignored — they are 60–65% of the pool.

## Honeypots

H1 (≥2 expert skills ≤1mo) ∪ H2 (stint dates contradict duration by >6mo) ∪
H3 (claimed YoE exceeds career sum by >2.5y) → score ×0.05. Phase 2 verified
65 planted profiles vs spec's ~80; 5 have AI titles, so checks run on all
recalled candidates. Result: 0 flagged candidates in top-100.

## Final formula

```
score = fit × penalties × behavioral × honeypot
sort by (-score, candidate_id)        # validator tie-break built in
```

Weights follow **fakeability**: career text (2× title) > title = corroborated
skills > experience = location (uniform distributions, non-selective).

## Measured results (full 100K run)

- Runtime ~48s single pass, CPU-only, stdlib+pyyaml only → 6× inside the 5-min budget.
- Recalled 3,968; top-100 score range 0.951 → 0.603.
- Top-100 composition: all relevant titles (14 MLE, 14 Applied ML, 13 Recommendation Systems, 11 Search Eng...); 95/100 pass all three gates.
- **0 honeypots in top-100** (cross-checked vs Phase 2 independent flag list).
- `validate_submission.py`: PASS.

## Example breakdowns

| Candidate | Outcome | Why |
|---|---|---|
| CAND_0002025 (Senior AI Eng, 5.9y) | 0.875 | retrieval+eval+reco evidence, shipped, clean signals |
| CAND_0000031 (Reco Systems Eng, 6.0y — "plain-language Tier 5") | 0.494 | Recalled via extended title+text; held back honestly: job-hopper ×0.75, behavioral 0.883 |
| CAND_0000074 (Ops Manager stuffer, "advanced Embeddings") | NOT RECALLED | All skill claims uncorroborated → fails R3; no title/text evidence |
| CAND_0003582 (honeypot, expert skills @ 0 months) | NOT RECALLED | No relevant evidence; would be ×0.05 anyway |

## Known weaknesses (carried to Phases 4–7)

1. Paraphrase blindness — evidence without keywords is invisible (Phase 6 semantic layer).
2. Weights are reasoned, not validated — needs hand-labeled local NDCG (Phase 7).
3. Honeypot thresholds catch 65 of ~80 — Phase 4 tunes and adds checks.
4. Behavioral twins not deduped.
5. Adjacent-title false positives possible when career text is thin.
6. Reasoning column is a factual placeholder — Phase 5 builds the real engine.
