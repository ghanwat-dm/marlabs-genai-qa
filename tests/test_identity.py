import pytest

from src.identity import IdentityError, get_identity


def test_supported_callers():
    assert get_identity("atlas-employee-01").tenant == "Atlas"
    assert get_identity("atlas-employee-01").role == "employee"
    assert get_identity("atlas-contractor-01").role == "contractor"
    assert get_identity("boreal-employee-01").tenant == "Boreal"


@pytest.mark.parametrize("caller_id", [None, "", "unknown-01"])
def test_missing_or_unknown_callers_rejected(caller_id):
    with pytest.raises(IdentityError):
        get_identity(caller_id)
