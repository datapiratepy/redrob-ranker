"""Phase 7 — template-based career evidence (the 'simplest sufficient' semantic layer).

Phase 6 proved the dataset's 300K stint descriptions collapse to 44 unique
templates. This module scores career evidence by exact md5 lookup against the
human-labeled table in config/template_evidence.yaml; texts not in the table
(e.g., a perturbed evaluation sample) fall back to the Phase 3 regexes.

Category weights match the baseline: retrieval .35, rank_eval .25,
reco_search .25, ltr .15. Per-category confidence = max across stints.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Any

import yaml

from src.config import CONFIG_DIR

CAT_WEIGHTS = {"retrieval": 0.35, "rank_eval": 0.25, "reco_search": 0.25, "ltr": 0.15}
# display labels used by breakdowns and the reasoning engine
CAT_LABEL = {"retrieval": "retrieval/embeddings", "rank_eval": "ranking-eval",
             "reco_search": "reco/search-system", "ltr": "LTR"}


@lru_cache(maxsize=1)
def _table() -> dict[str, dict[str, Any]]:
    with open(CONFIG_DIR / "template_evidence.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return {t["md5"]: t for t in cfg["templates"]}


def lookup_stint(description: str) -> dict[str, Any] | None:
    """Return the template entry for a stint description, or None if unknown."""
    if not description:
        return None
    return _table().get(hashlib.md5(description.encode()).hexdigest())


def career_evidence(career_history: list[dict[str, Any]],
                    regex_fallback) -> tuple[float, list[str], bool, int]:
    """Score career evidence from the template table.

    regex_fallback: callable(text) -> (conf_by_cat: dict, shipped: bool) used
    only for stints whose description is not one of the 44 known templates.

    Returns (career_ev 0-1, display category labels, shipped, n_unknown_stints).
    """
    conf: dict[str, float] = {}
    shipped = False
    unknown = 0
    for st in career_history:
        entry = lookup_stint(st.get("description", ""))
        if entry is not None:
            for cat, c in (entry.get("categories") or {}).items():
                conf[cat] = max(conf.get(cat, 0.0), float(c))
            if entry.get("categories") and entry.get("shipped"):
                shipped = True
        else:
            unknown += 1
            rc, rs = regex_fallback(st.get("description", ""))
            for cat, c in rc.items():
                conf[cat] = max(conf.get(cat, 0.0), c)
            shipped = shipped or rs
    ev = sum(CAT_WEIGHTS[c] * v for c, v in conf.items())
    if conf and not shipped:
        ev *= 0.8  # same dampener as the baseline regex path
    cats = [CAT_LABEL[c] for c, v in sorted(conf.items(), key=lambda x: -x[1]) if v >= 0.5]
    return min(ev, 1.0), cats, shipped, unknown


def stint_categories(description: str, regex_fallback) -> list[str]:
    """Per-stint category keys ('retrieval', ...) for the reasoning engine."""
    entry = lookup_stint(description)
    if entry is not None:
        return [c for c, v in (entry.get("categories") or {}).items() if float(v) >= 0.5]
    rc, _ = regex_fallback(description)
    return [c for c, v in rc.items() if v >= 0.5]
