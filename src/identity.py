from __future__ import annotations

from typing import Optional

from .models import Identity


_IDENTITIES = {
    "atlas-employee-01": Identity("atlas-employee-01", "Atlas", "employee"),
    "atlas-contractor-01": Identity("atlas-contractor-01", "Atlas", "contractor"),
    "boreal-employee-01": Identity("boreal-employee-01", "Boreal", "employee"),
}


class IdentityError(ValueError):
    """Raised when caller identity is missing or unknown."""


def get_identity(caller_id: Optional[str]) -> Identity:
    if not caller_id or caller_id not in _IDENTITIES:
        raise IdentityError("missing or unknown caller identity")
    return _IDENTITIES[caller_id]


def supported_identities() -> dict[str, Identity]:
    return dict(_IDENTITIES)
