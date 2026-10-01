from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from .identity import IdentityError, get_identity
from .models import Policy
from .policy_engine import eligible_policies


def _valid_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return len(value) == 10 and parsed.isoformat() == value


def validate_request(request: dict[str, Any]) -> tuple[bool, str | None]:
    question = request.get("question")
    as_of = request.get("as_of")
    if not isinstance(question, str) or not question.strip():
        return False, "question must be a non-empty string after trimming"
    if not _valid_date(as_of):
        return False, "as_of must be a real calendar date in YYYY-MM-DD format"
    return True, None


def classify_question(question: str) -> str:
    q = question.lower()
    if "certification" in q and any(x in q for x in ("reimbursement", "limit", "cap", "claim")):
        return "certification_reimbursement"
    if "home-office" in q or ("home" in q and "office" in q and "allowance" in q):
        return "home_office_allowance"
    if "rail" in q and "travel" in q:
        return "rail_travel"
    if "training" in q and any(x in q for x in ("approval", "book", "manager")):
        return "external_training_approval"
    return "unsupported"


def relevant_policies(intent: str, policies: Iterable[Policy]) -> list[Policy]:
    if intent == "certification_reimbursement":
        return [p for p in policies if "certification reimbursement limit" in p.passage.lower() and "proposed" not in p.passage.lower()]
    if intent == "home_office_allowance":
        return [p for p in policies if "home-office allowance" in p.passage.lower()]
    if intent == "rail_travel":
        return [p for p in policies if "rail travel" in p.passage.lower()]
    if intent == "external_training_approval":
        return [p for p in policies if "external training" in p.passage.lower()]
    return []


def _required_facts(intent: str, policies: list[Policy]) -> list[dict[str, Any]]:
    if intent == "certification_reimbursement" and len(policies) == 1:
        import re
        m = re.search(r"INR\s+(\d+)", policies[0].passage)
        amount = int(m.group(1)) if m else None
        facts = [{"type": "concept", "value": "certification_reimbursement"}]
        if amount is not None:
            facts.append({"type": "amount", "value": amount})
        return facts
    if intent == "home_office_allowance" and len(policies) == 1:
        import re
        m = re.search(r"INR\s+(\d+)", policies[0].passage)
        amount = int(m.group(1)) if m else None
        facts = [{"type": "concept", "value": "home_office_allowance"}]
        if amount is not None:
            facts.append({"type": "amount", "value": amount})
        return facts
    if intent == "rail_travel" and len(policies) == 1:
        return [{"type": "concept", "value": "rail_travel"}]
    if intent == "external_training_approval" and len(policies) == 1:
        return [{"type": "concept", "value": "external_training_approval"}]
    return []


def derive_expected(request: dict[str, Any], policies: list[Policy], provider_event: str | None = None) -> dict[str, Any]:
    """Derive expected behavior from contract + identity + policy corpus.

    provider_event is trace evidence, not business input. When supplied, contract-mandated
    error mapping for timeout/unavailable/malformed is applied.
    """
    valid, validation_reason = validate_request(request)
    if not valid:
        return {
            "expected_http_status": 400,
            "expected_response_status": None,
            "expected_answer_meaning": None,
            "required_facts": [],
            "prohibited_claims": [],
            "eligible_context_ids": [],
            "expected_citations": [],
            "expected_generation_behavior": {"max_attempts": 0, "must_not_generate": True},
            "expected_provider_behavior": "not_called",
            "expected_error": {"code": "non-empty stable code", "safe_message": True},
            "rationale": validation_reason,
        }

    try:
        caller = get_identity(request.get("caller_id"))
    except IdentityError:
        return {
            "expected_http_status": 401,
            "expected_response_status": None,
            "expected_answer_meaning": None,
            "required_facts": [],
            "prohibited_claims": [],
            "eligible_context_ids": [],
            "expected_citations": [],
            "expected_generation_behavior": {"max_attempts": 0, "must_not_generate": True},
            "expected_provider_behavior": "not_called",
            "expected_error": {"code": "non-empty stable code", "safe_message": True},
            "rationale": "Missing or unknown caller IDs are rejected; tenant and role come only from lookup.",
        }

    if provider_event in {"timeout", "unavailable", "malformed"}:
        status = 503 if provider_event in {"timeout", "unavailable"} else 502
        return {
            "expected_http_status": status,
            "expected_response_status": None,
            "expected_answer_meaning": None,
            "required_facts": [],
            "prohibited_claims": [],
            "eligible_context_ids": [],
            "expected_citations": [],
            "expected_generation_behavior": {"max_attempts": 1, "must_not_generate": False, "no_retries": True},
            "expected_provider_behavior": provider_event,
            "expected_error": {"code": "non-empty stable code", "safe_message": True},
            "rationale": f"Provider {provider_event} has contract-mandated error mapping.",
        }

    eligible = eligible_policies(policies, caller, request["as_of"])
    intent = classify_question(request["question"])
    relevant = relevant_policies(intent, eligible)
    relevant_ids = [p.id for p in relevant]

    prohibited = [
        "claim_approval",
        "payment_guarantee",
        "remaining_balance",
        "financial_action_completed",
        "unauthorized_tenant_switch",
    ]

    if not relevant:
        return {
            "expected_http_status": 200,
            "expected_response_status": "INSUFFICIENT_EVIDENCE",
            "expected_answer_meaning": None,
            "required_facts": [],
            "prohibited_claims": prohibited,
            "eligible_context_ids": [],
            "expected_citations": [],
            "expected_generation_behavior": {"max_attempts": 1, "must_not_generate": False, "note": "Contract does not require a model call when no evidence exists."},
            "expected_provider_behavior": "success_or_not_called",
            "expected_error": None,
            "rationale": "No relevant eligible policy evidence exists; company policy cannot be supplied from general knowledge.",
        }

    # Contradictory simultaneously applicable policies: no precedence rule, so return CONFLICT.
    passages = {p.passage for p in relevant}
    if len(relevant) > 1 and len(passages) > 1:
        return {
            "expected_http_status": 200,
            "expected_response_status": "CONFLICT",
            "expected_answer_meaning": None,
            "required_facts": [],
            "prohibited_claims": prohibited,
            "eligible_context_ids": relevant_ids,
            "expected_citations": relevant_ids,
            "expected_generation_behavior": {"max_attempts": 1, "must_not_generate": False},
            "expected_provider_behavior": "success_or_not_called",
            "expected_error": None,
            "rationale": "Multiple contradictory simultaneously applicable policies exist and no precedence rule is supplied.",
        }

    return {
        "expected_http_status": 200,
        "expected_response_status": "ANSWERED",
        "expected_answer_meaning": f"Answer the {intent.replace('_', ' ')} using the eligible policy evidence.",
        "required_facts": _required_facts(intent, relevant),
        "prohibited_claims": prohibited,
        "eligible_context_ids": relevant_ids,
        "expected_citations": relevant_ids,
        "expected_generation_behavior": {"max_attempts": 1, "must_not_generate": False, "no_retries": True},
        "expected_provider_behavior": "success_or_not_called",
        "expected_error": None,
        "rationale": "Exactly one relevant eligible policy supports the answer.",
    }
