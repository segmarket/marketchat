from unittest import mock

import pytest

from apps.residents.models import ChatSession
from apps.sales.services.handlers.payment import (
    HUMAN_QUEUE_PURCHASE_ESCAPE_MESSAGE,
    MACHINE_BACKUP_SALE_MESSAGE,
    start_maquininha_backup_sale,
    try_escape_human_queue_for_purchase,
)
from apps.tenants.context import tenant_scope
from tests.factories import (
    ChatSessionFactory,
    MarketFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)


@pytest.mark.django_db
def test_start_maquininha_backup_sale_opens_product_search():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant, name="Portal")
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511999000011"
    resident = ResidentFactory(
        tenant=tenant, phone_number=phone, market=market, name="Ana"
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.IDLE,
    )

    with (
        mock.patch(
            "apps.sales.services.handlers.payment.notify_owner_support_issue"
        ),
        mock.patch(
            "apps.sales.services.handlers.payment.create_critical_panel_notification"
        ),
        mock.patch(
            "apps.sales.services.handlers.payment.send_whatsapp_reply"
        ) as send_sale,
        mock.patch("apps.sales.services.handlers.payment.append_assistant_message"),
        tenant_scope(tenant.id),
    ):
        start_maquininha_backup_sale(
            instance=instance,
            tenant_id=tenant.id,
            phone=phone,
            resident=resident,
            session=session,
            message="maquina fora",
        )
        session.refresh_from_db()

    assert session.state == ChatSession.State.PRODUCT_SEARCH
    assert session.active_cart_id is not None
    assert send_sale.call_args[0][2] == MACHINE_BACKUP_SALE_MESSAGE


@pytest.mark.django_db
def test_escape_human_queue_on_purchase_keywords():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511999000033"
    resident = ResidentFactory(
        tenant=tenant, phone_number=phone, market=market, name="Bruno"
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.WAITING_FOR_HUMAN,
        is_bot_active=False,
    )

    with (
        mock.patch(
            "apps.sales.services.handlers.payment.send_whatsapp_reply"
        ) as send,
        mock.patch("apps.sales.services.handlers.payment.append_assistant_message"),
        tenant_scope(tenant.id),
    ):
        ok = try_escape_human_queue_for_purchase(
            instance=instance,
            phone=phone,
            text="quero comprar com pix",
            session=session,
            resident=resident,
        )

    assert ok is True
    session.refresh_from_db()
    assert session.is_bot_active is True
    assert session.state == ChatSession.State.PRODUCT_SEARCH
    assert session.active_cart_id is not None
    assert send.call_args[0][2] == HUMAN_QUEUE_PURCHASE_ESCAPE_MESSAGE


@pytest.mark.django_db
def test_escape_human_queue_silent_without_keywords():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511999000044"
    resident = ResidentFactory(
        tenant=tenant, phone_number=phone, market=market, name="Carla"
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.WAITING_FOR_HUMAN,
        is_bot_active=False,
    )

    with tenant_scope(tenant.id):
        ok = try_escape_human_queue_for_purchase(
            instance=instance,
            phone=phone,
            text="obrigado, aguardo",
            session=session,
            resident=resident,
        )

    assert ok is False
    session.refresh_from_db()
    assert session.state == ChatSession.State.WAITING_FOR_HUMAN
    assert session.is_bot_active is False
