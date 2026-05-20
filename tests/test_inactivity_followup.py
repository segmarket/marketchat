from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from apps.chatbot.services.inactivity_followup import (
    build_inactivity_closing_message,
    process_inactivity_followup_for_session,
    process_inactivity_followups,
    queryset_stale_sessions,
)
from apps.residents.models import ChatSession
from apps.sales.models import Cart
from tests.factories import (
    CartFactory,
    ChatSessionFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)


@pytest.mark.django_db
def test_build_inactivity_closing_message_uses_resident_and_market():
    text = build_inactivity_closing_message(
        resident_name="Maria Silva",
        market_name="Condomínio Sol",
    )
    assert "Maria Silva" in text
    assert "Condomínio Sol" in text
    assert "chamado/feedback" in text


@pytest.mark.django_db
def test_stale_session_window_excludes_recent_and_very_old():
    tenant = TenantFactory()
    recent = ChatSessionFactory(
        tenant=tenant,
        state=ChatSession.State.IDLE,
        inactivity_notified=False,
    )
    ChatSession.objects.filter(pk=recent.pk).update(
        last_activity_at=timezone.now() - timedelta(minutes=2),
    )

    in_window = ChatSessionFactory(
        tenant=tenant,
        phone_number="5511999000001",
        state=ChatSession.State.IDLE,
        inactivity_notified=False,
    )
    ChatSession.objects.filter(pk=in_window.pk).update(
        last_activity_at=timezone.now() - timedelta(minutes=6),
    )

    too_old = ChatSessionFactory(
        tenant=tenant,
        phone_number="5511999000002",
        state=ChatSession.State.IDLE,
        inactivity_notified=False,
    )
    ChatSession.objects.filter(pk=too_old.pk).update(
        last_activity_at=timezone.now() - timedelta(minutes=20),
    )

    ids = set(queryset_stale_sessions().values_list("pk", flat=True))
    assert in_window.pk in ids
    assert recent.pk not in ids
    assert too_old.pk not in ids


@pytest.mark.django_db
def test_inactivity_followup_sends_whatsapp_and_resets_session():
    tenant = TenantFactory()
    WhatsappInstanceFactory(tenant=tenant, is_active=True)
    resident = ResidentFactory(tenant=tenant, name="João Teste")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
        inactivity_notified=False,
    )
    cart = CartFactory(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.OPEN,
    )
    session.active_cart = cart
    session.pending_product_id = None
    session.save(update_fields=["active_cart"])

    ChatSession.objects.filter(pk=session.pk).update(
        last_activity_at=timezone.now() - timedelta(minutes=6),
    )
    session.refresh_from_db()

    with mock.patch(
        "apps.chatbot.services.inactivity_followup.send_whatsapp_reply",
    ) as send_reply:
        sent = process_inactivity_followup_for_session(session)

    assert sent is True
    send_reply.assert_called_once()
    args, kwargs = send_reply.call_args
    assert resident.phone_number in args[1] or args[1] == resident.phone_number
    assert "João" in args[2]
    assert "João Teste" not in args[2]
    assert kwargs.get("session") == session

    session.refresh_from_db()
    assert session.state == ChatSession.State.IDLE
    assert session.active_cart_id is None
    assert session.pending_product_id is None
    assert session.inactivity_notified is False

    cart.refresh_from_db()
    assert cart.status == Cart.Status.CANCELLED


@pytest.mark.django_db
def test_inactivity_skips_awaiting_payment_cart():
    tenant = TenantFactory()
    WhatsappInstanceFactory(tenant=tenant, is_active=True)
    resident = ResidentFactory(tenant=tenant)
    cart = CartFactory(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.AWAITING_PAYMENT,
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
        active_cart=cart,
        inactivity_notified=False,
    )
    ChatSession.objects.filter(pk=session.pk).update(
        last_activity_at=timezone.now() - timedelta(minutes=6),
    )

    with mock.patch(
        "apps.chatbot.services.inactivity_followup.send_whatsapp_reply",
    ) as send_reply:
        result = process_inactivity_followups()

    assert result.sent == 0
    send_reply.assert_not_called()


@pytest.mark.django_db
def test_management_command_logs_summary(capsys):
    tenant = TenantFactory()
    WhatsappInstanceFactory(tenant=tenant, is_active=True)
    resident = ResidentFactory(tenant=tenant)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
    )
    ChatSession.objects.filter(pk=session.pk).update(
        last_activity_at=timezone.now() - timedelta(minutes=6),
    )

    with mock.patch(
        "apps.chatbot.services.inactivity_followup.send_whatsapp_reply",
    ):
        from django.core.management import call_command

        call_command("send_inactivity_followups")

    captured = capsys.readouterr()
    assert "Encerradas por inatividade: 1" in captured.out
