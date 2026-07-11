import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import Lead


@pytest.fixture
def disable_signup_throttle():
    with override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_CLASSES": [],
            "DEFAULT_THROTTLE_RATES": {},
        }
    ):
        yield


@pytest.mark.usefixtures("disable_signup_throttle")
@pytest.mark.django_db
def test_consultative_lead_creates_f1(api_client):
    url = reverse("auth-consultative-lead")
    response = api_client.post(
        url,
        {
            "full_name": "João Consultoria",
            "email": "joao@consultoria.com",
            "phone": "11988887777",
        },
        format="json",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["lead_type"] == Lead.LeadType.F1
    assert data["status"] == Lead.Status.NOVO
    lead = Lead.objects.get(email="joao@consultoria.com")
    assert lead.full_name == "João Consultoria"
    assert lead.phone == "5511988887777"


@pytest.mark.usefixtures("disable_signup_throttle")
@pytest.mark.django_db
def test_consultative_lead_upserts_same_email(api_client):
    url = reverse("auth-consultative-lead")
    api_client.post(
        url,
        {"full_name": "Maria", "email": "maria@consultoria.com", "phone": "11999998888"},
        format="json",
    )
    response = api_client.post(
        url,
        {"full_name": "Maria Silva", "email": "maria@consultoria.com", "phone": "21977776666"},
        format="json",
    )
    assert response.status_code == 201
    assert Lead.objects.filter(email="maria@consultoria.com").count() == 1
    lead = Lead.objects.get(email="maria@consultoria.com")
    assert lead.full_name == "Maria Silva"
    assert lead.phone == "5521977776666"


@pytest.mark.usefixtures("disable_signup_throttle")
@pytest.mark.django_db
@override_settings(LEAD_SALES_ALERT_EMAIL="vendedora@marketchat.com.br")
def test_consultative_lead_sends_sales_email(api_client):
    mail.outbox.clear()
    url = reverse("auth-consultative-lead")
    response = api_client.post(
        url,
        {
            "full_name": "Ana Lead",
            "email": "ana@consultoria.com",
            "phone": "11977776666",
        },
        format="json",
    )
    assert response.status_code == 201
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == ["vendedora@marketchat.com.br"]
    assert "Novo Lead F1: Ana Lead" in msg.subject
    assert "Ana Lead" in msg.body
    assert "ana@consultoria.com" in msg.body


@pytest.mark.usefixtures("disable_signup_throttle")
@pytest.mark.django_db
@override_settings(LEAD_SALES_ALERT_EMAIL="")
def test_consultative_lead_without_alert_email(api_client):
    mail.outbox.clear()
    url = reverse("auth-consultative-lead")
    response = api_client.post(
        url,
        {
            "full_name": "Sem Alerta",
            "email": "sem@consultoria.com",
            "phone": "11966665555",
        },
        format="json",
    )
    assert response.status_code == 201
    assert len(mail.outbox) == 0
