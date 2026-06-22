"""Authorization dependencies.

Routes/services should depend on these central gates instead of scattering role
checks. Billing/feature gates are added in Slice 16.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends

from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.services.authz import Permission, RBACService

_CURRENT_PRINCIPAL_DEP = Depends(current_principal)
_RBAC_SERVICE_DEP = Depends(lambda: RBACService())


def require_permission(permission: Permission) -> Callable[..., CurrentPrincipal]:
    def _dependency(
        principal: CurrentPrincipal = _CURRENT_PRINCIPAL_DEP,
        rbac: RBACService = _RBAC_SERVICE_DEP,
    ) -> CurrentPrincipal:
        rbac.require(principal, permission)
        return principal

    return _dependency
