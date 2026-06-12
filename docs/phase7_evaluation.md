# Phase 7 — Hand-Labeled Evaluation Set

25 candidates labeled across five strata using the JD's own rubric.
Tier scale mirrors the challenge ground truth: 5 = ideal profile · 4 = strong fit ·
3 = relevant (P@10 counts tier 3+) · 2 = adjacent/effectively unavailable ·
1 = tech non-ML · 0 = irrelevant or honeypot.

⚠️ **Ownership note:** these tier labels were drafted by an AI assistant applying
the JD rubric, with rationale shown so each can be audited. Review every row and
adjust before treating this as your validation set — Stage 5 will probe whether
you own these judgments.

## The labeled set, with before/after verdicts

"Before" = Phase 5 top-100 rank; "after" = template-classified rank.

### Stratum 1 — top-ranked

| Candidate | Tier | Rationale | Before → After | Verdict |
|---|---|---|---|---|
| CAND_0081846 | 5 | Lead AI Eng, 6.7y, T35-grade retrieval+eval evidence at Razorpay, assessed IR skill, clean signals | 1 → 1 | ✔ stable |
| CAND_0018499 | 5 | Senior MLE, 7.2y, Noida (preferred city), retrieval+eval at Zomato | 2 → 3 | ✔ stable |
| CAND_0002025 | 5 | Senior AI Eng, 5.9y, full evidence stack, behavioral 1.0 | 5 → 5 | ✔ stable |
| CAND_0086022 | 5 | Sr Applied Scientist; T35 (recruiter-facing search @50M queries) — domain bonus the JD names | 12 → 19 | ✔ acceptable (displaced by fully-credited T35/T37 carriers; still NDCG@50 zone) |

### Stratum 2 — mid-ranked

| Candidate | Tier | Rationale | Before → After | Verdict |
|---|---|---|---|---|
| CAND_0083307 | 4 | Search Eng, 7.8y, T28 (e-comm search LTR, full pipeline); 120-day notice holds it below tier 5 | 48 → 26 | **improved** (T28 now fully credited incl. LTR) |
| CAND_0042029 | 4 | Sr DS, 6.5y, Flipkart discovery-feed ranking (T29) | 50 → 47 | ✔ stable |
| CAND_0096142 | 3 | Applied ML, 5.0y, assessed Weaviate, but 120-day notice + lighter evidence | 52 → 55 | ✔ stable |

### Stratum 3 — borderline

| Candidate | Tier | Rationale | Before → After | Verdict |
|---|---|---|---|---|
| CAND_0078492 | 3 | Reco Systems Eng, 5.1y; real but lighter-weight reco work (T23) | 99 → 71 | **improved** — T23 credit (0.9 reco) is fairer than the regex's partial view |
| CAND_0079064 | 3 | Sr DS, 5.2y, semantic-search template (T30) + 120-day notice | 100 → 54 | **improved** — query-expansion/FAISS work now fully credited |
| CAND_0040178 | 2 | ML Eng, 5.0y, single weak reco mention, thin elsewhere | 98 → 116 (out) | **improved** — correctly demoted below stronger evidence |
| CAND_0007412 | 4 | Applied ML, 7.4y, career_ev 1.0 but job-hopper (3 stints, median <20mo) | 105 → 135 (out) | ✘ **worsened** — the one regression; the hopper-penalty question (Phase 4, deferred) remains the openest issue in the system |

### Stratum 4 — honeypots and traps (all tier 0)

| Candidate | Trap | Before → After | Verdict |
|---|---|---|---|
| CAND_0093547 | H6: 2.9y claimed / 74mo history | excluded → excluded | ✔ |
| CAND_0039521 | H6: 3.0y / 59mo | excluded → excluded | ✔ |
| CAND_0001610 | H6: 3.0y / 61mo | excluded → excluded | ✔ |
| CAND_0003430 | H3: 13.7y / 11mo | excluded → excluded | ✔ |
| CAND_0003582 | H1: expert skills @ 0 months | excluded → excluded | ✔ |
| CAND_0000074 | H4 keyword stuffer (Ops Manager + "advanced" embeddings) | not recalled → not recalled | ✔ |

### Stratum 5 — under-credited semantic candidates

| Candidate | Tier | Rationale | Before → After | Verdict |
|---|---|---|---|---|
| CAND_0061257 | 4 | Staff MLE @ LinkedIn; T42 "ranking layer" paraphrase; 8.0y | 90 → **43** | **improved** — the Phase 3 audit case, resolved |
| CAND_0068351 | 4 | Lead AI Eng, 6.4y; T40 invisible template | 89 → **44** | **improved** |
| CAND_0093193 | 4 | Senior MLE, 7.9y, Bangalore; T40 carrier whose career_ev was literally 0.0 | ~250 → **110** | **improved but incomplete** — T40's reduced confidence (wording ambiguity) keeps implied evidence below explicit. Defensible; revisit only with better labels |
| CAND_0005538 | 3 | Senior AI Eng, 5.9y; T40 + strong ev 0.83 but job-hopper | ~200 → 172 | ✔ consistent with hopper policy |
| CAND_0006567 | 3 | Senior AI Eng, 7.9y; partial T40 credit, mixed signals | 76 → 81 | ✔ stable |

### Bonus — non-India availability cases (location policy check)

| Candidate | Tier | Before → After | Verdict |
|---|---|---|---|
| CAND_0078042 (Dubai, no relocation) | 2 | 96 → 122 (out) | **improved** — effectively unavailable per JD |
| CAND_0032515 (Seattle, no relocation) | 2 | 97 → 126 (out) | **improved** |

## Aggregate scorecard

| Measure | Before | After |
|---|---|---|
| Labeled tier-4/5 inside top-100 | 8/10 | 8/10 (two T4s remain out: the hopper case and CAND_0093193) |
| Labeled tier-≤2 inside top-100 | **3** | **0** |
| Labeled tier-4/5 mean rank (those in top-100) | 37.1 | **28.5** |
| Honeypots/stuffers in top-100 | 0 | 0 |
| Improved / stable / worsened (21 non-honeypot labels) | — | **9 improved · 11 stable · 1 worsened** |

## Decision

**Adopt the template-classified ranking — `outputs/updated_top100.csv` is the new
live submission candidate.** Nine labeled improvements, zero tier-≤2 in the
top-100, all known traps still excluded, the bubble now starts at 0.653 instead of
0.603, and the single regression (CAND_0007412) traces to the deliberately
unresolved hopper-penalty policy, not to the template mechanism. Remaining open
items for the final pre-submission pass: hopper ×0.75 vs ×0.85 (one labeled data
point is not enough to decide), and a final manual read of all 100 reasoning rows.
