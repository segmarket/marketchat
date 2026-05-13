from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.tenants.models import DemoNote
from apps.tenants.serializers import DemoNoteSerializer


class DemoNoteViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Lista e cria notas de exemplo escopadas ao tenant do usuário."""

    serializer_class = DemoNoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DemoNote.objects.order_by("-created_at")

    def perform_create(self, serializer):
        tenant_id = self.request.user.tenant_id
        if tenant_id is None:
            raise ValidationError("Usuário sem tenant associado.")
        serializer.save(tenant_id=tenant_id)
