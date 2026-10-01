from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .assertions import (
    assert_citation_chunk_valid,
    assert_citation_quote_integrity,
    assert_context_eligibility,
    assert_error_contract,
    assert_generation_attempts,
    assert_http_status,
    assert_no_generation_on_invalid_request,
    assert_no_unauthorized_context,
    assert_policy_eligibility,
    assert_prohibited_claims_absent,
    assert_provider_event,
    assert_required_facts,
    assert_response_schema,
    assert_status_contract,
)
from .deepeval_evaluator import evaluate_with_deepeval
from .expected_results import derive_expected
from .policy_engine import load_policies, policy_by_id

ROOT = Path(__file__).resolve().parents[1]

RULE_TO_RISK = {
    "http_status": "Response Contract",
    "response_schema": "Response Contract",
    "status_contract": "Response Contract",
    "policy_eligibility": "Policy Eligibility",
    "context_eligibility": "RAG Context",
    "no_unauthorized_context": "Security",
    "citation_chunk_valid": "Citation Integrity",
    "citation_quote_integrity": "Citation Integrity",
    "required_facts": "Answer Semantics",
    "prohibited_claims_absent": "Security",
    "generation_attempts": "Provider Behavior",
    "provider_event": "Provider Behavior",
    "error_contract": "Error Handling",
    "no_generation_on_invalid_request": "Error Handling",
}


def load_json(path: Path | str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_recording(recording: dict[str, Any], policies=None, include_deepeval: bool = True) -> dict[str, Any]:
    policies = policies or load_policies()
    expected = derive_expected(recording["request"], policies, recording.get("provider_event"))

    checks = [
        assert_http_status(recording, expected),
        assert_response_schema(recording, expected),
        assert_status_contract(recording, expected),
        assert_policy_eligibility(recording, expected, policies),
        assert_context_eligibility(recording, expected),
        assert_no_unauthorized_context(recording, expected, policies),
        assert_citation_chunk_valid(recording, expected, policies),
        assert_citation_quote_integrity(recording, expected, policies),
        assert_required_facts(recording, expected),
        assert_prohibited_claims_absent(recording, expected),
        assert_generation_attempts(recording, expected),
        assert_provider_event(recording, expected),
        assert_error_contract(recording, expected),
        assert_no_generation_on_invalid_request(recording, expected),
    ]

    if include_deepeval and recording.get("http_status") == 200 and recording.get("observed", {}).get("answer"):
        context = []
        for cid in recording.get("model_context_ids", []):
            policy = policy_by_id(policies, cid)
            if policy:
                context.append(policy.passage)
        checks.extend(
            evaluate_with_deepeval(
                recording["request"]["question"],
                recording["observed"]["answer"],
                context,
            )
        )

    for check in checks:
        check["risk_area"] = RULE_TO_RISK.get(check["rule"], "Answer Semantics" if check["rule"].startswith("deepeval") else "Other")

    return {
        "recording_id": recording["recording_id"],
        "request": recording["request"],
        "expected_result": expected,
        "checks": checks,
    }


def summarize(results: list[dict[str, Any]], designed_not_run: int = 0) -> dict[str, Any]:
    by_risk: dict[str, Counter] = defaultdict(Counter)
    overall = Counter()
    for result in results:
        for check in result["checks"]:
            verdict = check["verdict"]
            by_risk[check["risk_area"]][verdict] += 1
            overall[verdict] += 1
    overall["NOT_RUN"] += designed_not_run

    summary = {}
    for area, counts in by_risk.items():
        denominator = sum(counts.values())
        summary[area] = {
            "PASS": counts["PASS"],
            "FAIL": counts["FAIL"],
            "NOT_EVALUATED": counts["NOT_EVALUATED"],
            "NOT_RUN": counts["NOT_RUN"],
            "denominator": denominator,
        }
    summary["Designed Future Tests"] = {
        "PASS": 0,
        "FAIL": 0,
        "NOT_EVALUATED": 0,
        "NOT_RUN": designed_not_run,
        "denominator": designed_not_run,
    }
    return {
        "by_risk_area": summary,
        "overall_counts": dict(overall),
        "overall_percentage_meaningful": False,
        "overall_percentage_note": (
            "An overall pass percentage is not meaningful for this small, risk-biased synthetic sample. "
            "Checks have unequal safety impact, multiple checks can describe one defect, and NOT_EVALUATED/NOT_RUN evidence gaps must not be treated as passes."
        ),
    }


def evaluate_all(recordings_path: Path | str = ROOT / "data" / "recordings.json") -> dict[str, Any]:
    policies = load_policies()
    recordings = load_json(recordings_path)
    results = [evaluate_recording(r, policies=policies) for r in recordings]
    dataset = load_json(ROOT / "data" / "evaluation_dataset.json")
    future_count = sum(1 for s in dataset if s.get("execution_status") == "NOT_RUN")
    return {
        "source": "Marlabs GenAI QA Candidate Assessment - offline supplied recordings",
        "evaluation_mode": "OFFLINE_DETERMINISTIC_WITH_OPTIONAL_DEEPEVAL",
        "results": results,
        "summary": summarize(results, future_count),
    }
