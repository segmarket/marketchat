"""Persistência de sessões de preview de importação."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.products.models import ProductImportSession
from apps.products.services.import_compare import PreviewResult

IMPORT_SESSION_TTL = timedelta(hours=2)


def create_import_session(tenant_id: int, preview: PreviewResult) -> ProductImportSession:
    return ProductImportSession.objects.create(
        tenant_id=tenant_id,
        payload=preview.operations,
        new_count=preview.new_count,
        updated_count=preview.updated_count,
        expires_at=timezone.now() + IMPORT_SESSION_TTL,
    )


def get_valid_session(tenant_id: int, token) -> ProductImportSession:
    from apps.products.services.import_apply import ImportApplyError

    try:
        session = ProductImportSession.objects.get(tenant_id=tenant_id, token=token)
    except ProductImportSession.DoesNotExist as exc:
        raise ImportApplyError("Token de importação inválido.") from exc

    if session.confirmed_at is not None:
        raise ImportApplyError("Esta importação já foi confirmada.")
    if session.expires_at <= timezone.now():
        raise ImportApplyError("O token de importação expirou. Faça o preview novamente.")
    return session
