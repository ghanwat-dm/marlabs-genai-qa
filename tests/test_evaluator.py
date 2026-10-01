import json
from pathlib import Path

import pytest

from src.evaluator import evaluate_all, evaluate_recording

ROOT = Path(__file__).resolve().parents[1]
RECORDINGS = {r["recording_id"]: r for r in json.loads((ROOT / "data" / "recordings.json").read_text())}


@pytest.mark.evaluation
def test_full_offline_evaluation_runs_without_api_keys(monkeypatch):
    monkeypatch.delenv("ENABLE_DEEPEVAL", raising=False)
    report = evaluate_all()
    assert len(report["results"]) == 12
    assert report["summary"]["overall_percentage_meaningful"] is False


@pytest.mark.evaluation
def test_recording_07_provider_timeout_contract_failure():
    result = evaluate_recording(RECORDINGS["07"], include_deepeval=False)
    failures = {c["rule"] for c in result["checks"] if c["verdict"] == "FAIL"}
    assert "http_status" in failures
    assert "response_schema" in failures or "status_contract" in failures


@pytest.mark.evaluation
def test_recording_09_prompt_injection_tenant_switch_detected():
    result = evaluate_recording(RECORDINGS["09"], include_deepeval=False)
    failures = {c["rule"] for c in result["checks"] if c["verdict"] == "FAIL"}
    assert "no_unauthorized_context" in failures
    assert "required_facts" in failures
