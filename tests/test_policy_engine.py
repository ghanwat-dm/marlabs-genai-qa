from dataclasses import replace

from src.identity import get_identity
from src.policy_engine import is_policy_eligible, load_policies, policy_by_id


POLICIES = load_policies()
ATLAS_EMPLOYEE = get_identity("atlas-employee-01")
ATLAS_CONTRACTOR = get_identity("atlas-contractor-01")


def p(pid):
    return policy_by_id(POLICIES, pid)


def test_valid_tenant():
    assert is_policy_eligible(p("P02"), ATLAS_EMPLOYEE, "2026-09-21")


def test_wrong_tenant():
    assert not is_policy_eligible(p("P06"), ATLAS_EMPLOYEE, "2026-09-21")


def test_valid_role():
    assert is_policy_eligible(p("P05"), ATLAS_CONTRACTOR, "2026-09-21")


def test_wrong_role():
    assert not is_policy_eligible(p("P05"), ATLAS_EMPLOYEE, "2026-09-21")


def test_approved_policy():
    assert is_policy_eligible(p("P02"), ATLAS_EMPLOYEE, "2026-09-21")


def test_draft_policy():
    assert not is_policy_eligible(p("P04"), ATLAS_EMPLOYEE, "2026-09-21")


def test_effective_from_boundary_is_inclusive():
    assert is_policy_eligible(p("P02"), ATLAS_EMPLOYEE, "2026-06-01")


def test_effective_to_boundary_is_exclusive():
    assert not is_policy_eligible(p("P01"), ATLAS_EMPLOYEE, "2026-06-01")


def test_expired_policy():
    assert not is_policy_eligible(p("P01"), ATLAS_EMPLOYEE, "2026-09-21")


def test_future_policy():
    assert not is_policy_eligible(p("P03"), ATLAS_EMPLOYEE, "2026-09-21")
