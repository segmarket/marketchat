from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.billing.models import AsaasSubaccount
from apps.residents.models import ChatSession
from apps.sales.models import Cart, CartItem
from apps.sales.services.cart_flow import process_cart_flow
from apps.sales.services.intent_gatekeeper import PAYMENT_ERROR, PURCHASE
from apps.sales.services.product_term_extractor import extract_product_term
from apps.sales.services.intent_gatekeeper import GENERAL
from apps.sales.services.owner_alert import SUPPORT_RESIDENT_MESSAGE
from apps.sales.services.whatsapp_interactive import CART_ADD_MORE, CART_CHECKOUT, PROD_ID_PREFIX
from apps.tenants.context import tenant_scope
from tests.factories import (
    AsaasSubaccountFactory,
    CartFactory,
    ChatSessionFactory,
    ProductFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)


def _event_text(text: str, phone: str = "5511999887766") -> mock.Mock:
    from apps.integrations.services.webhook_parser import EvolutionWebhookEvent

    return EvolutionWebhookEvent(
        event_type="MESSAGE",
        instance_key="inst",
        connection_state="",
        remote_jid=f"{phone}@s.whatsapp.net",
        message_id="msg1",
        from_me=False,
        message_text=text,
        message_kind="text",
    )


def _event_interactive(interactive_id: str, phone: str = "5511999887766") -> mock.Mock:
    from apps.integrations.services.webhook_parser import EvolutionWebhookEvent

    return EvolutionWebhookEvent(
        event_type="MESSAGE",
        instance_key="inst",
        connection_state="",
        remote_jid=f"{phone}@s.whatsapp.net",
        message_id="msg2",
        from_me=False,
        message_text="",
        message_kind="interactive",
        interactive_id=interactive_id,
    )


def _event_image(raw_message: dict, phone: str = "5511999887766"):
    from apps.integrations.services.webhook_parser import EvolutionWebhookEvent

    return EvolutionWebhookEvent(
        event_type="MESSAGE",
        instance_key="inst",
        connection_state="",
        remote_jid=f"{phone}@s.whatsapp.net",
        message_id="msg3",
        from_me=False,
        message_text="",
        message_kind="image",
        raw_message=raw_message,
    )


@pytest.mark.django_db
def test_extract_product_term(settings):
    settings.OPENAI_API_KEY = "test-key"
    mock_response = mock.Mock()
    mock_response.choices = [mock.Mock(message=mock.Mock(content="coca cola"))]

    with mock.patch("openai.OpenAI") as openai_cls:
        openai_cls.return_value.chat.completions.create.return_value = mock_response
        term = extract_product_term("Quero comprar uma coca cola")

    assert term == "coca cola"


@pytest.mark.django_db
def test_flow_product_search_to_selection():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    ProductFactory(tenant=tenant, sku="COCA-01", name="Coca Cola 2L", price=Decimal("12.50"))
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.ACTIVE_BOT,
    )

    with (
        mock.patch(
            "apps.sales.services.active_bot_router.classify_user_intent",
            return_value=PURCHASE,
        ),
        mock.patch(
            "apps.sales.services.cart_flow.extract_product_term",
            return_value="coca cola",
        ),
        mock.patch("apps.sales.services.cart_flow.send_product_list") as send_list,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Quero comprar uma coca cola", resident.phone_number),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_PRODUCT_SELECTION
    assert session.active_cart_id is not None
    send_list.assert_called_once()


@pytest.mark.django_db
def test_flow_select_product_asks_quantity():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    product = ProductFactory(tenant=tenant, sku="COCA-01", name="Coca Cola", price=Decimal("10.00"))
    cart = CartFactory(tenant=tenant, resident=resident)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_PRODUCT_SELECTION,
        active_cart=cart,
        temporary_name="COCA-01",
    )

    with mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_interactive(f"{PROD_ID_PREFIX}COCA-01", resident.phone_number),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_QUANTITY
    assert session.pending_product_id == product.id
    assert CartItem.objects.filter(cart=cart, product=product, quantity=0).exists()
    assert "Quantas unidades" in send.call_args[0][2]


@pytest.mark.django_db
def test_flow_quantity_and_loop_buttons():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    product = ProductFactory(tenant=tenant, sku="COCA-01", name="Coca Cola", price=Decimal("5.00"))
    cart = CartFactory(tenant=tenant, resident=resident)
    CartItem.objects.create(cart=cart, product=product, quantity=0, unit_price=product.price)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_QUANTITY,
        active_cart=cart,
        pending_product=product,
    )

    with mock.patch("apps.sales.services.cart_flow.send_cart_decision_buttons") as send_btns:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("2", resident.phone_number),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_LOOP_DECISION
    item = CartItem.objects.get(cart=cart, product=product)
    assert item.quantity == 2
    cart.refresh_from_db()
    assert cart.total_value == Decimal("10.00")
    send_btns.assert_called_once()


@pytest.mark.django_db
def test_flow_add_more_returns_active_bot():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    cart = CartFactory(tenant=tenant, resident=resident, total_value=Decimal("10.00"))
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_LOOP_DECISION,
        active_cart=cart,
    )

    with mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_interactive(CART_ADD_MORE, resident.phone_number),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.ACTIVE_BOT
    assert "O que mais" in send.call_args[0][2]


@pytest.mark.django_db
def test_flow_checkout_requests_photo():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    product = ProductFactory(tenant=tenant, price=Decimal("15.00"))
    cart = CartFactory(tenant=tenant, resident=resident, total_value=Decimal("15.00"))
    CartItem.objects.create(
        cart=cart,
        product=product,
        quantity=1,
        unit_price=product.price,
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_LOOP_DECISION,
        active_cart=cart,
    )

    with mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_interactive(CART_CHECKOUT, resident.phone_number),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_PHOTO
    cart.refresh_from_db()
    assert cart.status == Cart.Status.AWAITING_PHOTO
    assert "foto nítida" in send.call_args[0][2].lower()


@pytest.mark.django_db
def test_webhook_image_sets_awaiting_payment():
    tenant = TenantFactory()
    AsaasSubaccountFactory(
        tenant=tenant,
        account_status=AsaasSubaccount.AccountStatus.APPROVED,
    )
    instance = WhatsappInstanceFactory(tenant=tenant, instance_name="mc-cart-test")
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    cart = CartFactory(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.AWAITING_PHOTO,
        total_value=Decimal("20.00"),
    )
    ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_PHOTO,
        active_cart=cart,
    )

    raw_message = {
        "imageMessage": {
            "mimetype": "image/jpeg",
            "caption": "",
        },
    }
    body = {
        "event": "MESSAGE",
        "instance": instance.instance_name,
        "data": {
            "key": {
                "remoteJid": f"{resident.phone_number}@s.whatsapp.net",
                "id": "img-msg-1",
                "fromMe": False,
            },
            "message": raw_message,
        },
    }

    def _fake_pix_charge(cart_arg, resident_arg):
        cart_arg.asaas_billing_id = "pay_test_123"
        cart_arg.status = Cart.Status.AWAITING_PAYMENT
        cart_arg.save(update_fields=["asaas_billing_id", "status", "updated_at"])
        return "00020126580014br.gov.bcb.pix"

    with (
        mock.patch(
            "apps.sales.services.evolution_media.EvolutionClient.download_media",
            return_value={"data": {"base64": "ZmFrZSBpbWFnZQ=="}},
        ),
        mock.patch(
            "apps.sales.services.evolution_media.EvolutionClient.extract_downloaded_media_bytes",
            return_value=b"fake image bytes",
        ),
        mock.patch(
            "apps.billing.services.asaas_pix_charge.create_cart_pix_charge",
            side_effect=_fake_pix_charge,
        ),
        mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply"),
    ):
        client = APIClient()
        url = reverse("webhook-evolution")
        response = client.post(
            f"{url}?secret={instance.webhook_secret}",
            body,
            format="json",
        )

    assert response.status_code == 200
    cart.refresh_from_db()
    assert cart.status == Cart.Status.AWAITING_PAYMENT
    assert cart.product_photo.name
    assert cart.asaas_billing_id == "pay_test_123"


@pytest.mark.django_db
def test_general_greeting_injects_resident_context():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766", name="Maria Silva")
    ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.ACTIVE_BOT,
    )

    with (
        mock.patch(
            "apps.sales.services.active_bot_router.classify_user_intent",
            return_value=GENERAL,
        ),
        mock.patch(
            "apps.sales.services.active_bot_router.complete_with_session_history",
            return_value="Olá, Maria! Como posso te ajudar?",
        ) as openai_chat,
        mock.patch("apps.sales.services.active_bot_router.send_whatsapp_reply"),
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Oi", resident.phone_number),
            )

    assert handled is True
    assert openai_chat.call_args.kwargs["user_content"] == "Oi"
    dynamic_tail = openai_chat.call_args.kwargs["dynamic_system_tail"]
    assert "Maria Silva" in dynamic_tail
    assert resident.market.name.strip() in dynamic_tail
    assert "Nunca seja genérico" in dynamic_tail


@pytest.mark.django_db
def test_payment_machine_offers_pix_and_enters_sales_funnel():
    tenant = TenantFactory(phone="5511988776655")
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.ACTIVE_BOT,
    )
    message = "A máquina de pagar está com problemas"

    with (
        mock.patch(
            "apps.sales.services.active_bot_router.classify_user_intent",
            return_value=PAYMENT_ERROR,
        ) as classify,
        mock.patch(
            "apps.sales.services.cart_flow.extract_product_term",
        ) as extract_term,
        mock.patch(
            "apps.sales.services.cart_flow.send_product_list",
        ) as send_list,
        mock.patch(
            "apps.sales.services.active_bot_router.send_whatsapp_reply",
        ) as send_resident,
        mock.patch(
            "apps.sales.services.owner_alert.send_whatsapp_reply",
        ) as send_owner,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text(message, resident.phone_number),
            )

    assert handled is True
    classify.assert_called_once_with(message)
    extract_term.assert_not_called()
    send_list.assert_not_called()

    resident_msgs = [c[0][2] for c in send_resident.call_args_list]
    assert len(resident_msgs) == 1
    recovery = resident_msgs[0]
    assert resident.name in recovery
    assert "Pix" in recovery
    assert "maquininha" in recovery.lower()
    assert "qual produto" in recovery.lower()
    assert SUPPORT_RESIDENT_MESSAGE not in recovery

    assert send_owner.call_count == 1
    owner_body = send_owner.call_args[0][2]
    assert resident.name in owner_body
    assert resident.phone_number in owner_body
    assert message in owner_body
    assert "Pagamento" in owner_body

    session.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_PRODUCT_SELECTION
    assert session.active_cart_id is not None
