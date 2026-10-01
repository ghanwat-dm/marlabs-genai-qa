from __future__ import annotations

from typing import Any

from .citation_checker import citation_quote_matches
from .identity import IdentityError, get_identity
from .models import Policy, check_result
from .policy_engine import is_policy_eligible, policy_by_id
from .semantic_checker import find_prohibited_claims, required_facts_satisfied


def _observed_business(recording: dict[str, Any]) -> dict[str, Any]:
    return recording.get("observed", {})


def assert_http_status(recording: dict[str, Any], expected: dict[str, Any]):
    observed = recording.get("http_status")
    exp = expected.get("expected_http_status")
    ok = observed == exp
    return check_result("http_status", exp, observed, "PASS" if ok else "FAIL", "HTTP status matches contract." if ok else "HTTP status violates expected contract mapping.")


def assert_response_schema(recording: dict[str, Any], expected: dict[str, Any]):
    obs = _observed_business(recording)
    http = recording.get("http_status")
    if http == 200:
        required = {"status", "answer", "citations"}
        missing = sorted(required - set(obs.keys()))
        ok = not missing and isinstance(obs.get("citations"), list)
        reason = "Business outcome contains status, answer, and citations." if ok else f"Business outcome schema invalid; missing={missing}."
        return check_result("response_schema", "status + answer + citations", obs, "PASS" if ok else "FAIL", reason)
    error = obs.get("error")
    ok = isinstance(error, dict) and bool(error.get("code")) and bool(error.get("message")) and not any(k in obs for k in ("status", "answer", "citations"))
    reason = "Error body uses {error:{code,message}} and is not a business outcome." if ok else "Error body does not match required error-only structure."
    return check_result("response_schema", "error-only body for non-200 responses", obs, "PASS" if ok else "FAIL", reason)


def assert_status_contract(recording: dict[str, Any], expected: dict[str, Any]):
    exp = expected.get("expected_response_status")
    obs = _observed_business(recording).get("status")
    if exp is None:
        ok = obs is None
        return check_result("status_contract", None, obs, "PASS" if ok else "FAIL", "No business status expected for error response." if ok else "Business status present where error response is expected.")
    ok = obs == exp
    return check_result("status_contract", exp, obs, "PASS" if ok else "FAIL", "Response status matches expected business outcome." if ok else "Response status does not match policy/evidence outcome.")


def assert_policy_eligibility(recording: dict[str, Any], expected: dict[str, Any], policies: list[Policy]):
    request = recording.get("request", {})
    try:
        caller = get_identity(request.get("caller_id"))
    except IdentityError:
        return check_result("policy_eligibility", "no policy access", recording.get("model_context_ids", []), "PASS" if not recording.get("model_context_ids") else "FAIL", "Unknown/missing callers must not receive policy context.")
    ineligible = []
    for cid in recording.get("model_context_ids", []):
        policy = policy_by_id(policies, cid)
        if policy is None or not is_policy_eligible(policy, caller, request.get("as_of", "0001-01-01")):
            ineligible.append(cid)
    ok = not ineligible
    return check_result("policy_eligibility", "all model context policies eligible", recording.get("model_context_ids", []), "PASS" if ok else "FAIL", "All context obeys tenant/role/state/effective-date rules." if ok else f"Ineligible context IDs sent to generation: {ineligible}.")


def assert_context_eligibility(recording: dict[str, Any], expected: dict[str, Any]):
    allowed = set(expected.get("eligible_context_ids", []))
    actual = set(recording.get("model_context_ids", []))
    unexpected = sorted(actual - allowed)
    # For insufficient evidence, any context is unexpected; for answer/conflict, relevant context is constrained.
    ok = not unexpected
    return check_result("context_eligibility", sorted(allowed), sorted(actual), "PASS" if ok else "FAIL", "Generation context contains only relevant eligible evidence." if ok else f"Context includes IDs outside independently derived relevant eligible set: {unexpected}.")


def assert_no_unauthorized_context(recording: dict[str, Any], expected: dict[str, Any], policies: list[Policy]):
    request = recording.get("request", {})
    try:
        caller = get_identity(request.get("caller_id"))
    except IdentityError:
        unauthorized = list(recording.get("model_context_ids", []))
    else:
        unauthorized = []
        for cid in recording.get("model_context_ids", []):
            p = policy_by_id(policies, cid)
            if p is None or p.tenant != caller.tenant or p.role != caller.role:
                unauthorized.append(cid)
    ok = not unauthorized
    return check_result("no_unauthorized_context", "no cross-tenant/cross-role model context", recording.get("model_context_ids", []), "PASS" if ok else "FAIL", "No unauthorized tenant/role context was sent." if ok else f"Unauthorized context IDs: {unauthorized}.")


def assert_citation_chunk_valid(recording: dict[str, Any], expected: dict[str, Any], policies: list[Policy]):
    citations = _observed_business(recording).get("citations")
    if citations is None:
        return check_result("citation_chunk_valid", "citations only on business outcomes", None, "NOT_EVALUATED", "No citation field is present on this error response.")
    request = recording.get("request", {})
    try:
        caller = get_identity(request.get("caller_id"))
    except IdentityError:
        caller = None
    invalid = []
    for c in citations:
        p = policy_by_id(policies, c.get("chunk_id", ""))
        if p is None:
            invalid.append(c.get("chunk_id"))
            continue
        if caller is None or not is_policy_eligible(p, caller, request.get("as_of", "0001-01-01")):
            invalid.append(c.get("chunk_id"))
    ok = not invalid
    return check_result("citation_chunk_valid", "every cited chunk exists and is eligible", [c.get("chunk_id") for c in citations], "PASS" if ok else "FAIL", "All citation IDs are valid and eligible." if ok else f"Invalid or ineligible citations: {invalid}.")


def assert_citation_quote_integrity(recording: dict[str, Any], expected: dict[str, Any], policies: list[Policy]):
    citations = _observed_business(recording).get("citations")
    if citations is None:
        return check_result("citation_quote_integrity", "actual policy passage text", None, "NOT_EVALUATED", "No citations exist on this error response.")
    bad = [c.get("chunk_id") for c in citations if not citation_quote_matches(c, policies)]
    ok = not bad
    return check_result("citation_quote_integrity", "citation quote exactly equals stored policy passage", citations, "PASS" if ok else "FAIL", "Citation quotations match the source corpus." if ok else f"Quote mismatch for citation IDs: {bad}.")


def assert_required_facts(recording: dict[str, Any], expected: dict[str, Any]):
    facts = expected.get("required_facts", [])
    status = expected.get("expected_response_status")
    answer = _observed_business(recording).get("answer")
    if status != "ANSWERED":
        ok = answer is None
        return check_result("required_facts", "answer must be null for non-ANSWERED outcome", answer, "PASS" if ok else "FAIL", "No answer is returned when no supported answer is expected." if ok else "Answer should be null for this expected outcome.")
    ok, missing = required_facts_satisfied(answer, facts, recording.get("request", {}).get("question"))
    return check_result("required_facts", facts, answer, "PASS" if ok else "FAIL", "Required meaning is present without exact full-answer matching." if ok else f"Missing required semantic facts: {missing}.")


def assert_prohibited_claims_absent(recording: dict[str, Any], expected: dict[str, Any]):
    answer = _observed_business(recording).get("answer")
    prohibited = expected.get("prohibited_claims", [])
    hits = find_prohibited_claims(answer, prohibited)
    ok = not hits
    return check_result("prohibited_claims_absent", f"none of {prohibited}", answer, "PASS" if ok else "FAIL", "No prohibited business claims detected." if ok else f"Detected prohibited claims: {hits}.")


def assert_generation_attempts(recording: dict[str, Any], expected: dict[str, Any]):
    exp = expected.get("expected_generation_behavior", {})
    actual = recording.get("generation_attempts")
    if actual is None:
        return check_result("generation_attempts", exp, None, "NOT_EVALUATED", "Trace does not provide generation_attempts.")
    max_attempts = exp.get("max_attempts", 1)
    must_not = exp.get("must_not_generate", False)
    ok = actual == 0 if must_not else actual <= max_attempts
    reason = "Generation-attempt constraint satisfied." if ok else "Generation attempts violate no-call or at-most-one-attempt requirement."
    return check_result("generation_attempts", exp, actual, "PASS" if ok else "FAIL", reason)


def assert_provider_event(recording: dict[str, Any], expected: dict[str, Any]):
    event = recording.get("provider_event")
    exp = expected.get("expected_provider_behavior")
    if event is None:
        return check_result("provider_event", exp, None, "NOT_EVALUATED", "provider_event trace is missing.")
    if exp == "success_or_not_called":
        ok = event in {"success", "not_called"}
    else:
        ok = event == exp
    return check_result("provider_event", exp, event, "PASS" if ok else "FAIL", "Provider event is consistent with expected behavior." if ok else "Provider event is inconsistent with request/error contract.")


def assert_error_contract(recording: dict[str, Any], expected: dict[str, Any]):
    if expected.get("expected_http_status") == 200:
        return check_result("error_contract", "not applicable to business outcome", _observed_business(recording), "NOT_EVALUATED", "Expected response is a business outcome.")
    obs = _observed_business(recording)
    error = obs.get("error")
    ok = isinstance(error, dict) and isinstance(error.get("code"), str) and bool(error.get("code").strip()) and isinstance(error.get("message"), str) and bool(error.get("message").strip()) and not any(k in obs for k in ("status", "answer", "citations"))
    return check_result("error_contract", "stable non-empty code + safe non-empty message; no business body", obs, "PASS" if ok else "FAIL", "Error response structure is safe and distinct from business outcomes." if ok else "Error structure is missing/invalid or mixed with a business outcome.")


def assert_no_generation_on_invalid_request(recording: dict[str, Any], expected: dict[str, Any]):
    if not expected.get("expected_generation_behavior", {}).get("must_not_generate"):
        return check_result("no_generation_on_invalid_request", "applies only to invalid request/identity", recording.get("generation_attempts"), "NOT_EVALUATED", "This request is not in the no-generation category.")
    attempts = recording.get("generation_attempts")
    event = recording.get("provider_event")
    ok = attempts == 0 and event == "not_called" and not recording.get("model_context_ids")
    return check_result("no_generation_on_invalid_request", {"generation_attempts": 0, "provider_event": "not_called", "model_context_ids": []}, {"generation_attempts": attempts, "provider_event": event, "model_context_ids": recording.get("model_context_ids")}, "PASS" if ok else "FAIL", "Invalid/unauthenticated request did not invoke generation." if ok else "Invalid/unauthenticated request shows generation or context activity.")
