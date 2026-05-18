from django.db import models
from django.db.models import Q

from apps.tenants.models import TenantAwareModel


class ChatbotWorkflow(TenantAwareModel):
    """Fluxo visual do chatbot WhatsApp (React Flow JSON por tenant)."""

    name = models.CharField(max_length=255, default="Fluxo principal")
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False, db_index=True)
    system_key = models.CharField(max_length=64, blank=True, default="")
    flow_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
            models.Index(fields=["tenant", "is_system"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "system_key"],
                condition=Q(system_key__gt=""),
                name="uniq_tenant_system_workflow_key",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} (tenant={self.tenant_id})"
