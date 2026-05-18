"""Motor de execução do fluxo visual do chatbot."""

from __future__ import annotations

import logging
import re
from typing import Any

from django.contrib.auth import get_user_model

from apps.chatbot.models import ChatbotWorkflow
from apps.chatbot.services.intent_classifier import IntentClassifierError, classify_intent
from apps.tenants.models import Tenant
from apps.integrations.models import WhatsappInstance
from apps.residents.models import Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply

logger = logging.getLogger(__name__)

User = get_user_model()

MAX_STEPS = 32


def _tenant_owner_phone(tenant_id: int) -> str:
    """Celular do dono: telefone da empresa ou do administrador/usuário do tenant."""
    try:
        tenant = Tenant.objects.get(pk=tenant_id)
        phone = re.sub(r"\D", "", tenant.phone or "")
        if phone:
            return phone
    except Tenant.DoesNotExist:
        pass

    admin = (
        User.objects.filter(tenant_id=tenant_id, is_tenant_admin=True)
        .exclude(phone="")
        .order_by("id")
        .first()
    )
    if admin:
        return re.sub(r"\D", "", admin.phone or "")

    any_user = User.objects.filter(tenant_id=tenant_id).exclude(phone="").order_by("id").first()
    if any_user:
        return re.sub(r"\D", "", any_user.phone or "")
    return ""


def _nodes_by_id(flow_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = flow_data.get("nodes") or []
    return {n["id"]: n for n in nodes if isinstance(n, dict) and n.get("id")}


def _outgoing_edges(flow_data: dict[str, Any], node_id: str) -> list[dict[str, Any]]:
    edges = flow_data.get("edges") or []
    return [e for e in edges if isinstance(e, dict) and e.get("source") == node_id]


def _find_trigger_node(nodes: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for node in nodes.values():
        if node.get("type") == "trigger":
            return node
    return None


def _render_template(template: str, *, name: str, phone: str, text: str) -> str:
    return (
        (template or "")
        .replace("{name}", name)
        .replace("{phone}", phone)
        .replace("{text}", text)
    )


def _execute_node(
    node: dict[str, Any],
    *,
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    text: str,
    flow_data: dict[str, Any],
) -> str | None:
    """Executa nó e retorna id do próximo nó, ou None para encerrar."""
    node_type = node.get("type")
    data = node.get("data") or {}

    if node_type == "trigger":
        outs = _outgoing_edges(flow_data, node["id"])
        return outs[0]["target"] if outs else None

    if node_type == "ai_filter":
        intents = data.get("intents") or []
        if not isinstance(intents, list):
            intents = []
        try:
            chosen = classify_intent(
                message=text,
                intents=[str(i) for i in intents],
                system_prompt=str(data.get("systemPrompt") or ""),
            )
        except IntentClassifierError:
            logger.warning(
                "Classificação de intenção falhou: tenant=%s node=%s",
                tenant_id,
                node.get("id"),
            )
            return None

        outs = _outgoing_edges(flow_data, node["id"])
        for edge in outs:
            edge_data = edge.get("data") or {}
            edge_intent = str(edge_data.get("intent") or "").strip()
            if edge_intent and edge_intent.lower() == chosen.lower():
                return edge["target"]
        if outs:
            return outs[0]["target"]
        return None

    if node_type == "response":
        message = str(data.get("message") or "").strip()
        if message:
            send_whatsapp_reply(instance, phone, message)
        outs = _outgoing_edges(flow_data, node["id"])
        return outs[0]["target"] if outs else None

    if node_type == "owner_alert":
        owner_phone = re.sub(r"\D", "", str(data.get("ownerPhone") or ""))
        if not owner_phone:
            owner_phone = _tenant_owner_phone(tenant_id)
        template = str(
            data.get("messageTemplate")
            or "Alerta: {name} ({phone}) reportou: {text}"
        )
        resident = (
            Resident.objects.filter(tenant_id=tenant_id, phone_number=phone)
            .select_related("market")
            .first()
        )
        name = resident.name if resident else "Morador"
        body = _render_template(template, name=name, phone=phone, text=text)
        if owner_phone and body:
            send_whatsapp_reply(instance, owner_phone, body)
        outs = _outgoing_edges(flow_data, node["id"])
        return outs[0]["target"] if outs else None

    return None


def run_chatbot_flow(
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    text: str,
) -> bool:
    workflow = (
        ChatbotWorkflow.objects.filter(is_active=True)
        .order_by("-updated_at")
        .first()
    )
    if workflow is None:
        return False

    flow_data = workflow.flow_data or {}
    nodes = flow_data.get("nodes") or []
    if not nodes:
        return False

    nodes_map = _nodes_by_id(flow_data)
    trigger = _find_trigger_node(nodes_map)
    if trigger is None:
        logger.warning("Workflow sem nó trigger: tenant=%s workflow=%s", tenant_id, workflow.pk)
        return False

    current_id: str | None = trigger["id"]
    steps = 0
    while current_id and steps < MAX_STEPS:
        steps += 1
        node = nodes_map.get(current_id)
        if node is None:
            break
        current_id = _execute_node(
            node,
            tenant_id=tenant_id,
            instance=instance,
            phone=phone,
            text=text,
            flow_data=flow_data,
        )

    return True
