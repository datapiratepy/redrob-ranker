"""Central configuration: paths and dataset constants.

Single source of truth — every module imports paths from here, never
hardcodes them. Data location resolution order:

1. ``REDROB_DATA`` environment variable (full path to the .jsonl/.jsonl.gz)
2. ``candidates.jsonl`` in the hackathon bundle dir (parent of this repo)
3. ``candidates.jsonl.gz`` in the same place
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo root = parent of src/
REPO_ROOT = Path(__file__).resolve().parent.parent

# Hackathon bundle (JD, schema, dataset) lives one level above the repo.
BUNDLE_DIR = REPO_ROOT.parent

CONFIG_DIR = REPO_ROOT / "config"
OUTPUTS_DIR = REPO_ROOT / "outputs"

# Dataset invariants from the challenge spec.
EXPECTED_CANDIDATE_COUNT = 100_000
CANDIDATE_ID_PATTERN = r"^CAND_[0-9]{7}$"
REQUIRED_TOP_LEVEL_KEYS = (
    "candidate_id",
    "profile",
    "career_history",
    "education",
    "skills",
    "redrob_signals",
)
REQUIRED_SIGNAL_COUNT = 23


def resolve_candidates_path(explicit: str | os.PathLike | None = None) -> Path:
    """Locate the candidates file. Raise FileNotFoundError with guidance if absent."""
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
        raise FileNotFoundError(f"--candidates path does not exist: {p}")

    env = os.environ.get("REDROB_DATA")
    if env:
        p = Path(env)
        if p.exists():
            return p
        raise FileNotFoundError(f"REDROB_DATA points to a missing file: {p}")

    for name in ("candidates.jsonl", "candidates.jsonl.gz"):
        p = BUNDLE_DIR / name
        if p.exists():
            return p

    raise FileNotFoundError(
        "candidates.jsonl(.gz) not found. Place it in the bundle directory "
        f"({BUNDLE_DIR}) or set REDROB_DATA."
    )
