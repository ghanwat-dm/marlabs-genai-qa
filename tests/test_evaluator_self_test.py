import json
from pathlib import Path

import pytest

from src.evaluator import evaluate_recording

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "evaluator_tests" / name).read_text())


@pytest.mark.evaluation
@pytest.mark.parametrize("variant", load("faulty_variants.json"), ids=lambda x: x["variant_id"])
def test_faulty_variants_are_detected(variant):
    candidate = dict(variant["candidate"])
    candidate["recording_id"] = variant["variant_id"]
    result = evaluate_recording(candidate, include_deepeval=False)
    failures = {c["rule"] for c in result["checks"] if c["verdict"] == "FAIL"}
    assert failures.intersection(variant["expected_detected_by"]), (variant["variant_id"], failures)


@pytest.mark.evaluation
@pytest.mark.parametrize("variant", load("valid_variants.json"), ids=lambda x: x["variant_id"])
def test_valid_meaning_preserving_variants_are_accepted(variant):
    candidate = dict(variant["candidate"])
    candidate["recording_id"] = variant["variant_id"]
    result = evaluate_recording(candidate, include_deepeval=False)
    critical = {"http_status","response_schema","status_contract","policy_eligibility","context_eligibility","no_unauthorized_context","citation_chunk_valid","citation_quote_integrity","required_facts","prohibited_claims_absent","generation_attempts","provider_event"}
    failures = [c for c in result["checks"] if c["rule"] in critical and c["verdict"] == "FAIL"]
    assert not failures, failures
