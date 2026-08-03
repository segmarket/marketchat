from decimal import Decimal

import pytest

from apps.chatbot.models import ChatMessageLog
from apps.financial.models import LedgerTransaction, Wallet
from apps.lgpd.services.anonymization import (
    ResidentAnonymizationError,
    anonymize_resident_by_phone,
    build_anonymous_phone_token,
)
from apps.residents.models import ChatMessage, ChatSession, Resident
from apps.sales.models import Cart
from tests.factories import CartFactory, MarketFactory, ResidentFactory, TenantFactory


def test_anonymous_phone_token_fits_chat_session_and_resident():
    token = build_anonymous_phone_token(tenant_id=1, phone_number="5511999887766")
    session_max = ChatSession._meta.get_field("phone_number").max_length
    resident_max = Resident._meta.get_field("phone_number").max_length
    assert token.startswith("anon_")
    assert len(token) <= session_max
    assert len(token) <= resident_max
    # Compatível com varchar(32) legado da sessão em ambientes ainda sem migration.
    assert len(token) <= 32


@pytest.mark.django_db
def test_anonymize_resident_preserves_ledger():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market, phone_number="5511999887766", name="Ana")
    cart = CartFactory(tenant=tenant, resident=resident, status=Cart.Status.COMPLETED)
    wallet, _ = Wallet.objects.get_or_create(tenant=tenant)
    LedgerTransaction.objects.create(
        wallet=wallet,
        amount=Decimal("10.00"),
        entry_type=LedgerTransaction.EntryType.INFLOW,
        description="Venda teste",
        external_id="pay_lgpd_1",
        cart=cart,
    )

    anonymize_resident_by_phone(tenant_id=tenant.id, phone="11999887766")

    resident.refresh_from_db()
    assert resident.is_anonymized is True
    assert resident.is_active is False
    assert resident.name == "Usuário Anonimizado"
    assert resident.phone_number.startswith("anon_")
    assert LedgerTransaction.objects.filter(cart=cart).count() == 1
    assert Cart.objects.filter(pk=cart.pk).exists()


@pytest.mark.django_db
def test_anonymize_redacts_chat_data():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market, phone_number="5511888777666", name="Bob")
    session = ChatSession.objects.create(
        tenant=tenant,
        phone_number="5511888777666",
        state=ChatSession.State.IDLE,
        temporary_name="Bob Temp",
    )
    ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, content="lista de compras")
    ChatMessageLog.objects.create(
        tenant=tenant,
        session=session,
        resident=resident,
        market=market,
        message_text="oi",
        direction=ChatMessageLog.Direction.INBOUND,
    )

    anonymize_resident_by_phone(tenant_id=tenant.id, phone="11888777666")

    session.refresh_from_db()
    assert session.temporary_name == ""
    assert session.phone_number.startswith("anon_")
    assert ChatMessage.objects.filter(session=session).first().content.startswith("[conteúdo removido")
    log = ChatMessageLog.objects.filter(resident=resident).first()
    assert log is not None
    assert log.message_text.startswith("[conteúdo removido")


@pytest.mark.django_db
def test_same_phone_can_register_after_anonymization():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market, phone_number="5511777666555", name="Carla")
    anonymize_resident_by_phone(tenant_id=tenant.id, phone="11777666555")

    new_resident = Resident.objects.create(
        tenant=tenant,
        phone_number="5511777666555",
        name="Carla Nova",
        market=market,
    )
    assert new_resident.pk != resident.pk
    assert new_resident.is_anonymized is False


@pytest.mark.django_db
def test_anonymize_twice_raises():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    ResidentFactory(tenant=tenant, market=market, phone_number="5511666555444", name="Dan")
    anonymize_resident_by_phone(tenant_id=tenant.id, phone="11666555444")

    with pytest.raises(ResidentAnonymizationError):
        anonymize_resident_by_phone(tenant_id=tenant.id, phone="11666555444")
