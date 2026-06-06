from __future__ import annotations

from apps.billing.services.asaas_client import AsaasAPIError


def format_asaas_error(exc: AsaasAPIError) -> str:
    payload = exc.payload
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            descriptions = [
                str(item.get("description", "")).strip()
                for item in errors
                if isinstance(item, dict) and item.get("description")
            ]
            if descriptions:
                return " · ".join(descriptions[:3])
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
    return "Não foi possível concluir a operação no Asaas. Verifique os dados informados."
