# Phase 4 — High-Confidence Improvements

Scope: only findings from `docs/phase3_top100_audit.md`. No embeddings, no semantic
search, no LLM scoring. Three changes shipped, one analyzed-and-deferred.
Artifacts: `outputs/top100_phase3.csv` (before) vs `outputs/baseline_top100.csv` (after).

## Investigations (evidence before code)

### 1. Title census (full 47-title enumeration)
The dataset has only 47 distinct titles, so the gap analysis is exhaustive, not
sampled. Result: **"Senior Applied Scientist" (4 candidates) was the ONLY relevant
title the regex missed.** "Relevance Engineer" doesn't exist in this dataset;
"Senior Software Engineer (ML)" already matches via `\bml\b`; "Computer Vision
Engineer" is correctly excluded (JD don't-want). Fix: one regex alternative.

### 2. H3-inverse (career history ≫ claimed YoE)
Distribution of `sum(stint_months) − yoe×12` over all 100K:

| Gap | Candidates |
|---|---|
| ≤ 6 months | **99,976** |
| 7–30 months | 2 |
| 31–42 months | 1 |
| > 42 months | 21 |

The generator is exact to ±6 months for 99.98% of profiles. The 24 outliers have
sequential (zero overlapping) stints — i.e., the discrepancy cannot be explained by
parallel jobs. Verdict: **planted inconsistency — a honeypot class we were missing.**
Combined estimate: 65 (H1–H3) + ~24 (H6) ≈ the spec's "~80 honeypots".
Fix: new check **H6** (`history − yoe×12 > 12mo` → honeypot).

### 3. Location policy
Of the 9 non-India candidates in the Phase 3 top-100, **6 were unwilling to relocate
or remote-preference** (e.g., London: remote + won't relocate) — effectively
unavailable for hybrid Pune/Noida with no visa sponsorship.
Fix: non-India `loc_sc` split hard on `willing_to_relocate`: 0.35 / 0.10 (was flat
0.25 + 0.1). Never zero — JD says "case-by-case".

### 4. Penalty sensitivity (ranks 90–110) — ANALYZED, NOT CHANGED
Counterfactual hopper penalty ×0.75 → ×0.85 on the new shortlist: 8 hopper-penalized
candidates in the top-150; the change would lift CAND_0007412 (career_ev = 1.00) to
~rank 72 and pull 2–3 more toward the cut. Both readings are defensible from the JD
("title-chasers" vs "strongest evidence profile"). **Deferred to Phase 7** — this is
precisely what the hand-labeled eval set must adjudicate; changing it now would be
tuning blind.

## Before → after comparison

| Metric | Phase 3 | Phase 4 |
|---|---|---|
| Top-100 overlap | — | **97/100** |
| Honeypots in top-100 | **3 (undetected)** | **0** |
| Validator | PASS | PASS |
| Runtime (full 100K) | ~48s | ~43s |

**Left the top-100 (all three are H6 honeypots — formerly ranks 28, 80, 84):**

| Candidate | Old rank | Claimed | Actual history | New score |
|---|---|---|---|---|
| CAND_0093547 | 28 | 2.9y | 74 months (6.2y) | ×0.05 → excluded |
| CAND_0039521 | 80 | 3.0y | 59 months (4.9y) | ×0.05 → excluded |
| CAND_0001610 | 84 | 3.0y | 61 months (5.1y) | ×0.05 → excluded |

Notably, the Phase 3 audit's surprise scan had flagged **all three** as anomalous
("senior title/strong text at <3.1y") before we knew why. The Phase 3 top-100
contained a 3% honeypot rate — under the 10% DQ threshold but pure NDCG poison
(honeypots are forced tier-0).

**Entered:** CAND_0037980 (#78), CAND_0078492 (#99), CAND_0079064 (#100) — the
previous bubble candidates #101–102, as the audit predicted.

**Key movements:**

| Candidate | Old → New | Driver |
|---|---|---|
| CAND_0086022 (Senior Applied Scientist; RAG ranking @ 50M queries, recruiter-search domain) | **70 → 12** | Title fix: title_sc 0.15 → 1.0 |
| CAND_0055905 (London, remote, won't relocate) | 15 → 16 | Location split — honest result: at 0.10 weight, location barely moves ranks |
| CAND_0078042 (Dubai, won't relocate) | 90 → 96 | Same |

## Ranked impact of each change

1. **H6 honeypot check — critical.** Removed 3 planted profiles from our own
   submission top-100; directly reduces Stage 3 DQ exposure and removes guaranteed
   tier-0 rows from NDCG@50. Also closes the gap to the spec's ~80 honeypot count.
2. **Applied-Scientist title fix — high.** A JD-perfect candidate (recruiter-facing
   search, RAG ranking at scale) moved 70 → 12, inside the NDCG@10-relevant zone at
   weight 0.50. Exhaustive census says no other title gaps exist.
3. **Non-India relocate split — modest.** Direction is right but the 0.10 location
   weight caps its effect (London moved one rank). A larger non-India decision needs
   Phase 7 labels; documented as open.
4. **Hopper penalty — no change, analysis documented.** High-leverage but two-sided;
   blind tuning rejected.

## Still open (unchanged, by design)

- Paraphrase blindness (#93 LinkedIn Staff MLE, career_ev 0.25) — Phase 6 target.
- Location weight itself (0.10) — Phase 7 sensitivity test.
- Hopper ×0.75 vs ×0.85 — Phase 7 adjudication via hand labels.
