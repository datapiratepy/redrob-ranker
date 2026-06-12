"""Streaming loader for the 100K-candidate JSONL pool.

Design notes
------------
- The uncompressed file is ~465 MB; parsed into Python dicts it is several GB.
  Default access pattern is therefore a **generator** (`iter_candidates`) so
  downstream phases can stream, filter, and project fields without holding
  the whole pool in memory.
- Handles both plain ``.jsonl`` and gzipped ``.jsonl.gz`` transparently.
- `validate_record` does cheap structural checks (keys, ID format) — full
  semantic validation against candidate_schema.json is intentionally out of
  scope here; Phase 2 explores semantics.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import IO, Any, Iterator

from src.config import (
    CANDIDATE_ID_PATTERN,
    REQUIRED_SIGNAL_COUNT,
    REQUIRED_TOP_LEVEL_KEYS,
    resolve_candidates_path,
)

Candidate = dict[str, Any]

_ID_RE = re.compile(CANDIDATE_ID_PATTERN)


def _open_maybe_gzip(path: Path) -> IO[str]:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def iter_candidates(
    path: str | Path | None = None,
    limit: int | None = None,
    skip: int = 0,
) -> Iterator[Candidate]:
    """Stream candidates one record at a time.

    Parameters
    ----------
    path:  explicit path to the jsonl(.gz); resolved via config if None.
    limit: yield at most N records (useful for quick iteration in dev).
    skip:  skip the first N lines *without parsing them* — enables cheap
           chunked processing of the 100K pool.

    Raises ``ValueError`` with the line number on malformed JSON — fail loud,
    a silently skipped record could hide a dataset bug.
    """
    resolved = resolve_candidates_path(path)
    yielded = 0
    with _open_maybe_gzip(resolved) as f:
        for line_no, line in enumerate(f, start=1):
            if line_no <= skip:
                continue
            if limit is not None and yielded >= limit:
                return
            if not line.strip():
                continue
            try:
                yield json.loads(line)
                yielded += 1
            except json.JSONDecodeError as e:
                raise ValueError(f"Malformed JSON on line {line_no}: {e}") from e


def load_sample(n: int = 50, path: str | Path | None = None) -> list[Candidate]:
    """First *n* records as a list — convenience for notebooks and tests."""
    return list(iter_candidates(path=path, limit=n))


def validate_record(record: Candidate) -> list[str]:
    """Cheap structural validation. Returns a list of problems (empty = OK)."""
    problems: list[str] = []

    cid = record.get("candidate_id", "")
    if not isinstance(cid, str) or not _ID_RE.match(cid):
        problems.append(f"bad candidate_id: {cid!r}")

    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in record:
            problems.append(f"missing top-level key: {key}")

    signals = record.get("redrob_signals")
    if isinstance(signals, dict):
        if len(signals) < REQUIRED_SIGNAL_COUNT:
            problems.append(
                f"redrob_signals has {len(signals)} keys, expected >= {REQUIRED_SIGNAL_COUNT}"
            )
    elif "redrob_signals" in record:
        problems.append("redrob_signals is not an object")

    career = record.get("career_history")
    if isinstance(career, list) and len(career) == 0:
        problems.append("career_history is empty (schema requires >= 1 entry)")

    return problems
