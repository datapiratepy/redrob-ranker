# Redrob Ranker — Intelligent Candidate Discovery & Ranking Challenge

Ranks the top 100 candidates from a 100,000-candidate pool against the Redrob
Senior AI Engineer JD, under challenge constraints (≤5 min wall-clock, CPU-only,
≤16 GB RAM, no network during ranking).

## Project status

| Phase | Status |
|---|---|
| 0 — Setup & data loading | ✅ done |
| 1 — JD reverse engineering | ✅ done (`config/jd_signals.yaml`, `docs/phase1_jd_analysis.md`) |
| 2 — Dataset exploration | ⬜ |
| 3 — Baseline ranker | ⬜ |
| 4 — Honeypot detection | ⬜ |
| 5 — Reasoning engine | ⬜ |
| 6 — Semantic layer | ⬜ |
| 7 — Final ranking | ⬜ |

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
│   └── jd_signals.yaml      # Phase 1: machine-readable JD signal extraction
├── docs/
│   └── phase1_jd_analysis.md
├── notebooks/               # EDA notebooks (Phase 2)
├── src/
│   ├── config.py            # paths + constants, single source of truth
│   ├── data_loader.py       # streaming JSONL loader
│   └── inspect_dataset.py   # structural verification CLI
├── tests/
│   └── test_data_loader.py
├── outputs/                 # generated artifacts (gitignored)
└── requirements.txt
```

## Reproduction (final — will be updated in Phase 7)

```
python rank.py --candidates ../candidates.jsonl --out ./submission.csv
```
