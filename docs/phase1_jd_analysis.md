# Phase 1 — JD Reverse Engineering

Source: `job_description.md` (Redrob bundle). Machine-readable output: `config/jd_signals.yaml`.
This doc explains *why* each signal was extracted and how the JD wants it interpreted.

## The single most important sentence in the JD

> "The right answer involves reasoning about the gap between what the JD says and what the JD means."

The JD's final section (written *for hackathon participants*) is an answer key. It defines both traps:
the **keyword stuffer** (perfect skills array, wrong career — e.g., the HR Manager at rank 1 of
`sample_submission.csv`) and the **plain-language Tier 5** (right career, no buzzwords). Both have the
same root cause: trusting the `skills` array over `career_history`. Our evidence hierarchy is therefore:

1. `career_history` descriptions (what they actually did)
2. Corroborated skills (assessment scores, endorsements, `duration_months`)
3. Raw skill names (lowest trust — this is the gamed surface)

## Positive signals

**Must-haves (4):** production embeddings/retrieval, vector-DB/hybrid-search ops, strong Python,
ranking evaluation (NDCG/MRR/MAP/AB). Note the JD's framing: *operational* experience, not tool
checklists — "we don't care which model... we care that you've handled embedding drift."
Implication for us: keyword hits in career descriptions ("shipped", "deployed", "production",
"scaled") matter more than the same words in the skills list.

**Nice-to-haves (5):** LLM fine-tuning, learning-to-rank, HR-tech/marketplace domain, distributed
systems, OSS. Boosts only — the JD says "won't reject you for" lacking these.

**Ideal profile:** 6–8 yrs total (5–9 acceptable, explicitly soft: "we'll seriously consider
candidates outside the band if other signals are strong" → score as a curve, never a hard gate),
4–5 yrs applied ML at *product* companies, ≥1 shipped ranking/search/reco system at scale,
in or willing to relocate to Pune/Noida, active on the platform.

## Negative signals

**Hard disqualifiers (JD: "we will not move forward"):**

| Disqualifier | Detection strategy (Phase 3) |
|---|---|
| Pure research career, no production | All roles academic/research-flavored; no shipping language anywhere |
| <12-month LangChain-only "AI experience" without pre-LLM ML history | AI skills all with low `duration_months`; career text only LLM-wrapper work |
| No production code in 18+ months (architect/manager drift) | Current title Architect/Head/Director/VP + no hands-on language. JD: "This role writes code." |

**Explicit don't-wants:** title-chasers (~1.5-yr hops up the title ladder — detectable from
`career_history` durations), framework enthusiasts, consulting-firms-ONLY careers (TCS, Infosys,
Wipro, Accenture, Cognizant, Capgemini, ... — **neutralized by any product-company stint**),
CV/speech/robotics specialists without NLP/IR, 5+ yrs closed-source with zero external validation.

Caution flags for Phase 3: the consulting check is *entire career*, not current employer; the
closed-source check is weak evidence (absence-of-signal), keep it mild.

## Behavioral signals

The JD names the principle twice: a stale, unresponsive candidate is **"not actually available"**
regardless of fit. So behavioral signals act as an **availability/reliability modifier on top of
skill-fit**, not as fit itself. Mapping of all 23 `redrob_signals` fields:

| Group | Fields | Use |
|---|---|---|
| Availability (JD-explicit) | `last_active_date` (6-mo anchor), `recruiter_response_rate` (5% anchor), `open_to_work_flag`, `applications_submitted_30d` | Core multiplier |
| Reliability | `interview_completion_rate`, `offer_acceptance_rate` (-1 = no history = neutral), `avg_response_time_hours` | Secondary multiplier |
| Logistics | `notice_period_days` (30+ = "bar gets higher" = penalty not exclusion), `preferred_work_mode`, `willing_to_relocate` | Friction adjustments |
| Trust/validation | `skill_assessment_scores` (anti-stuffer verification), `github_activity_score` (-1 = neutral-ish), `verified_email/phone`, `linkedin_connected` | Skill-claim corroboration |
| Demand-side (low trust) | `profile_views_received_30d`, `saved_by_recruiters_30d`, `search_appearance_30d` | Mostly ignore — recruiter attention is keyword-driven, i.e., the gamed metric |
| Context | `signup_date`, `profile_completeness_score`, `connection_count`, `endorsements_received`, `expected_salary_range_inr_lpa` | Minor; salary has no JD comp anchor to compare against |

## Hidden hiring preferences

1. **Shipper > researcher** ("tilt slightly toward shipper").
2. **Precision > recall** ("10 great matches over 1000 maybes") — conservative, defensible top-10; aligns with NDCG@10 carrying 50% of the composite.
3. **Career text > skills array** — the anti-trap principle.
4. **3+ year commitment intent** — stint-length pattern matters beyond title-chasing.
5. **Writing culture** — articulate summaries are a weak positive.
6. **Pre-LLM fundamentals** — retrieval/ranking work predating ~2022 signals authenticity.
7. **Opinionated seniority** — ownership/decision language in career descriptions.
8. **Startup adaptability** — early-stage company sizes are mild positive context; big-tech-only comfort-seeking is warned off.

## What Phase 3 consumes from this

`config/jd_signals.yaml` gives the baseline ranker: evidence keyword lists per must-have,
disqualifier detection hints, the consulting-firm list, location tiers, behavioral field
directions/anchors, and severity tags. **Weights are deliberately absent** — they're a Phase 3
decision, tuned against the Phase 2/3 hand-labeled validation set.
