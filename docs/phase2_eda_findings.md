# Phase 2 — EDA Findings

Source: full scan of all 100,000 records via `src/eda_scan.py` (chunked single-pass scanner;
aggregates in `outputs/eda_stats.json`, flagged profiles in `outputs/honeypot_suspects.csv`).
All numbers below are measured, not estimated. Dataset reference date: 2026-06-01
(max `last_active_date` observed: 2026-05-27 — consistent).

## A. Candidate population

| Dimension | Finding | Ranking implication |
|---|---|---|
| Geography | India 75.1%, USA 10.0%, AUS/CAN/UK/DE ~2.5% each | Country filter is cheap and aligned with JD (no visa sponsorship) |
| Cities | Nearly uniform ~4.2K per Indian city (Pune 4,186, Noida 4,283, Bangalore 4,238...) | Synthetic uniformity — location won't shrink the pool much; it's a fit modifier, not a recall filter |
| Experience | Roughly uniform: 5–9 yr band holds ~34K candidates | YoE alone is nearly useless as a discriminator — must combine with role evidence |
| Industry | IT Services 29.9%, Software 22.4%, Manufacturing 22.3% | `IT Services` + `Consulting` industries give a workable services-career detector |
| Company size | 40.5% at 10001+ | Mild signal for the startup-adaptability hidden preference |
| Titles | 47 distinct; top 12 are all non-tech (~5.7K each, again uniform) | ~70% of the pool is trivially irrelevant by title alone |

## B. AI/ML candidate discovery — the funnel

Venn over four independent relevance markers (T = AI/ML title, S = ≥2 JD-aligned skills,
C = core retrieval/ranking/search language in career history, M = general ML language in career history):

| Cohort | Count | Reading |
|---|---|---|
| AI/ML-titled (T) | **1,126** (1.1%) | The obvious pool |
| ≥2 JD-aligned skills (S) | 9,600 (9.6%) | 8.5× larger than T — most of S is **not** corroborated elsewhere |
| Core career-text evidence (C) | **503** (0.5%) | The scarcest, hardest-to-fake marker |
| General ML career text (M) | ~39,981 (40%) | Far too common — casual ML mentions everywhere |
| T ∩ C (title + career proof) | 451 | The defensible core of any top-100 |
| C without T ("plain-language") | **52** | The Tier-5 hidden gems the JD warns about |
| S without C or T | 8,672 | **The stuffer surface** — skill claims with zero career support |

**Realistic relevant pool: ~500–1,200 candidates (0.5–1.2%).** A top-100 is carved from this; the
remaining ~99% of compute is about *not being fooled*.

**Surprising finding:** my AI-title regex missed a perfect candidate titled *"Recommendation Systems
Engineer"* (6.0 yrs, shipped XGBoost/LightGBM ranking models, ran offline-online correlation analysis —
textbook JD must-have material in plain text). **Title-based recall must include search/reco/retrieval/
information-retrieval titles, and career text must always be scanned regardless of title.**

## C. Skill analysis

| Finding | Evidence | Implication |
|---|---|---|
| Raw skill frequency is near-uniform (~200 skills, each on ~2.5% of profiles) | `skill_freq` | A skill's *presence* is weak signal by design — the generator hands skills out uniformly |
| **JD-core skills have the WORST corroboration in the dataset** | embeddings/retrieval skills: avg 6.5 endorsements, 16 mo duration, 6% assessment-backed — vs learning-to-rank (19.5, 32 mo, 24%) and Python (19.8, 32 mo, 23%) | The exact skills the JD asks for are the most-stuffed ones. **Never score a JD-core skill without its endorsements/duration/assessment.** |
| Assessments are scarce | 75.8% of candidates have **zero** assessment scores | When present, an assessment is high-trust verification; absence is neutral |
| Rare-but-valuable (career text, not skill list) | "embedding/retrieval" language: 852 profiles; named vector DBs: 122; ranking-eval language (NDCG/MRR/A-B): 1,766; LTR: 1,969 | These four text markers are the strongest needles available |

## D. Career history analysis

| Pattern | Count | Implication |
|---|---|---|
| Consulting/services-only entire career | **9,745 (9.7%)** | JD strong negative — cheap, high-confidence down-rank |
| Any product-industry stint | 61.9% | Industry labels are coarse; product exposure needs text support too |
| Job-hoppers (≥3 stints, median <20 mo) | 7,148 (7.1%) | Title-chaser penalty is implementable and selective |
| 1–2 stints only | 42.7% | Career-math honeypot checks must handle short histories gracefully |
| Median stint 30–48 mo | 43.5% of pool | "3+ year commitment" signal has real spread |

## E. Behavioral signals

| Signal | Distribution | Verdict |
|---|---|---|
| `last_active_date` | 80.7% active within 180 days; **19.3% inactive 6–12 months** (none older than 1 yr) | Useful — the JD's exact "6 months" anchor splits the pool 80/20 |
| `recruiter_response_rate` | Wide spread: 5.3% below 0.10, ~27% per 0.2-band up to 0.9 | Useful — real variance, JD-anchored at "5% ≈ unavailable" |
| `open_to_work_flag` | 35.3% true | Useful availability gate/boost |
| `notice_period_days` | Only **13.8% ≤30 days**; 61.6% >60 days | Stronger differentiator than expected — JD says 30+ raises the bar |
| `skill_assessment_scores` | 75.8% have none | Scarce → verification value (see C) |
| `github_activity_score` | **64.6% = -1** (no GitHub) | -1 must be neutral, not negative — it's the majority |
| `offer_acceptance_rate` | 59.6% = -1 (no history) | Same neutral-handling rule |

## F. Honeypot investigation

Five consistency checks ran on every record:

| Check | Flags | What it catches |
|---|---|---|
| H1: ≥3 "expert" skills with ≤1 month usage | 21 | Impossible proficiency claims |
| H2: stint `duration_months` contradicts its own start/end dates (>9 mo gap) | 33 | Fabricated stint math |
| H3: claimed YoE exceeds total career history by >3.5 yrs | 25 | Inflated experience |
| **H1∪H2∪H3 distinct candidates** | **65** | **≈ the spec's "~80 honeypots"** — thresholds slightly tight; Phase 4 will tune (e.g., H2 gap >6 mo, H3 >2.5 yrs) toward ~80 |
| H4: non-tech title + ≥8 advanced/expert skills | 1,687 | **Keyword stuffers — a separate trap class**, not honeypots |
| H5: expert claim contradicted by own assessment <40 | 0 | Dead check — assessments too sparse to contradict |

Verified by manual inspection: CAND_0003430 claims 13.7 yrs on a single 11-month stint;
CAND_0003582 lists "expert" MLflow/Photoshop/Content Writing at 0 months each. Sample H4 stuffer
CAND_0000074: *Operations Manager, 1.9 yrs*, with "advanced" Sentence Transformers / Embeddings /
Recommendation Systems — 0–4 endorsements, zero assessments, career history = operations only.

**Critical:** 5 of the 65 honeypots have AI titles and 7 have core career text — **honeypots will
enter a naive shortlist.** Consistency checks are mandatory, not defensive.

## G. JD-signal alignment (Phase 1 contract, measured)

| Phase 1 signal | Prevalence | Verdict |
|---|---|---|
| embeddings/retrieval (career text) | 852 | **High value** — scarce, hard to fake |
| vector DB named in career text | 122 | **High value**, very scarce |
| ranking-eval language (NDCG/MRR/A-B) | 1,766 | **High value** — maps to a must-have |
| learning-to-rank language | 1,969 | High value (nice-to-have) |
| LLM fine-tuning language | 5,320 | Moderate |
| Python (career text) | 12,238 | Moderate — common but required |
| ml + shipping language | 32,101 | **Noisy** as a binary; useful only in combination |
| distributed-systems keywords | 44,461 | **Noisy** — generic words (scale, latency, pipeline) |
| HR-tech/marketplace domain | **7** | Effectively void — drop this nice-to-have |
| Consulting-only career | 9,745 | Implementable, selective |
| Job-hop pattern | 7,148 | Implementable, selective |

---

## Signals Likely To Matter

1. **Core retrieval/ranking/search language in `career_history` descriptions** (852–1,969 profiles per marker). Scarce, JD-central, and expensive to fake — the backbone of fit scoring.
2. **Title ∩ career-text agreement** (451 candidates). When both say AI/ML/search, confidence is high. Extend titles to reco/search/IR variants or lose Tier-5s.
3. **Skill corroboration, not skill presence**: endorsements × duration_months × assessment-backing. JD-core skills are the most-stuffed; corroboration is what separates claims from evidence.
4. **Consistency checks (H1–H3)** — they find almost exactly the planted ~80 honeypots, and some honeypots look relevant on the surface.
5. **`last_active_date` 180-day split + `recruiter_response_rate`** — real spread, explicit JD anchors; the honest availability multiplier.
6. **Consulting-only career flag** (9.7%) and **job-hop pattern** (7.1%) — cheap, selective, straight from JD hard rules.
7. **`notice_period_days` ≤30** (13.8%) — scarcer than expected, JD-anchored differentiator.
8. **`open_to_work_flag`** (35.3%) — direct JD "in the job market" requirement.

## Signals Likely To Be Misleading

1. **Raw skill-list matches** — near-uniform distribution by design; the stuffer surface (8,672 uncorroborated S-only profiles). The sample submission's HR-Manager-at-rank-1 is this failure.
2. **Generic ML/scale career language** ("machine learning", "pipeline", "latency": 32–44K hits) — 40% of the pool mentions ML; binary use would drown the real 0.5%.
3. **`profile_views/saved_by_recruiters/search_appearance_30d`** — recruiter-attention metrics reward exactly the keyword games we're defending against; near-zero weight.
4. **`github_activity_score` / `offer_acceptance_rate` raw values** — majority are -1 sentinels; treating -1 as low instead of "missing" silently punishes 60%+ of the pool.
5. **YoE in isolation** — ~34K candidates sit in the 5–9 band; it confirms, never selects.
6. **Industry = product** (61.9% "product_any") — too coarse alone; needs career-text agreement.
7. **`endorsements_received` / `connection_count` (global)** — popularity, not competence; at most a tiebreak.
8. **HR-tech domain experience** — only 7 profiles; scoring it would fit noise.

## Carry-forward to Phase 3 (baseline ranker)

Recall by **union** (any AI/search/reco title OR core career text OR ≥2 corroborated JD skills), never
intersection — Tier-5s enter via text, not title. Score from career-text evidence first, corroborated
skills second. Behavioral availability as a multiplier with JD-anchored thresholds and neutral
handling of -1 sentinels. Consulting-only and hop penalties as JD-rule modifiers. H1–H3 checks run on
every shortlisted candidate before final ranking (Phase 4 hardens them toward the ~80 target).
