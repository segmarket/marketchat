"""Testes de interceptação de áudio/vídeo no webhook."""

from unittest import mock

import pytest

from apps.integrations.services.message_media import (
    OUT_OF_CONTEXT_IMAGE_REPLY,
    UNSUPPORTED_MEDIA_REPLY,
    detect_media_kind,
    event_is_unsupported_media,
)
from apps.integrations.services.webhook_handlers import handle_evolution_webhook
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent, parse_evolution_payload
from apps.residents.models import ChatSession
from apps.tenants.context import tenant_scope
from tests.factories import ResidentFactory, TenantFactory, WhatsappInstanceFactory


def _audio_event(phone: str = "5511999887766") -> EvolutionWebhookEvent:
    raw = {
        "message": {
            "audioMessage": {
                "ptt": True,
                "mimetype": "audio/ogg; codecs=opus",
            }
        }
    }
    return EvolutionWebhookEvent(
        event_type="MESSAGE",
        instance_key="inst",
        connection_state="",
        remote_jid=f"{phone}@s.whatsapp.net",
        message_id="msg-audio-1",
        from_me=False,
        message_text="",
        message_kind="ptt",
        raw_message=raw,
    )


@pytest.mark.django_db
def test_detect_media_kind_audio_ptt():
    data = {"message": {"audioMessage": {"ptt": True}}}
    assert detect_media_kind(data) == "ptt"


@pytest.mark.django_db
def test_detect_media_kind_image_not_blocked():
    data = {"message": {"imageMessage": {"mimetype": "image/jpeg"}}}
    assert detect_media_kind(data) is None


@pytest.mark.django_db
def test_audio_message_is_rejected_gracefully():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSession.objects.create(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.QUANTITY_SELECTION,
    )

    event = _audio_event(resident.phone_number)
    assert event_is_unsupported_media(
        message_kind=event.message_kind,
        raw_message=event.raw_message,
    )

    with (
        mock.patch("apps.integrations.services.webhook_handlers.send_whatsapp_reply") as send_reply,
        mock.patch("apps.integrations.services.webhook_handlers.classify_user_intent") as classify,
        mock.patch("apps.integrations.services.webhook_handlers.run_chatbot_flow") as run_flow,
        mock.patch("apps.integrations.services.webhook_handlers.process_cart_flow") as cart_flow,
    ):
        with tenant_scope(tenant.id):
            handle_evolution_webhook(event, instance)

    send_reply.assert_called_once_with(
        instance,
        resident.phone_number,
        UNSUPPORTED_MEDIA_REPLY,
        record_context=False,
    )
    assert "Ainda não consigo ouvir" in send_reply.call_args[0][2]
    classify.assert_not_called()
    run_flow.assert_not_called()
    cart_flow.assert_not_called()

    session.refresh_from_db()
    assert session.state == ChatSession.State.QUANTITY_SELECTION


@pytest.mark.django_db
def test_video_message_is_rejected():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    ResidentFactory(tenant=tenant, phone_number="5511888776655")

    body = {
        "event": "MESSAGE",
        "instance": "inst",
        "data": {
            "key": {
                "remoteJid": "5511888776655@s.whatsapp.net",
                "id": "msg-video",
                "fromMe": False,
            },
            "message": {"videoMessage": {"mimetype": "video/mp4"}},
        },
    }
    event = parse_evolution_payload(body)
    assert event is not None
    assert event.message_kind == "video"

    with mock.patch("apps.integrations.services.webhook_handlers.send_whatsapp_reply") as send_reply:
        with tenant_scope(tenant.id):
            handle_evolution_webhook(event, instance)

    send_reply.assert_called_once()


def _image_event(phone: str = "5511999887766") -> EvolutionWebhookEvent:
    raw = {"message": {"imageMessage": {"mimetype": "image/jpeg"}}}
    return EvolutionWebhookEvent(
        event_type="MESSAGE",
        instance_key="inst",
        connection_state="",
        remote_jid=f"{phone}@s.whatsapp.net",
        message_id="msg-image-1",
        from_me=False,
        message_text="",
        message_kind="image",
        raw_message=raw,
    )


@pytest.mark.django_db
def test_image_rejected_outside_checkout():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSession.objects.create(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
    )

    event = _image_event(resident.phone_number)

    with (
        mock.patch("apps.integrations.services.webhook_handlers.send_whatsapp_reply") as send_reply,
        mock.patch("apps.integrations.services.webhook_handlers.classify_user_intent") as classify,
        mock.patch("apps.chatbot.services.intent_classifier.classify_intent") as classify_intent,
        mock.patch("apps.integrations.services.webhook_handlers.run_chatbot_flow") as run_flow,
        mock.patch("apps.integrations.services.webhook_handlers.process_cart_flow") as cart_flow,
    ):
        with tenant_scope(tenant.id):
            handle_evolution_webhook(event, instance)

    send_reply.assert_called_once_with(
        instance,
        resident.phone_number,
        OUT_OF_CONTEXT_IMAGE_REPLY,
        record_context=False,
    )
    assert "Ainda não consigo analisar imagens soltas" in send_reply.call_args[0][2]
    assert "descreva o que aconteceu em texto" in send_reply.call_args[0][2]
    classify.assert_not_called()
    classify_intent.assert_not_called()
    run_flow.assert_not_called()
    cart_flow.assert_not_called()

    session.refresh_from_db()
    assert session.state == ChatSession.State.IDLE


@pytest.mark.django_db
def test_image_rejected_in_cart_review_keeps_state():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511888776655")
    session = ChatSession.objects.create(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.CART_REVIEW,
    )

    event = _image_event(resident.phone_number)

    with mock.patch("apps.integrations.services.webhook_handlers.send_whatsapp_reply"):
        with tenant_scope(tenant.id):
            handle_evolution_webhook(event, instance)

    session.refresh_from_db()
    assert session.state == ChatSession.State.CART_REVIEW
