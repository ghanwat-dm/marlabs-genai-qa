from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Iterable, List

from .models import Identity, Policy


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICIES = ROOT / "data" / "policies.json"


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def load_policies(path: Path | str = DEFAULT_POLICIES) -> List[Policy]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Policy(**item) for item in raw]


def is_policy_eligible(policy: Policy, caller: Identity, as_of: str) -> bool:
    when = parse_date(as_of)
    return (
        policy.state == "Approved"
        and policy.tenant == caller.tenant
        and policy.role == caller.role
        and parse_date(policy.effective_from) <= when
        and when < parse_date(policy.effective_to)
    )


def eligible_policies(policies: Iterable[Policy], caller: Identity, as_of: str) -> List[Policy]:
    return [p for p in policies if is_policy_eligible(p, caller, as_of)]


def policy_by_id(policies: Iterable[Policy], chunk_id: str) -> Policy | None:
    return next((p for p in policies if p.id == chunk_id), None)
