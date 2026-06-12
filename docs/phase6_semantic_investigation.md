# Phase 6 — Semantic Recall Investigation

Ranker frozen throughout; all numbers from the read-only probe `src/semantic_probe.py`
(full 100K scan, chunked; artifacts in `outputs/semantic_probe*.jsonl`).

## Method

A paraphrase lexicon (L1–L4: ranking-infra, reco-paraphrase, search-paraphrase,
IR-infra — 30+ phrase families, deliberately disjoint from the baseline's EVID_*
regexes) was scanned over every candidate's career text. For each hit on a category
the baseline did NOT credit, a counterfactual score was computed: paraphrase evidence
credited at 0.7 confidence, all other components and multipliers unchanged.

## Quantification

| Question | Answer |
|---|---|
| Candidates with paraphrase evidence, total | 495 (all already recalled) |
| **Candidates with paraphrase evidence NOT recalled by the baseline (Cohort B)** | **0** |
| Recalled candidates whose score would rise | 17 |
| Would newly enter the top-100 | 6 |
| Would newly enter the top-500 from below | 0 |
| Honeypots rescued by the boost | 0 (×0.05 dominates — correct) |

The headline: **semantic matching adds zero recall.** Every candidate who describes
retrieval/ranking/search work in any wording is already in the scored pool via the
title/skills/keyword union. The entire semantic question is about *crediting depth*
for ~17 already-recalled candidates.

## The decisive discovery: career text is 44 templates

While verifying the boosted candidates, their career descriptions turned out to be
**verbatim identical across candidates**. A full-corpus check: of 300,171 stint
descriptions, there are exactly **44 unique texts** (99.99% duplication). The entire
career-text layer of this dataset is a 44-template library — ~21 non-tech, ~7
generic-engineering, ~6 data/ML-adjacent, and ~10 retrieval/ranking-flavored
templates of graded quality (from "recommendation-style features, lighter weight
than ranking systems" ×369 up to "RAG ranking pipeline, 50M queries/month" ×12).

Classification of all 44 against the baseline regexes found exactly three templates
with relevant content the baseline under-credits:

| Template (first words) | Carriers | Baseline credit | Lexicon catches? |
|---|---|---|---|
| "Built systems that understand what users are looking for and connect them to the most relevant..." | 4 | **none** | **no — pure paraphrase** |
| "Designed the ranking layer... how do we surface the right thing..." | 5 | none | yes (L1, L3) |
| "Led the engineering team building infrastructure to surface relevant content..." | 2 | none | yes (L3) |

## Concrete candidates affected

**Under-credited (genuine misses):**

| Candidate | Profile | Today | With paraphrase credit |
|---|---|---|---|
| CAND_0093193 | Senior MLE, 7.9y — carries the fully invisible template | career_ev **0.0**, score 0.458 (~rank 250) | ev ≈ 0.5 → score ≈ 0.62, **enters top-100**. This is the JD's "plain-language Tier 5" warning made flesh. |
| CAND_0005538 | Senior AI Engineer, 5.9y (in-band) | 0.515 | ≈ 0.60, borderline top-100 |
| CAND_0061257 | Staff MLE @ LinkedIn (the Phase 3 audit's #93) | 0.620 | 0.690, ~rank 60 — properly credited at last |
| CAND_0068351 | Lead AI Engineer, 6.4y | 0.623 | 0.690 |
| + 6 crossers at the bubble | Search/Reco/MLE titles, "query expansion"/"tf-idf" template | 0.54–0.60 | 0.61–0.67, enter ranks ~70–100 |

**Possibly incorrectly promoted (false-positive analysis):**

- Title distribution of all 495 lexicon-hit candidates: 100% relevant/adjacent
  engineering titles. The feared SEO/marketing false-positive surface ("search
  results", "personalized content", CTR language) **did not materialize** — Cohort B
  is empty, so no non-technical candidate writes this language in this dataset.
- One honeypot (CAND_0093331, 16.1y) had lexicon hits; the ×0.05 factor keeps it
  excluded. Correct behavior.
- Residual risk: the 6 bubble-crossers would displace 6 current members whose
  evidence is keyword-explicit; both groups are legitimate engineers. With ±0.07
  score deltas at a <0.016-wide bubble, **the 0.7 confidence factor decides who wins
  — it must be validated against hand labels (Phase 7), not assumed.**
- Template-credit at exact-hash level has **zero** false-positive risk by
  construction: a template either is or is not about ranking/retrieval, decided once
  by a human reading all 44.

## Recommendation

**An embedding/transformer semantic layer is NOT justified.** Grounds:

1. **No recall benefit** — Cohort B = 0. Embeddings can only re-rank the already-recalled.
2. **The text space is 44 unique strings.** An embedding model approximates similarity
   over a corpus that can be *exhaustively, exactly* classified by a human in twenty
   minutes. A 44-row template-classification table (hash → evidence categories +
   confidence) strictly dominates: deterministic, interpretable, zero false positives,
   microseconds at rank time, trivially inside the 5-min/16GB budget.
3. Cost asymmetry: sentence-transformers adds a model artifact, ONNX dependency, and
   Stage-3 reproduction surface for a benefit of ~17 score adjustments — all of which
   the table delivers exactly.

**What to implement instead (Phase 7, gated on the hand-labeled eval set):**

- `template_evidence.yaml`: all 44 template hashes, manually labeled with evidence
  categories and a confidence weight; career-evidence scoring consults the table
  first, regex as fallback (robustness if evaluation perturbs texts).
- Validate the confidence factor (0.7 default) and the 6 bubble swaps against hand
  labels before adopting the new top-100.

**Honest caveat for Stage 5:** template hashing exploits a synthetic-data property and
would not generalize — in a production system with real free-text profiles, the
embedding layer IS the right tool, and saying exactly that (with this investigation
as evidence of choosing the simplest sufficient mechanism) is the defensible
engineering story.
