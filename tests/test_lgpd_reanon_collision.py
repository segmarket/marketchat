import pytest

from apps.lgpd.services.anonymization import (
    anonymize_resident_by_phone,
    perform_resident_anonymization,
)
from apps.residents.models import ChatSession, Resident
from tests.factories import MarketFactory, ResidentFactory, TenantFactory


@pytest.mark.django_db
def test_reanonymize_same_phone_clears_previous_session():
    """Mesmo telefone pode ser anonimizado de novo após re-cadastro."""
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    phone = "5511999000111"
    ResidentFactory(tenant=tenant, market=market, phone_number=phone, name="A")
    first_session = ChatSession.objects.create(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.IDLE,
    )
    anonymize_resident_by_phone(tenant_id=tenant.id, phone=phone)
    first_session.refresh_from_db()
    first_anon_phone = first_session.phone_number
    first_session_id = first_session.pk

    r2 = Resident.objects.create(
        tenant=tenant,
        phone_number=phone,
        name="B",
        market=market,
    )
    second_session = ChatSession.objects.create(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.IDLE,
    )

    perform_resident_anonymization(r2)

    r2.refresh_from_db()
    second_session.refresh_from_db()
    assert r2.is_anonymized is True
    assert second_session.phone_number == first_anon_phone
    assert not ChatSession.objects.filter(pk=first_session_id).exists()
    assert (
        ChatSession.objects.filter(
            tenant=tenant,
            phone_number=first_anon_phone,
        ).count()
        == 1
    )
