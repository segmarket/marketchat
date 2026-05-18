"""Regras de acesso por tenant (empresa do cliente)."""

from __future__ import annotations

from django.contrib.auth import get_user_model

User = get_user_model()


def user_can_manage_tenant(user: User) -> bool:
    """Pode gerenciar integrações e dados da empresa no app."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    try:
        db_user = User.objects.get(pk=user.pk)
    except (User.DoesNotExist, TypeError, ValueError):
        return False
    if db_user.is_tenant_admin and db_user.tenant_id:
        return True
    if db_user.is_superuser and db_user.tenant_id:
        return True
    return False


def user_access_flags(user: User) -> dict[str, bool]:
    try:
        db_user = User.objects.get(pk=user.pk)
    except (User.DoesNotExist, TypeError, ValueError):
        return {
            "is_tenant_admin": False,
            "can_manage_integrations": False,
            "is_platform_superuser": False,
            "has_tenant": False,
        }
    return {
        "is_tenant_admin": bool(db_user.is_tenant_admin),
        "can_manage_integrations": user_can_manage_tenant(db_user),
        "is_platform_superuser": bool(db_user.is_superuser),
        "has_tenant": bool(db_user.tenant_id),
    }
