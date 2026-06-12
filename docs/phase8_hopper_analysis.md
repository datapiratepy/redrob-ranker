# Phase 8 — Job-Hopper Penalty Analysis

Read-only investigation via `src/hopper_probe.py` (full 100K, chunked). The live
ranking (`outputs/updated_top100.csv`) is unchanged. Artifacts:
`outputs/hopper_affected.json`.

## 1. Who is affected

| Fact | Value |
|---|---|
| Recalled pool | 5,138 |
| Hopper-penalized (≥3 stints, median <20mo) | **536 (10.4%)** |
| Penalized with strong evidence (career_ev ≥ 0.8) | **14** |
| Mean career_ev of the penalized cohort | 0.089 |

The penalty's practical footprint is tiny: 522 of 536 penalized candidates are
low-evidence profiles that wouldn't approach the top-100 regardless. **The entire
decision concerns ~14 high-evidence candidates** (Senior DS / Staff MLE / Search
Eng with career_ev 0.83–0.97 and stint medians of 12–19 months).

## 2. The detector does NOT detect title-chasers

The JD's explicit don't-want is the *title-chaser*: "optimizing for Senior → Staff
→ Principal titles by switching companies every 1.5 years." Chronological
title-ladder analysis of all 536 penalized candidates:

| Ladder pattern | Count |
|---|---|
| Climbing (the JD's actual rule) | **2** |
| Lateral (same level across hops) | 251 |
| Mixed (up and down) | 283 |

**Only 2 of 536 penalized candidates are literal title-chasers.** What the
detector actually measures is *short-stint behavior*, which connects to a
different JD requirement — "someone who plans to be here 3+ years." The penalty
is therefore defensible, but its honest justification is **retention risk, not
title-chasing**. (Documented; the YAML rationale should be reworded at adoption.)

## 3. Is hopping predictive of lower fit in this dataset?

| Signal | Hopper cohort | Read |
|---|---|---|
| Honeypot rate | 0.56% (3/536) | Hopping does NOT correlate with traps |
| Mean behavioral multiplier | 0.78 | Slightly below typical — hoppers also have somewhat weaker availability signals |
| Mean recruiter response rate | 0.50 | Unremarkable |
| Career evidence | overwhelmingly low (mean 0.089), but with a clean 14-candidate high-evidence tail | The penalty mostly hits candidates already out of contention |

No in-data evidence that short stints predict lower *skill* fit. The case for the
penalty is entirely the JD's stated retention preference — a real-world prior the
ground-truth authors explicitly wrote into the JD, which is why removing the
penalty outright is risky.

## 4. Ranking variants

| Variant | Top-100 overlap vs current | Enters | Exits |
|---|---|---|---|
| ×0.75 (current) | — | — | — |
| ×0.85 | **96/100** | 4 high-evidence hoppers: CAND_0093912 (→56), CAND_0005649 (→82), CAND_0077337 (→84), **CAND_0007412 (→100)** | current ranks 97–100 (thin-margin, tier-3-ish) |
| ×1.00 | 90/100 | those 4 + 6 more (incl. CAND_0005538, T3-labeled) | 10, incl. CAND_0013613 (Singapore, no relocation — tier 2, good riddance) but also two T30 semantic-crossers (tier 3) |

Honeypots in any variant top-100: **0** — the penalty question is fully decoupled
from trap safety.

**Labeled-candidate movements** (Phase 7 eval set):

| Candidate | Label | ×0.75 | ×0.85 | ×1.00 |
|---|---|---|---|---|
| CAND_0007412 (ev 0.965, lateral mover, 5 stints) | Tier 4 | out (135) | **in (100)** | in |
| CAND_0005538 (ev 0.83, mixed, 4 stints) | Tier 3 | out (172) | out | in |
| CAND_0000031 (Reco Eng, hopper) | Tier 3 | out (182) | out | out |
| All honeypots/stuffers | Tier 0 | out | out | out |

## 5. Verdict: current ×0.75 is **slightly too harsh** → recommend **×0.85**

The evidence triangulates:

1. **The labeled regression resolves.** The only "worsened" row in the Phase 7
   evaluation (tier-4 CAND_0007412) enters at exactly rank 100 under ×0.85 —
   the labeled set's one outstanding error is corrected with minimal disruption.
2. **The detector over-fires relative to the JD's letter** (2/536 actual
   title-chasers), so the maximum-severity reading of the JD rule isn't supported;
   but the "3+ years" retention concern still argues against removing it.
3. **×1.00 is over-correction:** it trades two tier-3 semantic-crossers for
   unvalidated candidates, ignores an explicit JD negative the ground-truth
   authors wrote themselves, and doubles the churn (10 swaps vs 4) for no labeled
   gain beyond ×0.85 (the extra entrant is tier-3, the extra exits include tier-3s).
4. **The exits at ×0.85 are the four thinnest-margin rows (97–100)** — currently
   tier-3-ish bubble candidates separated by <0.01; swapping them for ev-0.92+
   profiles with honest stint-length concerns is favorable under NDCG@50 and
   neutral-to-favorable under the JD's own "10 great matches" precision framing.

**Risk note:** if the hidden ground truth implements a severe short-stint
penalty, ×0.85 costs us ~4 rows at ranks 56–100 (NDCG@50 weight only — the top 10
are untouched in all variants). The asymmetry favors ×0.85: bounded downside at
low rank-weight, fixes a confirmed labeled error.

## Proposed change (NOT yet applied)

`src/scoring.py`: hopper multiplier 0.75 → 0.85, and reword the penalty comment
from "title-chaser rule" to "short-stint retention concern ('plans to be here
3+ years'); JD's literal title-chaser pattern occurs in only 2/536 penalized
profiles (Phase 8)." Reasoning-engine concern phrasing should shift the same way
("frequent short stints raise the JD's 3-year-commitment concern"). Apply on your
approval, then re-rank + regenerate reasoning + validator before refreshing
`updated_top100.csv`.
