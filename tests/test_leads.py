from unittest import mock

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, override_settings
from django.urls import reverse

from apps.accounts.admin import LeadAdmin, marcar_como_contatado
from apps.accounts.models import Lead
from tests.test_registration import _asaas_mock, _register_payload

User = get_user_model()

pytestmark = pytest.mark.usefixtures("disable_signup_lead_throttle")


@pytest.fixture
def disable_signup_lead_throttle():
    with override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_CLASSES": [],
            "DEFAULT_THROTTLE_RATES": {},
        }
    ):
        yield


def _signup_lead_f1_payload(**overrides):
    payload = {
        "lead_type": "F1",
        "full_name": "Maria Lead",
        "email": "maria@lead.com",
        "phone": "11988887777",
    }
    payload.update(overrides)
    return payload


def _signup_lead_f2_payload(**overrides):
    payload = {
        "lead_type": "F2",
        "email": "maria@lead.com",
        "company_name": "Acme Mercados",
        "address": "Av Paulista, São Paulo",
        "address_number": "1000",
        "complement": "Sala 10",
        "cep": "01311000",
        "state": "SP",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_signup_lead_f1_creates_novo(api_client):
    url = reverse("auth-signup-lead")
    response = api_client.post(url, _signup_lead_f1_payload(), format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == Lead.Status.NOVO
    assert data["lead_type"] == Lead.LeadType.F1
    lead = Lead.objects.get(email="maria@lead.com")
    assert lead.full_name == "Maria Lead"
    assert lead.phone == "5511988887777"
    assert lead.lead_type == Lead.LeadType.F1


@pytest.mark.django_db
def test_signup_lead_f1_upserts_same_email(api_client):
    url = reverse("auth-signup-lead")
    api_client.post(url, _signup_lead_f1_payload(), format="json")
    response = api_client.post(
        url,
        _signup_lead_f1_payload(full_name="Maria Atualizada", phone="21977776666"),
        format="json",
    )
    assert response.status_code == 201
    assert Lead.objects.filter(email="maria@lead.com").count() == 1
    lead = Lead.objects.get(email="maria@lead.com")
    assert lead.full_name == "Maria Atualizada"
    assert lead.phone == "5521977776666"


@pytest.mark.django_db
def test_signup_lead_f2_updates_existing_lead(api_client):
    url = reverse("auth-signup-lead")
    api_client.post(url, _signup_lead_f1_payload(), format="json")
    response = api_client.post(url, _signup_lead_f2_payload(), format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["lead_type"] == Lead.LeadType.F2
    lead = Lead.objects.get(email="maria@lead.com")
    assert lead.lead_type == Lead.LeadType.F2
    assert lead.company_name == "Acme Mercados"
    assert lead.company_address == "Av Paulista, São Paulo, nº 1000, Sala 10 — CEP 01311000"
    assert lead.state == "SP"
    assert lead.full_name == "Maria Lead"
    assert lead.phone == "5511988887777"


@pytest.mark.django_db
def test_signup_lead_f2_without_f1_creates_lead(api_client):
    url = reverse("auth-signup-lead")
    response = api_client.post(
        url,
        _signup_lead_f2_payload(email="f2only@lead.com"),
        format="json",
    )
    assert response.status_code == 201
    lead = Lead.objects.get(email="f2only@lead.com")
    assert lead.lead_type == Lead.LeadType.F2
    assert lead.status == Lead.Status.NOVO
    assert lead.company_name == "Acme Mercados"


@pytest.mark.django_db
def test_signup_lead_f2_does_not_downgrade_em_contato_status(api_client):
    url = reverse("auth-signup-lead")
    api_client.post(url, _signup_lead_f1_payload(email="contato@lead.com"), format="json")
    lead = Lead.objects.get(email="contato@lead.com")
    lead.status = Lead.Status.EM_CONTATO
    lead.save(update_fields=["status"])

    response = api_client.post(
        url,
        _signup_lead_f2_payload(email="contato@lead.com"),
        format="json",
    )
    assert response.status_code == 201
    lead.refresh_from_db()
    assert lead.status == Lead.Status.EM_CONTATO
    assert lead.lead_type == Lead.LeadType.F2


@pytest.mark.django_db
def test_signup_lead_f1_does_not_downgrade_f2_lead_type(api_client):
    url = reverse("auth-signup-lead")
    api_client.post(url, _signup_lead_f2_payload(email="keepf2@lead.com"), format="json")
    response = api_client.post(
        url,
        _signup_lead_f1_payload(email="keepf2@lead.com", full_name="Novo Nome"),
        format="json",
    )
    assert response.status_code == 201
    lead = Lead.objects.get(email="keepf2@lead.com")
    assert lead.lead_type == Lead.LeadType.F2
    assert lead.full_name == "Novo Nome"


@pytest.mark.django_db
def test_register_converts_lead(api_client):
    lead_url = reverse("auth-signup-lead")
    api_client.post(lead_url, _signup_lead_f1_payload(email="convert@lead.com"), format="json")
    lead = Lead.objects.get(email="convert@lead.com")
    assert lead.status == Lead.Status.NOVO

    register_url = reverse("auth-register")
    payload = _register_payload(
        admin_email="convert@lead.com",
        tenant_slug="convert-lead",
        credit_card_holder={
            "name": "Maria Lead",
            "email": "convert@lead.com",
            "cpfCnpj": "24971563792",
            "postalCode": "01311000",
            "address": "Av Paulista",
            "addressNumber": "1000",
            "province": "SP",
            "phone": "11988887777",
        },
    )
    patcher, _ = _asaas_mock()
    try:
        response = api_client.post(register_url, payload, format="json")
    finally:
        patcher.stop()

    assert response.status_code == 201
    lead.refresh_from_db()
    assert lead.status == Lead.Status.CONVERTIDO
    assert lead.converted_at is not None


@pytest.mark.django_db
def test_lead_admin_hides_converted_by_default():
    Lead.objects.create(
        full_name="Ativo",
        email="ativo@lead.com",
        phone="5511999999999",
        status=Lead.Status.NOVO,
    )
    Lead.objects.create(
        full_name="Convertido",
        email="convertido@lead.com",
        phone="5511888888888",
        status=Lead.Status.CONVERTIDO,
    )

    factory = RequestFactory()
    request = factory.get("/admin/accounts/lead/")
    request.user = User.objects.create_superuser(
        email="admin@test.com",
        password="AdminPass123!",
    )

    admin = LeadAdmin(Lead, AdminSite())
    qs = admin.get_queryset(request)
    emails = set(qs.values_list("email", flat=True))
    assert "ativo@lead.com" in emails
    assert "convertido@lead.com" not in emails

    request_filtered = factory.get("/admin/accounts/lead/?status__exact=CONVERTIDO")
    request_filtered.user = request.user
    qs_filtered = admin.get_queryset(request_filtered)
    emails_filtered = set(qs_filtered.values_list("email", flat=True))
    assert "convertido@lead.com" in emails_filtered


@pytest.mark.django_db
def test_lead_admin_action_marcar_como_contatado():
    lead_a = Lead.objects.create(
        full_name="Lead A",
        email="a@lead.com",
        phone="5511999999999",
        status=Lead.Status.NOVO,
    )
    lead_b = Lead.objects.create(
        full_name="Lead B",
        email="b@lead.com",
        phone="5511888888888",
        status=Lead.Status.NOVO,
    )
    converted = Lead.objects.create(
        full_name="Convertido",
        email="c@lead.com",
        phone="5511777777777",
        status=Lead.Status.CONVERTIDO,
    )

    factory = RequestFactory()
    request = factory.post("/admin/accounts/lead/")
    request.user = User.objects.create_superuser(
        email="admin@test.com",
        password="AdminPass123!",
    )
    admin = LeadAdmin(Lead, AdminSite())
    queryset = Lead.objects.filter(pk__in=[lead_a.pk, lead_b.pk, converted.pk])
    with mock.patch.object(admin, "message_user"):
        marcar_como_contatado(admin, request, queryset)

    lead_a.refresh_from_db()
    lead_b.refresh_from_db()
    converted.refresh_from_db()
    assert lead_a.status == Lead.Status.EM_CONTATO
    assert lead_b.status == Lead.Status.EM_CONTATO
    assert converted.status == Lead.Status.CONVERTIDO
