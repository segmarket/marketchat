from django.db import models
from django.db.models import QuerySet

from apps.tenants.context import get_current_tenant_id


class TenantQuerySet(QuerySet):
    """QuerySet que filtra por tenant quando o contexto define tenant_id."""

    def for_current_tenant(self) -> "TenantQuerySet":
        tid = get_current_tenant_id()
        if tid is None:
            return self.none()
        return self.filter(tenant_id=tid)

    def all_tenants(self) -> "TenantQuerySet":
        """Consultas administrativas / webhooks: sem filtro automático."""
        return self._clone()


class TenantManager(models.Manager):
    def get_queryset(self) -> TenantQuerySet:
        qs = TenantQuerySet(self.model, using=self._db)
        tid = get_current_tenant_id()
        if tid is not None and hasattr(self.model, "tenant_id"):
            return qs.filter(tenant_id=tid)
        return qs

    def all_tenants(self) -> TenantQuerySet:
        return TenantQuerySet(self.model, using=self._db)
