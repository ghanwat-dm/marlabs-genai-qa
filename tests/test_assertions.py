import json
from pathlib import Path

from src.assertions import (
    assert_no_generation_on_invalid_request,
    assert_no_unauthorized_context,
    assert_prohibited_claims_absent,
    assert_required_facts,
    assert_status_contract,
)
from src.expected_results import derive_expected
from src.policy_engine import load_policies

ROOT = Path(__file__).resolve().parents[1]
POLICIES = load_policies()
RECORDINGS = {r["recording_id"]: r for r in json.loads((ROOT / "data" / "recordings.json").read_text())}


def exp(r):
    return derive_expected(r["request"], POLICIES, r.get("provider_event"))


def test_semantic_variation_recording_11_is_accepted():
    r = RECORDINGS["11"]
    assert assert_required_facts(r, exp(r))["verdict"] == "PASS"


def test_conflict_recording_04_is_detected():
    r = RECORDINGS["04"]
    assert assert_status_contract(r, exp(r))["verdict"] == "FAIL"


def test_unauthorized_context_recording_08_is_detected():
    r = RECORDINGS["08"]
    assert assert_no_unauthorized_context(r, exp(r), POLICIES)["verdict"] == "FAIL"


def test_financial_hallucination_recording_10_is_detected():
    r = RECORDINGS["10"]
    assert assert_prohibited_claims_absent(r, exp(r))["verdict"] == "FAIL"


def test_invalid_request_recording_12_does_not_generate():
    r = RECORDINGS["12"]
    assert assert_no_generation_on_invalid_request(r, exp(r))["verdict"] == "PASS"
