"""Suíte FSM + ocorrências: tags da IA, estados, carrinho e anti-troll."""

from __future__ import annotations

from contextlib import ExitStack
from datetime import timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.residents.models import ChatMessage, ChatSession
from apps.sales.models import Cart, CartItem
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent
from apps.sales.services.active_bot_router import route_idle_message
from apps.sales.services.cart_flow import process_cart_flow
from apps.sales.services.intent_gatekeeper import COMPLAINT, COURTESY_FAREWELL, GENERAL
from apps.sales.services.owner_alert import SUPPORT_RESIDENT_MESSAGE
from apps.sales.services.product_search import ASK_PRODUCT_MESSAGE
from apps.sales.services.pix_hurry_cart import parse_hurry_line_items
from apps.tenants.context import tenant_scope
from tests.factories import (
    ChatSessionFactory,
    MarketFactory,
    ProductFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)

_TAG_FORBIDDEN = ("[ALERTA_", "[SOLICITACAO_", "[AJUDA_", "[FEEDBACK_")


@pytest.fixture
def fsm_tenant():
    return TenantFactory()


@pytest.fixture
def fsm_market(fsm_tenant):
    return MarketFactory(tenant=fsm_tenant)


@pytest.fixture
def fsm_resident(fsm_tenant, fsm_market):
    return ResidentFactory(tenant=fsm_tenant, market=fsm_market, name="João Silva")


@pytest.fixture
def fsm_instance(fsm_tenant):
    return WhatsappInstanceFactory(tenant=fsm_tenant)


@pytest.fixture
def fsm_session(fsm_tenant, fsm_resident):
    return ChatSessionFactory(
        tenant=fsm_tenant,
        phone_number=fsm_resident.phone_number,
        state=ChatSession.State.IDLE,
        active_cart=None,
    )


@pytest.fixture
def fsm_catalog(fsm_tenant):
    coca = ProductFactory(
        tenant=fsm_tenant,
        sku="COCA-350",
        name="Coca Cola Lata 350ml",
        price=Decimal("5.50"),
    )
    doritos = ProductFactory(
        tenant=fsm_tenant,
        sku="DOR-140",
        name="Doritos 140g",
        price=Decimal("11.90"),
    )
    return {"coca": coca, "doritos": doritos}


def _whatsapp_body(send_mock: mock.Mock) -> str:
    assert send_mock.called
    return send_mock.call_args[0][2]


def _assert_no_tags_in_outbound(send_mock: mock.Mock) -> None:
    body = _whatsapp_body(send_mock)
    for fragment in _TAG_FORBIDDEN:
        assert fragment not in body


def _assert_assistant_history_clean(session: ChatSession) -> None:
    last = (
        ChatMessage.objects.filter(session=session, role=ChatMessage.Role.ASSISTANT)
        .order_by("-id")
        .first()
    )
    assert last is not None
    for fragment in _TAG_FORBIDDEN:
        assert fragment not in last.content


def _run_idle_router(
    *,
    session: ChatSession,
    resident,
    instance,
    tenant_id: int,
    text: str,
    gatekeeper_intent: str = GENERAL,
    ai_reply: str,
    on_purchase=None,
    extra_patches: list | None = None,
) -> mock.Mock:
    if on_purchase is None:
        on_purchase = mock.Mock(return_value=False)

    send_mock = mock.Mock()
    with ExitStack() as stack:
        stack.enter_context(
            mock.patch(
                "apps.sales.services.active_bot_router.classify_user_intent",
                return_value=gatekeeper_intent,
            )
        )
        stack.enter_context(
            mock.patch(
                "apps.sales.services.active_bot_router.complete_with_session_history",
                return_value=ai_reply,
            )
        )
        stack.enter_context(
            mock.patch(
                "apps.sales.services.active_bot_router.send_whatsapp_reply",
                send_mock,
            )
        )
        stack.enter_context(
            mock.patch(
                "apps.sales.services.availability_handler.handle_availability_question",
                return_value=False,
            )
        )
        for patcher in extra_patches or []:
            stack.enter_context(patcher)

        route_idle_message(
            tenant_id=tenant_id,
            instance=instance,
            phone=resident.phone_number,
            resident=resident,
            session=session,
            message=text,
            on_purchase=on_purchase,
        )

    return send_mock


def test_parse_hurry_line_items_extracts_quantities():
    items = parse_hurry_line_items(
        "Tô com pressa, peguei 3 cocas e 1 doritos, manda o pix"
    )
    assert (3, "cocas") in [(q, t.lower()) for q, t in items] or any(
        q == 3 and "coca" in t.lower() for q, t in items
    )
    assert any(q == 1 and "dorito" in t.lower() for q, t in items)


# --- Infraestrutura e maquininha ---


@pytest.mark.django_db
def test_infra_issue_escapes_product_search(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
):
    phrase = "A Luz de entrada esta queimada"
    session = ChatSessionFactory(
        tenant=fsm_tenant,
        phone_number=fsm_resident.phone_number,
        state=ChatSession.State.PRODUCT_SEARCH,
    )
    event = EvolutionWebhookEvent(
        event_type="MESSAGE",
        instance_key="inst",
        connection_state="",
        remote_jid=f"{fsm_resident.phone_number}@s.whatsapp.net",
        message_id="msg-infra-escape",
        from_me=False,
        message_text=phrase,
        message_kind="text",
    )

    owner_patch = mock.patch(
        "apps.chatbot.services.occurrence_dispatch.notify_owner_support_issue",
    )

    with ExitStack() as stack:
        classify_mock = stack.enter_context(
            mock.patch(
                "apps.sales.services.active_bot_router.classify_user_intent",
                return_value=GENERAL,
            )
        )
        stack.enter_context(
            mock.patch(
                "apps.sales.services.active_bot_router.complete_with_session_history",
                return_value="[ALERTA_INFRA] Obrigado por avisar, João! Já acionei a manutenção.",
            )
        )
        send_mock = stack.enter_context(
            mock.patch(
                "apps.sales.services.active_bot_router.send_whatsapp_reply",
                mock.Mock(),
            )
        )
        extract_mock = stack.enter_context(
            mock.patch("apps.sales.services.cart_flow.extract_product_term"),
        )
        stack.enter_context(owner_patch)

        with tenant_scope(fsm_tenant.id):
            handled = process_cart_flow(
                fsm_tenant.id,
                fsm_instance,
                fsm_resident.phone_number,
                event,
            )

    assert handled is True
    classify_mock.assert_called_once_with(
        phrase,
        tenant_id=fsm_tenant.id,
        phone=fsm_resident.phone_number,
    )
    extract_mock.assert_not_called()

    session.refresh_from_db()
    assert session.state == ChatSession.State.IDLE

    note = Notification.all_objects.filter(
        tenant=fsm_tenant,
        intent_type="ALERTA_INFRA",
    ).first()
    assert note is not None
    assert note.severity == Notification.Severity.CRITICAL

    _assert_no_tags_in_outbound(send_mock)
    _assert_assistant_history_clean(session)


@pytest.mark.django_db
def test_courtesy_intent_after_incident(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
    fsm_session,
):
    from apps.chatbot.services.chat_context_cache import append_message, clear_context

    clear_context(fsm_tenant.id, fsm_resident.phone_number)
    append_message(
        fsm_tenant.id,
        fsm_resident.phone_number,
        role="user",
        content="A luz de entrada esta queimada",
    )
    append_message(
        fsm_tenant.id,
        fsm_resident.phone_number,
        role="assistant",
        content=SUPPORT_RESIDENT_MESSAGE,
    )

    send_mock = mock.Mock()
    purchase_mock = mock.Mock(return_value=False)

    with (
        mock.patch(
            "apps.sales.services.active_bot_router.send_whatsapp_reply",
            send_mock,
        ),
        mock.patch(
            "apps.sales.services.cart_flow.extract_product_term",
        ) as extract_mock,
        mock.patch(
            "apps.sales.services.cart_flow.send_product_list",
        ) as send_list,
    ):
        route_idle_message(
            tenant_id=fsm_tenant.id,
            instance=fsm_instance,
            phone=fsm_resident.phone_number,
            resident=fsm_resident,
            session=fsm_session,
            message="Certo, obrigado!",
            on_purchase=purchase_mock,
        )

    purchase_mock.assert_not_called()
    extract_mock.assert_not_called()
    send_list.assert_not_called()

    fsm_session.refresh_from_db()
    assert fsm_session.state == ChatSession.State.IDLE

    body = _whatsapp_body(send_mock)
    assert "Por nada" in body
    assert ASK_PRODUCT_MESSAGE not in body
    assert "O que você deseja comprar" not in body

    clear_context(fsm_tenant.id, fsm_resident.phone_number)


@pytest.mark.django_db
def test_greeting_idle_welcome_message(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
    fsm_session,
):
    from apps.chatbot.services.chat_context_cache import clear_context

    clear_context(fsm_tenant.id, fsm_resident.phone_number)

    send_mock = mock.Mock()
    purchase_mock = mock.Mock(return_value=False)

    with (
        mock.patch(
            "apps.sales.services.main_menu.send_whatsapp_reply",
            send_mock,
        ),
        mock.patch(
            "apps.sales.services.cart_flow.extract_product_term",
        ) as extract_mock,
    ):
        route_idle_message(
            tenant_id=fsm_tenant.id,
            instance=fsm_instance,
            phone=fsm_resident.phone_number,
            resident=fsm_resident,
            session=fsm_session,
            message="Bom dia",
            on_purchase=purchase_mock,
        )

    purchase_mock.assert_not_called()
    extract_mock.assert_not_called()
    fsm_session.refresh_from_db()
    assert fsm_session.state == ChatSession.State.AWAITING_MAIN_MENU

    body = _whatsapp_body(send_mock)
    assert "Olá" in body
    assert "Fazer uma compra" in body
    assert "O que você precisa" not in body
    assert "Por nada" not in body


@pytest.mark.django_db
def test_geladeira_quebrada_triggers_infra_alert(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
    fsm_session,
):
    owner_patch = mock.patch(
        "apps.chatbot.services.occurrence_dispatch.notify_owner_support_issue",
    )
    send_mock = _run_idle_router(
        session=fsm_session,
        resident=fsm_resident,
        instance=fsm_instance,
        tenant_id=fsm_tenant.id,
        text="geladeira desligada",
        ai_reply="[ALERTA_INFRA] Obrigado por avisar, João! Já acionei a manutenção.",
        extra_patches=[owner_patch],
    )

    fsm_session.refresh_from_db()
    assert fsm_session.state == ChatSession.State.IDLE
    assert fsm_session.active_cart_id is None

    note = Notification.all_objects.filter(
        tenant=fsm_tenant,
        intent_type="ALERTA_INFRA",
    ).first()
    assert note is not None
    assert note.severity == Notification.Severity.CRITICAL

    _assert_no_tags_in_outbound(send_mock)
    _assert_assistant_history_clean(fsm_session)


@pytest.mark.django_db
def test_maquininha_fora_do_ar_starts_cart_flow(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
    fsm_session,
):
    owner_patch = mock.patch(
        "apps.chatbot.services.occurrence_dispatch.notify_owner_support_issue",
    )
    send_mock = _run_idle_router(
        session=fsm_session,
        resident=fsm_resident,
        instance=fsm_instance,
        tenant_id=fsm_tenant.id,
        text="maquininha deu erro",
        ai_reply=(
            "[ALERTA_MAQUININHA] Sem problemas! Vamos fechar por aqui no WhatsApp com Pix."
        ),
        extra_patches=[owner_patch],
    )

    fsm_session.refresh_from_db()
    assert fsm_session.state == ChatSession.State.PRODUCT_SEARCH
    assert fsm_session.active_cart_id is not None

    _assert_no_tags_in_outbound(send_mock)
    _assert_assistant_history_clean(fsm_session)


# --- Catálogo e qualidade ---


@pytest.mark.django_db
def test_produto_estragado_sanitary_alert(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
    fsm_session,
):
    owner_patch = mock.patch(
        "apps.chatbot.services.occurrence_dispatch.notify_owner_support_issue",
    )
    send_mock = _run_idle_router(
        session=fsm_session,
        resident=fsm_resident,
        instance=fsm_instance,
        tenant_id=fsm_tenant.id,
        text="iogurte estufado e estragado",
        gatekeeper_intent=COMPLAINT,
        ai_reply="[ALERTA_QUALIDADE] Poxa, João! Lamento pelo iogurte. Já avisei a equipe.",
        extra_patches=[owner_patch],
    )

    fsm_session.refresh_from_db()
    assert fsm_session.state == ChatSession.State.IDLE

    note = Notification.all_objects.filter(
        tenant=fsm_tenant,
        intent_type="ALERTA_QUALIDADE",
    ).first()
    assert note is not None
    assert note.severity == Notification.Severity.CRITICAL

    _assert_no_tags_in_outbound(send_mock)
    _assert_assistant_history_clean(fsm_session)


@pytest.mark.django_db
def test_produto_sem_preco_updates_database(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
    fsm_session,
    fsm_catalog,
):
    owner_patch = mock.patch(
        "apps.chatbot.services.occurrence_dispatch.notify_owner_support_issue",
    )
    send_mock = _run_idle_router(
        session=fsm_session,
        resident=fsm_resident,
        instance=fsm_instance,
        tenant_id=fsm_tenant.id,
        text="Doritos tá sem preço na prateleira",
        ai_reply=(
            "[ALERTA_CATALOGO] O Doritos 140g está R$ 11,90 no sistema. "
            "Vou pedir para colocarem a etiqueta."
        ),
        extra_patches=[owner_patch],
    )

    fsm_session.refresh_from_db()
    assert fsm_session.state == ChatSession.State.IDLE

    note = Notification.all_objects.filter(
        tenant=fsm_tenant,
        intent_type="ALERTA_CATALOGO",
    ).first()
    assert note is not None
    assert note.severity == Notification.Severity.WARNING

    _assert_no_tags_in_outbound(send_mock)
    _assert_assistant_history_clean(fsm_session)


@pytest.mark.django_db
def test_codigo_barras_riscado_fallback(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
    fsm_session,
):
    owner_patch = mock.patch(
        "apps.chatbot.services.occurrence_dispatch.notify_owner_support_issue",
    )
    send_mock = _run_idle_router(
        session=fsm_session,
        resident=fsm_resident,
        instance=fsm_instance,
        tenant_id=fsm_tenant.id,
        text="leitor não tá lendo o feijão",
        ai_reply="[AJUDA_LEITURA] Me diga a marca ou nome do feijão que eu localizo no catálogo.",
        extra_patches=[owner_patch],
    )

    fsm_session.refresh_from_db()
    assert fsm_session.state == ChatSession.State.PRODUCT_SEARCH
    assert fsm_session.active_cart_id is not None

    _assert_no_tags_in_outbound(send_mock)
    _assert_assistant_history_clean(fsm_session)


# --- Checkout dinâmico e estoque ---


@pytest.mark.django_db
def test_comprador_com_pressa_splits_items_and_skips_steps(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
    fsm_session,
    fsm_catalog,
):
    send_mock = _run_idle_router(
        session=fsm_session,
        resident=fsm_resident,
        instance=fsm_instance,
        tenant_id=fsm_tenant.id,
        text="Tô com pressa, peguei 3 cocas e 1 doritos, manda o pix",
        ai_reply="[SOLICITACAO_PIX] Perfeito, João! Já montei seu pedido. Envie a foto dos produtos.",
    )

    fsm_session.refresh_from_db()
    assert fsm_session.state == ChatSession.State.AWAITING_PHOTO
    assert fsm_session.active_cart_id is not None

    cart = Cart.objects.get(pk=fsm_session.active_cart_id)
    assert cart.status == Cart.Status.AWAITING_PHOTO

    coca_item = CartItem.objects.filter(
        cart=cart,
        product=fsm_catalog["coca"],
    ).first()
    doritos_item = CartItem.objects.filter(
        cart=cart,
        product=fsm_catalog["doritos"],
    ).first()
    assert coca_item is not None and coca_item.quantity == 3
    assert doritos_item is not None and doritos_item.quantity == 1

    assert Notification.all_objects.filter(intent_type="SOLICITACAO_PIX").count() == 0

    _assert_no_tags_in_outbound(send_mock)
    _assert_assistant_history_clean(fsm_session)


@pytest.mark.django_db
def test_furo_de_estoque_triggers_rupture_warning(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
    fsm_session,
):
    restock_patch = mock.patch(
        "apps.chatbot.services.occurrence_dispatch.notify_owner_restock_issue",
    )
    send_mock = _run_idle_router(
        session=fsm_session,
        resident=fsm_resident,
        instance=fsm_instance,
        tenant_id=fsm_tenant.id,
        text="não tem mais leite desnatado",
        ai_reply="[ALERTA_ESTOQUE] Anotado! Vou avisar o responsável para repor o leite desnatado.",
        extra_patches=[restock_patch],
    )

    fsm_session.refresh_from_db()
    assert fsm_session.state == ChatSession.State.IDLE

    note = Notification.all_objects.filter(
        tenant=fsm_tenant,
        intent_type="ALERTA_ESTOQUE",
    ).first()
    assert note is not None
    assert note.severity == Notification.Severity.WARNING

    _assert_no_tags_in_outbound(send_mock)
    _assert_assistant_history_clean(fsm_session)


# --- Anti-troll e linguagem casual ---


@pytest.mark.django_db
def test_casual_language_allowed_with_emojis(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
    fsm_session,
):
    friendly = (
        "Fala, João! Beleza? 😄 Me conta o que você pegou que eu monto o Pix rapidinho!"
    )
    send_mock = _run_idle_router(
        session=fsm_session,
        resident=fsm_resident,
        instance=fsm_instance,
        tenant_id=fsm_tenant.id,
        text="Eae mano, beleza? Peguei um refri aqui",
        ai_reply=friendly,
    )

    fsm_session.refresh_from_db()
    assert fsm_session.state == ChatSession.State.IDLE

    body = _whatsapp_body(send_mock)
    assert "exclusivamente para processar compras" not in body.lower()
    assert "😄" in body or "beleza" in body.lower()

    _assert_no_tags_in_outbound(send_mock)
    _assert_assistant_history_clean(fsm_session)


@pytest.mark.django_db
def test_offensive_troll_triggers_dry_response_without_emojis(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
    fsm_session,
):
    dry = (
        "Sou o assistente virtual do mercado autônomo e estou aqui exclusivamente "
        "para processar compras. Como posso te ajudar com o catálogo ou com seu carrinho?"
    )
    send_mock = _run_idle_router(
        session=fsm_session,
        resident=fsm_resident,
        instance=fsm_instance,
        tenant_id=fsm_tenant.id,
        text="você é burra? me manda nude",
        ai_reply=dry,
    )

    fsm_session.refresh_from_db()
    assert fsm_session.state == ChatSession.State.IDLE

    body = _whatsapp_body(send_mock)
    assert "exclusivamente para processar compras" in body.lower()
    assert not any(ord(c) > 0x1F300 for c in body)

    _assert_no_tags_in_outbound(send_mock)
    _assert_assistant_history_clean(fsm_session)


# --- Expiração preguiçosa (lazy expiration) ---


def _event_text(text: str, phone: str) -> mock.Mock:
    from apps.integrations.services.webhook_parser import EvolutionWebhookEvent

    return EvolutionWebhookEvent(
        event_type="MESSAGE",
        instance_key="inst",
        connection_state="",
        remote_jid=f"{phone}@s.whatsapp.net",
        message_id="msg-stale-1",
        from_me=False,
        message_text=text,
        message_kind="text",
    )


@pytest.mark.django_db
def test_maybe_reset_stale_session_skips_recent_activity(
    fsm_tenant,
    fsm_resident,
    fsm_session,
):
    from apps.residents.services.session_lazy_expiration import maybe_reset_stale_chat_session

    cart = Cart.objects.create(
        tenant=fsm_tenant,
        resident=fsm_resident,
        status=Cart.Status.OPEN,
    )
    fsm_session.active_cart = cart
    fsm_session.save(update_fields=["active_cart", "updated_at"])
    ChatSession.objects.filter(pk=fsm_session.pk).update(
        last_activity_at=timezone.now() - timedelta(minutes=5),
    )
    fsm_session.refresh_from_db()

    assert maybe_reset_stale_chat_session(fsm_session, resident=fsm_resident) is False
    cart.refresh_from_db()
    assert cart.status == Cart.Status.OPEN
    assert fsm_session.active_cart_id == cart.pk


@pytest.mark.django_db
def test_maybe_reset_stale_session_clears_old_cart(
    fsm_tenant,
    fsm_resident,
    fsm_session,
):
    from apps.residents.services.session_lazy_expiration import maybe_reset_stale_chat_session

    cart = Cart.objects.create(
        tenant=fsm_tenant,
        resident=fsm_resident,
        status=Cart.Status.OPEN,
    )
    fsm_session.active_cart = cart
    fsm_session.state = ChatSession.State.CART_REVIEW
    fsm_session.save(update_fields=["active_cart", "state", "updated_at"])
    ChatSession.objects.filter(pk=fsm_session.pk).update(
        last_activity_at=timezone.now() - timedelta(days=2),
    )
    fsm_session.refresh_from_db()

    assert maybe_reset_stale_chat_session(fsm_session, resident=fsm_resident) is True
    fsm_session.refresh_from_db()
    cart.refresh_from_db()
    assert fsm_session.state == ChatSession.State.IDLE
    assert fsm_session.active_cart_id is None
    assert cart.status == Cart.Status.CANCELLED


@pytest.mark.django_db
def test_stale_session_resets_automatically(
    fsm_tenant,
    fsm_resident,
    fsm_instance,
    fsm_catalog,
):
    from apps.integrations.services.webhook_handlers import _handle_message
    from apps.sales.services.cart_escape import CHECKOUT_PHOTO_MESSAGE
    from tests.factories import CartFactory, CartItemFactory

    cart = CartFactory(
        tenant=fsm_tenant,
        resident=fsm_resident,
        status=Cart.Status.OPEN,
    )
    CartItemFactory(
        cart=cart,
        product=fsm_catalog["coca"],
        quantity=2,
        unit_price=fsm_catalog["coca"].price,
    )
    cart.recalculate_total()

    session = ChatSessionFactory(
        tenant=fsm_tenant,
        phone_number=fsm_resident.phone_number,
        state=ChatSession.State.IDLE,
        active_cart=cart,
    )
    ChatSession.objects.filter(pk=session.pk).update(
        last_activity_at=timezone.now() - timedelta(days=2),
    )

    send_mock = mock.Mock()
    purchase_mock = mock.Mock(return_value=True)

    with (
        mock.patch(
            "apps.billing.services.tenant_suspension.tenant_has_messaging_access",
            return_value=True,
        ),
        mock.patch(
            "apps.residents.services.whatsapp_reply.send_whatsapp_reply",
            send_mock,
        ),
        mock.patch(
            "apps.integrations.services.webhook_handlers.classify_user_intent",
            return_value="PURCHASE",
        ),
        mock.patch(
            "apps.sales.services.cart_flow.route_idle_message",
            purchase_mock,
        ),
    ):
        _handle_message(
            _event_text("preciso pagar", phone=fsm_resident.phone_number),
            fsm_instance,
        )

    session.refresh_from_db()
    cart.refresh_from_db()
    assert session.active_cart_id is None
    assert session.state == ChatSession.State.IDLE
    assert cart.status == Cart.Status.CANCELLED

    for call in send_mock.call_args_list:
        body = call[0][2]
        assert CHECKOUT_PHOTO_MESSAGE not in body

    purchase_mock.assert_called_once()
