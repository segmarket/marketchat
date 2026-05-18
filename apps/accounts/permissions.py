from rest_framework.permissions import BasePermission

from apps.accounts.services.tenant_access import user_can_manage_tenant


class IsTenantAdmin(BasePermission):
    """Administrador da empresa (is_tenant_admin) ou superusuário vinculado a um tenant."""

    message = "Apenas administradores da empresa podem acessar este recurso."

    def has_permission(self, request, view) -> bool:
        return user_can_manage_tenant(request.user)
