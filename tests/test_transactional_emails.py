from __future__ import annotations

from unittest import mock

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.billing.models import Subscription
from apps.core.emails import (
    PASSWORD_RESET_SUBJECT,
    SUBSCRIPTION_SUSPENDED_SUBJECT,
    WELCOME_SUBJECT,
    send_market_transactional_email,
    send_password_reset_email,
    send_subscription_suspended_email,
    send_welcome_trial_email,
)
from apps.tenants.models import Tenant

User = get_user_model()


@pytest.fixture
def sample_user(db):
    now = timezone.now()
    tenant = Tenant.objects.create(
        name="Mercado Teste",
        slug="mercado-teste",
        trial_started_at=now,
        trial_ends_at=now + timedelta(days=7),
    )
    return User.objects.create_user(
        "owner@test.com",
        password="StrongPass123!",
        tenant=tenant,
        first_name="Maria",
        is_tenant_admin=True,
    )


@pytest.mark.django_db
def test_send_market_transactional_email_multipart(sample_user):
    mail.outbox.clear()
    send_market_transactional_email(
        "Assunto teste",
        "welcome_trial",
        {
            "first_name": "Maria",
            "company_name": "Mercado Teste",
            "trial_days": 7,
            "action_url": "http://localhost:5173/signin",
            "logo_url": "http://localhost:5173/images/brand/logotipo_marketchat_completo_PRETO.gif",
            "company_legal_name": "Viva Software",
            "cnpj": "35.960.300/0001-05",
            "support_email": "suporte@marketchat.com.br",
            "support_phone": "(14) 99168-3639",
            "support_whatsapp_url": "https://wa.me/5514991683639",
            "address_lines": ["Linha 1", "Linha 2"],
            "current_year": 2026,
        },
        sample_user.email,
    )
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == "Assunto teste"
    assert "Maria" in msg.body
    assert "Acessar Meu Painel Administrativo" in msg.body
    assert len(msg.alternatives) == 1
    html, mime = msg.alternatives[0]
    assert mime == "text/html"
    assert "Maria" in html
    assert "059669" in html or "#059669" in html


@pytest.mark.django_db
def test_transactional_from_uses_default_from_email(settings):
    settings.TRANSACTIONAL_FROM_EMAIL = ""
    settings.DEFAULT_FROM_EMAIL = "contato@marketchat.com.br"
    mail.outbox.clear()
    user = User.objects.create_user("smtp@test.com", password="x")
    send_password_reset_email(user)
    assert "contato@marketchat.com.br" in mail.outbox[0].from_email


@pytest.mark.django_db
def test_email_attaches_inline_logo_when_file_exists(settings, tmp_path):
    logo = tmp_path / "logo.gif"
    logo.write_bytes(b"GIF89a")
    settings.EMAIL_BRAND_LOGO_PATH = str(logo)
    mail.outbox.clear()
    user = User.objects.create_user("logo@test.com", password="x")
    send_password_reset_email(user)
    msg = mail.outbox[0]
    html, _ = msg.alternatives[0]
    assert "cid:marketchat-logo" in html
    assert any(getattr(p, "get_content_type", lambda: "")() == "image/gif" for p in msg.attachments)


@pytest.mark.django_db
def test_send_password_reset_email(sample_user):
    mail.outbox.clear()
    send_password_reset_email(sample_user)
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == PASSWORD_RESET_SUBJECT
    assert "emoji" not in msg.subject.lower()
    uid = urlsafe_base64_encode(force_bytes(sample_user.pk))
    token = default_token_generator.make_token(sample_user)
    assert uid in msg.body
    assert token in msg.body
    html, _ = msg.alternatives[0]
    assert "Redefinir Minha Senha" in html
    assert "1E3A8A" in html


@pytest.mark.django_db
def test_send_subscription_suspended_email(sample_user, settings):
    settings.FRONTEND_SIGNIN_URL = "https://app.example/signin"
    mail.outbox.clear()
    tenant = sample_user.tenant
    send_subscription_suspended_email(
        sample_user,
        tenant,
        reason="trial_expired",
        reason_label="período de testes encerrado",
    )
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == SUBSCRIPTION_SUSPENDED_SUBJECT
    assert "pausada" in msg.body.lower() or "pausada" in msg.subject.lower()
    assert "https://app.example/signin" in msg.body
    html, _ = msg.alternatives[0]
    assert "059669" in html or "#059669" in html
    assert "Regularizar" in html


@pytest.mark.django_db
def test_send_welcome_trial_email(sample_user, settings):
    settings.FRONTEND_SIGNIN_URL = "https://app.example/signin"
    mail.outbox.clear()
    tenant = sample_user.tenant
    send_welcome_trial_email(sample_user, tenant)
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == WELCOME_SUBJECT
    assert "Maria" in msg.body
    assert "Mercado Teste" in msg.body
    assert "https://app.example/signin" in msg.body
    html, _ = msg.alternatives[0]
    assert "Pilares ativos" in html
    assert "059669" in html or "#059669" in html


def _asaas_mock():
    patcher = mock.patch("apps.billing.services.subscription_flow.AsaasClient")
    mock_cls = patcher.start()
    inst = mock_cls.return_value
    inst.create_customer.return_value = {"id": "cus_test_1"}
    inst.tokenize_credit_card.return_value = {"creditCardToken": "tok_test_1"}
    inst.create_subscription.return_value = {"id": "sub_test_1", "status": "ACTIVE"}
    return patcher, inst


@pytest.mark.django_db
def test_register_sends_welcome_email(api_client):
    url = reverse("auth-register")
    payload = {
        "company_name": "Acme Ltda",
        "tenant_slug": "acme-email",
        "admin_email": "admin@acme.com",
        "admin_password": "StrongPass123!",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "accept_terms": True,
        "credit_card": {
            "holderName": "ADA LOVELACE",
            "number": "5162306219378829",
            "expiryMonth": "12",
            "expiryYear": "2030",
            "ccv": "123",
        },
        "credit_card_holder": {
            "name": "Ada Lovelace",
            "email": "admin@acme.com",
            "cpfCnpj": "24971563792",
            "postalCode": "01311000",
            "address": "Av Paulista",
            "addressNumber": "1000",
            "province": "SP",
            "phone": "11999999999",
        },
    }
    mail.outbox.clear()
    patcher, _ = _asaas_mock()
    try:
        response = api_client.post(url, payload, format="json")
    finally:
        patcher.stop()
    assert response.status_code == 201
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == WELCOME_SUBJECT
    assert "Ada" in mail.outbox[0].body
    assert Subscription.objects.filter(asaas_subscription_id="sub_test_1").exists()
