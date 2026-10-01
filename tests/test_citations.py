import json
from pathlib import Path

from src.assertions import assert_citation_chunk_valid, assert_citation_quote_integrity
from src.expected_results import derive_expected
from src.policy_engine import load_policies

ROOT = Path(__file__).resolve().parents[1]
POLICIES = load_policies()
RECORDINGS = {r["recording_id"]: r for r in json.loads((ROOT / "data" / "recordings.json").read_text())}


def expected(r):
    return derive_expected(r["request"], POLICIES, r.get("provider_event"))


def test_recording_06_quote_override_is_detected():
    r = RECORDINGS["06"]
    result = assert_citation_quote_integrity(r, expected(r), POLICIES)
    assert result["verdict"] == "FAIL"


def test_recording_02_cross_role_citation_is_detected():
    r = RECORDINGS["02"]
    result = assert_citation_chunk_valid(r, expected(r), POLICIES)
    assert result["verdict"] == "FAIL"


def test_recording_01_valid_citation_passes():
    r = RECORDINGS["01"]
    assert assert_citation_chunk_valid(r, expected(r), POLICIES)["verdict"] == "PASS"
    assert assert_citation_quote_integrity(r, expected(r), POLICIES)["verdict"] == "PASS"
