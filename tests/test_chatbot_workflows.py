from unittest import mock

import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chatbot.models import ChatbotWorkflow
from apps.chatbot.services.flow_engine import run_chatbot_flow
from apps.chatbot.services.intent_classifier import IntentClassifierError
from apps.chatbot.services.system_workflows import seed_system_workflows
from tests.factories import (
    ChatbotWorkflowFactory,
    ResidentFactory,
    TenantFactory,
    UserFactory,
    WhatsappInstanceFactory,
)

GELADEIRA_FLOW = {
    "nodes": [
        {"id": "trigger-1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {"label": "Início"}},
        {
            "id": "ai-1",
            "type": "ai_filter",
            "position": {"x": 0, "y": 100},
            "data": {"intents": ["manutenção"], "systemPrompt": ""},
        },
        {
            "id": "response-1",
            "type": "response",
            "position": {"x": 0, "y": 200},
            "data": {"message": "Responsável avisado."},
        },
        {
            "id": "alert-1",
            "type": "owner_alert",
            "position": {"x": 0, "y": 300},
            "data": {
                "ownerPhone": "5511999887766",
                "messageTemplate": "{name}: {text}",
            },
        },
    ],
    "edges": [
        {"id": "e1", "source": "trigger-1", "target": "ai-1"},
        {"id": "e2", "source": "ai-1", "target": "response-1", "data": {"intent": "manutenção"}},
        {"id": "e3", "source": "response-1", "target": "alert-1"},
    ],
}


def _auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


@pytest.mark.django_db
def test_chatbot_workflow_save_and_tenant_isolation(api_client):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_a = UserFactory(tenant=tenant_a, email="chatbot-a@example.com")
    ChatbotWorkflowFactory(tenant=tenant_b, name="Outro fluxo", flow_data=GELADEIRA_FLOW)

    _auth(api_client, user_a)
    save_resp = api_client.post(
        reverse("chatbot-workflows-save"),
        {"name": "Meu fluxo", "is_active": True, "flow_data": GELADEIRA_FLOW},
        format="json",
    )
    assert save_resp.status_code == 201
    workflow_id = save_resp.json()["id"]

    list_resp = api_client.get(reverse("chatbot-workflows-list"))
    assert list_resp.status_code == 200
    custom_flows = [w for w in list_resp.json() if not w["is_system"]]
    assert len(custom_flows) == 1
    assert custom_flows[0]["id"] == workflow_id

    detail_resp = api_client.get(reverse("chatbot-workflows-detail", kwargs={"pk": workflow_id}))
    assert detail_resp.status_code == 200
    assert len(detail_resp.json()["flow_data"]["nodes"]) == 4

    update_resp = api_client.post(
        reverse("chatbot-workflows-save"),
        {
            "id": workflow_id,
            "flow_data": {
                "nodes": GELADEIRA_FLOW["nodes"][:2],
                "edges": [GELADEIRA_FLOW["edges"][0]],
            },
        },
        format="json",
    )
    assert update_resp.status_code == 200
    assert len(update_resp.json()["flow_data"]["nodes"]) == 2


@pytest.mark.django_db
def test_chatbot_multiple_active_per_tenant(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="chatbot-active@example.com")
    _auth(api_client, user)

    first = ChatbotWorkflowFactory(tenant=tenant, name="A", is_active=True)
    second = ChatbotWorkflowFactory(tenant=tenant, name="B", is_active=True)

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_active is True
    assert second.is_active is True

    patch = api_client.patch(
        reverse("chatbot-workflows-detail", kwargs={"pk": first.id}),
        {"is_active": False},
        format="json",
    )
    assert patch.status_code == 200
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_active is False
    assert second.is_active is True


@pytest.mark.django_db
def test_chatbot_workflow_detail_patch_delete_duplicate(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="chatbot-crud@example.com")
    wf = ChatbotWorkflowFactory(tenant=tenant, name="Fluxo A", flow_data=GELADEIRA_FLOW)
    _auth(api_client, user)

    detail = api_client.get(reverse("chatbot-workflows-detail", kwargs={"pk": wf.id}))
    assert detail.status_code == 200
    assert detail.json()["name"] == "Fluxo A"
    assert len(detail.json()["flow_data"]["nodes"]) == 4

    patch = api_client.patch(
        reverse("chatbot-workflows-detail", kwargs={"pk": wf.id}),
        {"name": "Fluxo Renomeado", "is_active": True},
        format="json",
    )
    assert patch.status_code == 200
    assert patch.json()["name"] == "Fluxo Renomeado"

    dup = api_client.post(reverse("chatbot-workflows-duplicate", kwargs={"pk": wf.id}))
    assert dup.status_code == 201
    dup_id = dup.json()["id"]
    assert dup.json()["name"].startswith("Cópia de")
    assert dup.json()["is_active"] is False

    delete = api_client.delete(reverse("chatbot-workflows-detail", kwargs={"pk": dup_id}))
    assert delete.status_code == 204
    assert not ChatbotWorkflow.all_objects.filter(pk=dup_id).exists()


@pytest.mark.django_db
def test_chatbot_detail_other_tenant_returns_404(api_client):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_b = UserFactory(tenant=tenant_b, email="chatbot-b-detail@example.com")
    wf_a = ChatbotWorkflowFactory(tenant=tenant_a, name="Privado")

    _auth(api_client, user_b)
    resp = api_client.get(reverse("chatbot-workflows-detail", kwargs={"pk": wf_a.id}))
    assert resp.status_code == 404


@pytest.mark.django_db
def test_chatbot_save_rejects_invalid_flow_data(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="chatbot-val@example.com")
    _auth(api_client, user)

    resp = api_client.post(
        reverse("chatbot-workflows-save"),
        {"flow_data": {"nodes": "invalid", "edges": []}},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_flow_engine_runs_geladeira_template():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    ResidentFactory(tenant=tenant, phone_number="5511977665544", name="João")
    ChatbotWorkflowFactory(tenant=tenant, is_active=True, flow_data=GELADEIRA_FLOW)

    with (
        mock.patch(
            "apps.chatbot.services.flow_engine.classify_intent",
            return_value="manutenção",
        ),
        mock.patch("apps.chatbot.services.flow_engine.send_whatsapp_reply") as send,
    ):
        handled = run_chatbot_flow(tenant.id, instance, "5511977665544", "A geladeira não gela")

    assert handled is True
    assert send.call_count == 2
    resident_call = send.call_args_list[0]
    owner_call = send.call_args_list[1]
    assert resident_call[0][1] == "5511977665544"
    assert resident_call[0][2] == "Responsável avisado."
    assert owner_call[0][1] == "5511999887766"
    assert "João" in owner_call[0][2]


@pytest.mark.django_db
def test_flow_engine_returns_false_without_active_workflow():
    tenant = TenantFactory()
    ChatbotWorkflow.all_objects.filter(tenant=tenant).update(is_active=False)
    instance = WhatsappInstanceFactory(tenant=tenant)
    assert run_chatbot_flow(tenant.id, instance, "5511000000000", "oi") is False


@pytest.mark.django_db
def test_seed_system_workflows_idempotent():
    tenant = TenantFactory()
    assert ChatbotWorkflow.all_objects.filter(tenant=tenant, is_system=True).count() == 5
    created = seed_system_workflows(tenant.pk)
    assert created == 0
    assert ChatbotWorkflow.all_objects.filter(tenant=tenant, is_system=True).count() == 5


@pytest.mark.django_db
def test_system_workflow_delete_and_rename_forbidden(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="chatbot-system@example.com")
    system_wf = ChatbotWorkflow.objects.filter(tenant=tenant, is_system=True).first()
    assert system_wf is not None
    _auth(api_client, user)

    delete_resp = api_client.delete(
        reverse("chatbot-workflows-detail", kwargs={"pk": system_wf.id})
    )
    assert delete_resp.status_code == 403

    patch_resp = api_client.patch(
        reverse("chatbot-workflows-detail", kwargs={"pk": system_wf.id}),
        {"name": "Nome Proibido"},
        format="json",
    )
    assert patch_resp.status_code == 403

    toggle_resp = api_client.patch(
        reverse("chatbot-workflows-detail", kwargs={"pk": system_wf.id}),
        {"is_active": True},
        format="json",
    )
    assert toggle_resp.status_code == 200


@pytest.mark.django_db
def test_list_orders_system_first(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="chatbot-order@example.com")
    ChatbotWorkflowFactory(tenant=tenant, name="Custom Z", is_active=False)
    _auth(api_client, user)

    resp = api_client.get(reverse("chatbot-workflows-list"))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 6
    assert data[0]["is_system"] is True


@pytest.mark.django_db
def test_classify_intent_requires_api_key(settings):
    settings.OPENAI_API_KEY = ""
    from apps.chatbot.services.intent_classifier import classify_intent

    with pytest.raises(IntentClassifierError, match="Serviço de IA"):
        classify_intent(message="teste", intents=["a"])


@pytest.mark.django_db
def test_classify_intent_empty_message_skips_openai(settings):
    settings.OPENAI_API_KEY = "sk-test"
    from apps.chatbot.services.intent_classifier import classify_intent

    with mock.patch("openai.OpenAI") as openai_cls:
        result = classify_intent(message="   ", intents=["compra", "duvida"])

    assert result == "compra"
    openai_cls.assert_not_called()


@pytest.mark.django_db
def test_classify_intent_bad_request_returns_fallback(settings):
    settings.OPENAI_API_KEY = "sk-test"
    from openai import BadRequestError
    from apps.chatbot.services.intent_classifier import classify_intent

    with mock.patch("openai.OpenAI") as openai_cls:
        openai_cls.return_value.chat.completions.create.side_effect = BadRequestError(
            "json required",
            response=mock.Mock(status_code=400),
            body=None,
        )
        result = classify_intent(message="quero comprar", intents=["compra", "duvida"])

    assert result == "compra"
