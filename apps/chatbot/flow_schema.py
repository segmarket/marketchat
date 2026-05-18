"""Validação do JSON flow_data (React Flow)."""

from __future__ import annotations

import re
from typing import Any

ALLOWED_NODE_TYPES = frozenset({"trigger", "ai_filter", "response", "owner_alert"})


def _is_dict(value: Any) -> bool:
    return isinstance(value, dict)


def _is_list(value: Any) -> bool:
    return isinstance(value, list)


def validate_flow_data(flow_data: Any) -> dict[str, Any]:
    if not _is_dict(flow_data):
        raise ValueError("flow_data deve ser um objeto JSON.")

    nodes = flow_data.get("nodes")
    edges = flow_data.get("edges")
    if not _is_list(nodes):
        raise ValueError("flow_data.nodes deve ser uma lista.")
    if not _is_list(edges):
        raise ValueError("flow_data.edges deve ser uma lista.")

    node_ids: set[str] = set()
    for idx, node in enumerate(nodes):
        if not _is_dict(node):
            raise ValueError(f"Nó na posição {idx} inválido.")
        node_id = node.get("id")
        node_type = node.get("type")
        if not node_id or not isinstance(node_id, str):
            raise ValueError(f"Nó na posição {idx} sem id.")
        if node_type not in ALLOWED_NODE_TYPES:
            raise ValueError(f"Tipo de nó não permitido: {node_type!r}.")
        data = node.get("data")
        if data is not None and not _is_dict(data):
            raise ValueError(f"data do nó {node_id} deve ser objeto.")
        if node_type == "owner_alert" and _is_dict(data):
            phone = str(data.get("ownerPhone") or "")
            digits = re.sub(r"\D", "", phone)
            if phone and digits != phone:
                raise ValueError(f"ownerPhone do nó {node_id} deve conter apenas dígitos.")
        node_ids.add(node_id)

    for idx, edge in enumerate(edges):
        if not _is_dict(edge):
            raise ValueError(f"Aresta na posição {idx} inválida.")
        for key in ("id", "source", "target"):
            if not edge.get(key):
                raise ValueError(f"Aresta na posição {idx} sem {key}.")
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            raise ValueError(f"Aresta {edge.get('id')} referencia nó inexistente.")

    viewport = flow_data.get("viewport")
    if viewport is not None and not _is_dict(viewport):
        raise ValueError("flow_data.viewport deve ser um objeto.")

    return flow_data
