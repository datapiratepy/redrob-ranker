# Phase 3 — Top-100 Audit

Audit of `outputs/baseline_top100.csv` (+ `baseline_shortlist.csv` for the bubble).
No ranker changes made — findings feed Phases 4–6.

## 1. Title distribution

| Title | n | | Title | n |
|---|---|---|---|---|
| Machine Learning Engineer | 14 | | NLP Engineer | 8 |
| Applied ML Engineer | 14 | | Senior MLE / Senior NLP Eng | 4 + 4 |
| Recommendation Systems Engineer | 13 | | Lead AI / Senior AI Engineer | 3 + 3 |
| AI Engineer | 12 | | Staff MLE | 3 |
| Search Engineer | 11 | | Senior Applied Scientist | 1 |
| Senior Data Scientist | 9 | | ML Engineer | 1 |

All 100 are relevant engineering titles — zero non-tech leakage (the sample-submission failure mode is absent). Reco/Search engineers = 24, validating the Phase 2 title-extension fix.

## 2. Score distribution

max 0.951 · p25 0.780 · median 0.726 · p75 0.665 · min 0.603. One meaningful cliff: rank 3→4 (-0.047). Ranks 4–100 are a smooth gradient; **ranks 95–105 are separated by <0.016 total** — the cut line is weight-sensitive (see §10). 10 adjacent ties exist; tie-break by candidate_id ascending is enforced and validator-confirmed.

## 3. Recall-gate distribution

| Gates | n |
|---|---|
| TCS (all three) | 95 |
| TC- (title+text) | 2 |
| T-S (title+skills) | 1 |
| -CS (text+skills, no title) | 1 |
| T-- (title only) | 1 |

## 4. Career-evidence categories

reco/search-system 96 · retrieval/embeddings 88 · ranking-eval 86 · LTR 48. **Zero candidates without career evidence**; median career_ev 0.85, min 0.25. The 0.40-weight component is doing the selection, as designed.

## 5–7. Penalties & honeypots in top-100

Consulting-only: **0** · Job-hoppers: **0** · Any penalty: **0** · Honeypot flags: **0** (also zero overlap with the independent Phase 2 suspect list). At top-100 score levels, multiplicative penalties act as de-facto exclusions — sensible for ×0.30, debatable for ×0.75 (see #105 below).

## 8. Ten most surprising candidates

| # | Candidate | Surprise | What inspection shows |
|---|---|---|---|
| 28 | CAND_0093547 | "Senior MLE" claiming **2.9y** | Career history sums to **74 months (6.2y)** — YoE *understated*, the inverse of H3. Career text is elite (fine-tuned BGE → Pinecone → XGBoost LTR → behavioral-signal integration). Trap-or-noise? **Phase 4 must decide an H3-inverse policy.** |
| 70 | CAND_0086022 | title_sc = **0.15** at rank 70 | "Senior Applied Scientist" — **our title regex misses "Applied Scientist"**, a standard industry ML title. Career text is a dream fit: "RAG-based ranking pipeline serving 50M+ queries for a recruiter-facing search product", BM25+BGE+FAISS+LTR, **HR-tech domain**. Fairly titled, this is a top-10 candidate. Biggest single bug found. |
| 93 | CAND_0061257 | Single-gate (T--), career_ev 0.25 | Staff MLE @ LinkedIn. Career text: "designed the ranking layer… surface the right thing across millions of items/users" — **pure paraphrase, no keywords**. Phase 3's paraphrase-blindness failure mode, confirmed in a real profile. Phase 6's case-in-point. |
| 15 | CAND_0055905 | London, rank 15 | Non-India at loc_sc 0.25 still reaches top-15 — location weight (0.10) barely bites when fit is strong |
| 20, 33, 63, 89, 90, 95, 97 | 7 more non-India | Austin, Berlin, Toronto ×2, Dubai, Seattle, Berlin | **9 of top-100 are outside India.** JD: "case-by-case, no visa sponsorship" + ideal profile is Pune/Noida. Ground truth likely tiers these down. Decision needed: harsher non-India factor vs trust the JD's "case-by-case" |
| 80, 84 | 3.0y Search Eng / MLE | In-band-adjacent juniors carried by strong text | Acceptable at ranks 80+, watch at higher ranks |
| 91 | CAND_0094759 | behavioral 0.684 in top-100 | Fit strong enough to survive a 32% availability cut — multiplier working as intended (modifier, not gate) |
| 92, 100 | career_ev = 0.25 | Thin-evidence entrants at the tail | Same paraphrase root cause as #93 |

## 9. Single-gate entrants

Only one: **#93 CAND_0061257** (title-only gate, see above). The -CS entrant (no AI title) is the plain-language pathway working. Single-gate entry is rare (1%) — the gates strongly agree at the top.

## 10. The bubble (ranks 95–105)

| # | Candidate | Title | YoE | ev | beh | score |
|---|---|---|---|---|---|---|
| 95–100 | (in) | MLE/Applied ML/Sr DS | 4.2–6.6 | 0.25–0.75 | 0.84–0.95 | 0.618→0.603 |
| 101 | CAND_0078492 | Reco Systems Eng | 5.1 | 0.32 | 1.00 | 0.6030 |
| 102 | CAND_0079064 | Senior DS | 5.2 | 0.35 | 0.90 | 0.6030 |
| 105 | CAND_0007412 | Applied ML Eng | 7.4 | **1.00** | 0.90 | 0.5990 |

#100 vs #101 gap: **0.0002**. And #105 has *perfect* career evidence (1.00) + ideal YoE but sits outside on a job-hopper ×0.75 — the strongest evidence profile excluded by a behavioral-pattern penalty. Defensible per JD ("title-chasers"), but worth a Stage-5-ready justification and a Phase 7 sensitivity test on the 0.75 factor.

## Actionable findings (ordered by impact)

1. **Add "Applied Scientist" (and similar: "Research Engineer — Search", "Relevance Engineer") to the relevant-title regex** — concrete miscredit at rank 70; likely candidates missed entirely below the cut. → Phase 4/6 fix, then re-rank.
2. **Decide H3-inverse policy** (career history ≫ claimed YoE, e.g. 6.2y vs 2.9 at #28): trap, noise, or trust-career-math? Inspect more cases in Phase 4.
3. **Paraphrase blindness confirmed** (#93 LinkedIn Staff MLE) — Phase 6 semantic layer has a measurable target: re-rank should lift keyword-free ranking-layer profiles.
4. **Non-India policy** (9/100): consider 0.15 loc weight or harsher non-India base (0.25→0.15) given "no visa sponsorship" + the ideal-profile note; verify against hand labels in Phase 7 before changing.
5. **Penalty sensitivity at the cut**: #105 (perfect evidence, hopper) vs #100 (thin evidence, clean) is the kind of pair the hand-labeled eval set must adjudicate.
6. Bubble instability (<0.016 across 11 ranks) means **NDCG@50 is sensitive to small weight changes** — do not tune weights without the Phase 7 eval harness.
