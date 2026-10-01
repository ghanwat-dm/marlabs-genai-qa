from __future__ import annotations

from typing import Any, Iterable

from .models import Identity, Policy
from .policy_engine import is_policy_eligible, policy_by_id
from .semantic_checker import extract_inr_amounts


def citation_chunk_exists(citation: dict[str, Any], policies: Iterable[Policy]) -> bool:
    return policy_by_id(policies, citation.get("chunk_id", "")) is not None


def citation_is_eligible(citation: dict[str, Any], policies: Iterable[Policy], caller: Identity, as_of: str) -> bool:
    policy = policy_by_id(policies, citation.get("chunk_id", ""))
    return bool(policy and is_policy_eligible(policy, caller, as_of))


def citation_quote_matches(citation: dict[str, Any], policies: Iterable[Policy]) -> bool:
    policy = policy_by_id(policies, citation.get("chunk_id", ""))
    return bool(policy and citation.get("quote") == policy.passage)


def citation_supports_amounts(answer: str | None, citations: list[dict[str, Any]]) -> bool:
    answer_amounts = extract_inr_amounts(answer)
    if not answer_amounts:
        return True
    quote_amounts = set()
    for citation in citations:
        quote_amounts |= extract_inr_amounts(citation.get("quote"))
    return answer_amounts.issubset(quote_amounts)
