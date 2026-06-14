# Redrob Ranker — Intelligent Candidate Discovery & Ranking Challenge

Ranks the top 100 candidates from a 100,000-candidate pool against the Redrob
Senior AI Engineer JD, under challenge constraints (≤5 min wall-clock, CPU-only,
≤16 GB RAM, no network during ranking).

## Project status

| Phase | Status |
|---|---|
| 0 — Setup & data loading | ✅ done |
| 1 — JD reverse engineering | ✅ done (`config/jd_signals.yaml`, `docs/phase1_jd_analysis.md`) |
| 2 — Dataset exploration | ✅ done (`docs/phase2_eda_findings.md`, `src/eda_scan.py`) |
| 3 — Baseline ranker | ✅ done (`src/scoring.py`, `src/baseline_ranker.py`, `docs/phase3_baseline_design.md`) |
| 4 — Honeypot detection | ✅ done (`docs/phase4_improvements.md` — H6 check, title fix, location split) |
| 5 — Reasoning engine | ✅ done (`src/reasoning_engine.py`, `docs/phase5_reasoning_design.md`, `docs/sample_reasoning_output.md`) |
| 6 — Semantic layer | ✅ investigated (`docs/phase6_semantic_investigation.md` — verdict: 44-template table, NOT embeddings) |
| 7 — Final ranking | ✅ done (`config/template_evidence.yaml`, `docs/phase7_template_classification.md`, `docs/phase7_evaluation.md`, `outputs/updated_top100.csv`) |
| 8 — Hopper penalty investigation | ✅ done (`docs/phase8_hopper_analysis.md` — penalty ×0.75 → ×0.85; final re-rank + reasoning regeneration) |

## Setup (Windows)

```bat
cd redrob-ranker
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

(macOS/Linux: `source .venv/bin/activate` instead.)

## Data

The dataset is **not committed** (465 MB). The loader looks for `candidates.jsonl`
(or `candidates.jsonl.gz`) in the parent directory of this repo by default —
i.e. the hackathon bundle folder. Override with the `REDROB_DATA` environment
variable or `--candidates` CLI flags.

## Verify your setup

```bat
python -m src.inspect_dataset            :: full structural scan of all 100K records
python -m src.inspect_dataset --limit 5000   :: quick pass
pytest tests/ -q
```

## Repo layout

```
redrob-ranker/
├── config/
│   ├── jd_signals.yaml          # Phase 1: machine-readable JD signal extraction
│   └── template_evidence.yaml   # Phase 7: 44-template career-evidence table
├── data/
│   └── sample_candidates.json   # 50-candidate sample for the Colab sandbox
├── docs/                        # phase design docs + audit trail
│   ├── phase1_jd_analysis.md … phase8_hopper_analysis.md
│   ├── final_submission_audit.md
│   └── sandbox_setup.md
├── notebooks/
│   └── redrob_ranker_sandbox.ipynb   # Colab sandbox (§10.5)
├── src/
│   ├── config.py                # paths + constants, single source of truth
│   ├── data_loader.py           # streaming JSONL loader (gzip-transparent)
│   ├── scoring.py               # five-component interpretable scorer
│   ├── template_evidence.py     # md5-keyed 44-template career-evidence lookup
│   ├── reasoning_engine.py      # fact-grounded, hallucination-checked reasoning
│   └── baseline_ranker.py       # chunked ranker CLI + explain mode
├── tests/
│   └── test_data_loader.py
├── outputs/                     # generated artifacts (gitignored except final CSV)
│   └── updated_top100.csv       # final submission candidate
├── rank.py                      # single-command reproduction entry point (§10.3)
├── validate_submission.py        # official hackathon validator
├── submission_metadata.yaml
└── requirements.txt
```

## Reproduction (submission_spec.md §10.3)

```
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

Two streaming passes, CPU-only, no network, no model artifacts. Measured ~60s on
the full 100K pool (5-min budget: ~5× headroom). Deterministic — repeated runs
produce a byte-identical CSV. Validate before upload:

```
python validate_submission.py submission.csv   # validator from the hackathon bundle
```

Phase 8 addendum: hopper penalty ×0.75 → ×0.85 (see `docs/phase8_hopper_analysis.md`).
Final pre-submission audit: `docs/final_submission_audit.md`.

## Sandbox (§10.5)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/datapiratepy/redrob-ranker/blob/main/notebooks/redrob_ranker_sandbox.ipynb)

**Notebook:** `notebooks/redrob_ranker_sandbox.ipynb`

Runs the full pipeline on the 50-candidate sample bundled with the hackathon.
No dataset upload required — sample data is converted inline.

Steps: install pyyaml → clone repo → convert sample JSON → `rank.py` → display
top-10 table + score chart → validator → CSV download.

Runtime on Colab CPU: < 60 seconds.

The Colab notebook provides a reproducible CPU-only demonstration of the ranking pipeline on the provided sample dataset.
