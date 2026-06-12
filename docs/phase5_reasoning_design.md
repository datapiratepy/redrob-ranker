# Phase 5 — Reasoning Engine Design

Goal: reasoning strings that pass all six Stage 4 checks. Scoring and ordering are
untouched — the engine is a post-processing step over the frozen top-100.

## Architecture: facts → bands → templates, never free text

```
candidate record ──► FACT EXTRACTION (verified evidence only)
        + breakdown      │  strengths (with JD hooks)  +  concerns (ordered by severity)
        + rank           ▼
                 RANK BAND (1-10 / 11-40 / 41-80 / 81-100)
                         ▼
                 TEMPLATE ASSEMBLY (deterministic variation via crc32(candidate_id))
                         ▼
                 MECHANICAL VERIFICATION (hallucination / length / uniqueness)
```

### 1. Fact extraction — the anti-hallucination boundary

Every clause is built from a fact tuple read directly from the record. The engine
can only mention: the candidate's own title, YoE, city, a company **from their
career_history**, evidence categories **regex-verified inside that specific stint's
description**, a skill **from their skills array** with its real corroboration
numbers (endorsements / months / assessment score), and behavioral values from
`redrob_signals`. There is no free-text generation path, so hallucination is
structurally impossible, and a verifier still re-checks mechanically (belt and
braces — Stage 4 calls fabricated skills a red flag).

### 2. JD connection — category → requirement map

| Verified evidence | JD hook used in text |
|---|---|
| retrieval/embeddings in stint text | "the JD's core production embeddings/retrieval requirement" |
| ranking-eval (NDCG/MRR/A-B) | "the evaluation-framework experience the JD treats as a must-have" |
| reco/search system shipped | "the shipped search/recommendation system the ideal profile calls for" |
| LTR | "learning-to-rank depth (JD nice-to-have)" |
| 5–9 YoE | "inside the JD's 5–9y band" |
| Pune/Noida/welcome city | "location fits the hybrid Pune/Noida setup" |

### 3. Honest concerns — severity-ordered, max 2

notice >60d · inactive >90d · response rate <0.2 · non-India (with relocation
status) · YoE outside 4–9 · penalty flags (hopper etc.) · thin career evidence
(career_ev <0.5). Concerns are real score-drivers, so tone automatically tracks
rank — a borderline candidate genuinely has more to disclose.

### 4. Rank consistency — four tone bands

| Band | Structure | Verb register |
|---|---|---|
| 1–10 | 2 strengths; concern only if severe | "exactly", "squarely", "strong" |
| 11–40 | 2 strengths + top concern | "strong", "well-aligned" |
| 41–80 | 1–2 strengths + 1 concern | "solid", "credible", "reasonable" |
| 81–100 | 1 strength + 1–2 concerns | "borderline", "included on", "despite" |

### 5. Variation — deterministic, not random

Template slot choices are selected by `crc32(candidate_id + slot)` — different
candidates draw different phrasings, but every run is byte-identical
(reproducibility requirement for Stage 3). 3–5 lexical variants per slot across
4 bands; fact selection also varies (lead with title vs evidence vs domain
depending on which component scored highest).

### 6. Mechanical verification (runs on all 100 before writing)

- Every company / skill token inserted exists in the candidate's record.
- 1–2 sentences, ≤ 320 chars.
- All 100 strings pairwise distinct; no template fires >15 times verbatim-structurally.
- Non-empty for every row.

## Pipeline position

`baseline_ranker.py` (ranking, frozen) → `reasoning_engine.py` (reasoning column
rewrite, order-preserving) → `validate_submission.py`. The engine asserts the
output CSV has identical candidate_id/rank/score columns to its input.
