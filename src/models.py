from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Identity:
    caller_id: str
    tenant: str
    role: str


@dataclass(frozen=True)
class Policy:
    id: str
    tenant: str
    role: str
    state: str
    effective_from: str
    effective_to: str
    passage: str


CheckResult = Dict[str, Any]


def check_result(rule: str, expected: Any, observed: Any, verdict: str, reason: str) -> CheckResult:
    return {
        "rule": rule,
        "expected": expected,
        "observed": observed,
        "verdict": verdict,
        "reason": reason,
    }
