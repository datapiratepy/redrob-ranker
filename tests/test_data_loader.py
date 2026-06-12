"""Unit tests for src.data_loader — run with: pytest tests/ -q"""

import gzip
import json

import pytest

from src.data_loader import iter_candidates, load_sample, validate_record


def _good_record(cid: str = "CAND_0000001") -> dict:
    return {
        "candidate_id": cid,
        "profile": {"current_title": "ML Engineer"},
        "career_history": [{"company": "Acme", "title": "ML Engineer"}],
        "education": [],
        "skills": [],
        "redrob_signals": {f"signal_{i}": 0 for i in range(23)},
    }


@pytest.fixture
def jsonl_file(tmp_path):
    p = tmp_path / "candidates.jsonl"
    records = [_good_record(f"CAND_{i:07d}") for i in range(1, 6)]
    p.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return p


def test_iter_candidates_streams_all_records(jsonl_file):
    records = list(iter_candidates(path=jsonl_file))
    assert len(records) == 5
    assert records[0]["candidate_id"] == "CAND_0000001"


def test_limit_stops_early(jsonl_file):
    assert len(list(iter_candidates(path=jsonl_file, limit=2))) == 2


def test_load_sample(jsonl_file):
    assert len(load_sample(3, path=jsonl_file)) == 3


def test_gzip_transparency(tmp_path):
    p = tmp_path / "candidates.jsonl.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(json.dumps(_good_record()) + "\n")
    records = list(iter_candidates(path=p))
    assert len(records) == 1


def test_malformed_json_raises_with_line_number(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text(json.dumps(_good_record()) + "\n{not json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        list(iter_candidates(path=p))


def test_blank_lines_skipped(tmp_path):
    p = tmp_path / "blank.jsonl"
    p.write_text(json.dumps(_good_record()) + "\n\n", encoding="utf-8")
    assert len(list(iter_candidates(path=p))) == 1


def test_validate_good_record_passes():
    assert validate_record(_good_record()) == []


def test_validate_catches_bad_id():
    rec = _good_record()
    rec["candidate_id"] = "CAND_123"  # too short
    assert any("candidate_id" in p for p in validate_record(rec))


def test_validate_catches_missing_keys():
    rec = _good_record()
    del rec["redrob_signals"]
    assert any("redrob_signals" in p for p in validate_record(rec))


def test_validate_catches_short_signals():
    rec = _good_record()
    rec["redrob_signals"] = {"only_one": 1}
    assert any("23" in p for p in validate_record(rec))


def test_validate_catches_empty_career():
    rec = _good_record()
    rec["career_history"] = []
    assert any("career_history" in p for p in validate_record(rec))
