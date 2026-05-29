import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.support.models import SupportTicket, SupportTicketMessage
from tests.factories import TenantFactory, UserFactory


def _auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


TICKET_PAYLOAD = {
    "subject": "QR Code não conecta",
    "description": "Histórico do Suporte Copilot:\nUsuário: ajuda\nCopilot: escaneie o QR",
    "category_route": "/admin/settings?section=integrations",
}


@pytest.mark.django_db
def test_support_ticket_create_success(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="ticket@example.com")
    _auth(api_client, user)

    response = api_client.post(reverse("support-ticket-list"), TICKET_PAYLOAD, format="json")

    assert response.status_code == 201
    data = response.json()
    assert data["subject"] == TICKET_PAYLOAD["subject"]
    assert data["status"] == "NEW"
    assert data["priority"] == "MEDIUM"
    assert "id" in data
    assert "created_at" in data

    ticket = SupportTicket.objects.get(pk=data["id"])
    assert ticket.tenant_id == tenant.id
    assert ticket.user_id == user.id
    assert ticket.category_route == TICKET_PAYLOAD["category_route"]
    assert SupportTicketMessage.objects.filter(ticket=ticket).count() == 1
    first_msg = SupportTicketMessage.objects.get(ticket=ticket)
    assert first_msg.is_from_admin is False
    assert first_msg.message == TICKET_PAYLOAD["description"]


@pytest.mark.django_db
def test_support_ticket_user_without_tenant(api_client):
    user = UserFactory(tenant=None, email="notenant@example.com")
    _auth(api_client, user)

    response = api_client.post(reverse("support-ticket-list"), TICKET_PAYLOAD, format="json")
    assert response.status_code == 400
    assert "empresa" in response.json()["detail"].lower()


@pytest.mark.django_db
def test_support_ticket_validation_empty_subject(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="badticket@example.com")
    _auth(api_client, user)

    payload = {**TICKET_PAYLOAD, "subject": "   "}
    response = api_client.post(reverse("support-ticket-list"), payload, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_support_ticket_list_tenant_scoped(api_client):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_a = UserFactory(tenant=tenant_a, email="lista@example.com")
    user_b = UserFactory(tenant=tenant_b, email="outro@example.com")

    ticket_a = SupportTicket.objects.create(
        tenant=tenant_a,
        user=user_a,
        subject="Ticket A",
        description="Corpo A",
        category_route="/admin",
    )
    SupportTicket.objects.create(
        tenant=tenant_b,
        user=user_b,
        subject="Ticket B",
        description="Corpo B",
        category_route="/admin",
    )

    _auth(api_client, user_a)
    response = api_client.get(reverse("support-ticket-list"))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == ticket_a.pk
    assert data[0]["subject"] == "Ticket A"


@pytest.mark.django_db
def test_support_ticket_detail_other_tenant_404(api_client):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_a = UserFactory(tenant=tenant_a, email="det@example.com")
    user_b = UserFactory(tenant=tenant_b, email="detb@example.com")
    ticket_b = SupportTicket.objects.create(
        tenant=tenant_b,
        user=user_b,
        subject="Privado",
        description="x",
        category_route="/admin",
    )

    _auth(api_client, user_a)
    response = api_client.get(reverse("support-ticket-detail", kwargs={"pk": ticket_b.pk}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_support_ticket_detail_with_messages(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="detail@example.com")
    _auth(api_client, user)

    create_resp = api_client.post(reverse("support-ticket-list"), TICKET_PAYLOAD, format="json")
    ticket_id = create_resp.json()["id"]

    response = api_client.get(reverse("support-ticket-detail", kwargs={"pk": ticket_id}))
    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == TICKET_PAYLOAD["subject"]
    assert len(data["messages"]) == 1
    assert data["messages"][0]["is_from_admin"] is False


@pytest.mark.django_db
def test_support_ticket_reply(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="reply@example.com")
    _auth(api_client, user)

    create_resp = api_client.post(reverse("support-ticket-list"), TICKET_PAYLOAD, format="json")
    ticket_id = create_resp.json()["id"]

    response = api_client.post(
        reverse("support-ticket-reply", kwargs={"pk": ticket_id}),
        {"message": "Segue mais informação"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["message"]["message"] == "Segue mais informação"

    detail = api_client.get(reverse("support-ticket-detail", kwargs={"pk": ticket_id})).json()
    assert len(detail["messages"]) == 2


@pytest.mark.django_db
def test_support_ticket_reply_closed_400(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="closed@example.com")
    ticket = SupportTicket.objects.create(
        tenant=tenant,
        user=user,
        subject="Fechado",
        description="x",
        category_route="/admin",
        status=SupportTicket.Status.CLOSED,
    )
    _auth(api_client, user)

    response = api_client.post(
        reverse("support-ticket-reply", kwargs={"pk": ticket.pk}),
        {"message": "Tentativa"},
        format="json",
    )
    assert response.status_code == 400
    assert "encerrado" in response.json()["detail"].lower()


@pytest.mark.django_db
def test_support_ticket_patch_resolved(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="patch@example.com")
    _auth(api_client, user)

    create_resp = api_client.post(reverse("support-ticket-list"), TICKET_PAYLOAD, format="json")
    ticket_id = create_resp.json()["id"]

    response = api_client.patch(
        reverse("support-ticket-detail", kwargs={"pk": ticket_id}),
        {"status": "RESOLVED"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "RESOLVED"


@pytest.mark.django_db
def test_support_ticket_reply_resolved_400(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="resolved-reply@example.com")
    ticket = SupportTicket.objects.create(
        tenant=tenant,
        user=user,
        subject="Resolvido",
        description="x",
        category_route="/admin",
        status=SupportTicket.Status.RESOLVED,
    )
    _auth(api_client, user)

    response = api_client.post(
        reverse("support-ticket-reply", kwargs={"pk": ticket.pk}),
        {"message": "Tentativa"},
        format="json",
    )
    assert response.status_code == 400
