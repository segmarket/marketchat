from __future__ import annotations

from apps.billing.services.asaas_client import AsaasAPIError

_CARD_ERROR_MESSAGES: dict[str, str] = {
    "invalid_creditCard": (
        "Os dados do cartão não foram aceitos. "
        "Confira número, validade, CVV e nome igual ao impresso no cartão."
    ),
    "invalid_holderInfo": (
        "Dados do titular incompletos ou incorretos. "
        "Revise CPF/CNPJ, endereço e telefone."
    ),
    "invalid_expiryDate": "Data de validade inválida ou expirada.",
    "invalid_cvv": "CVV inválido.",
}


def _iter_asaas_errors(payload: object) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        return []
    errors = payload.get("errors")
    if not isinstance(errors, list):
        return []
    result: list[dict[str, str]] = []
    for item in errors:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "code": str(item.get("code", "")).strip(),
                "description": str(item.get("description", "")).strip(),
            }
        )
    return result


def format_asaas_card_error(exc: AsaasAPIError) -> str:
    """Mensagem amigável para falhas de cartão no cadastro (sem citar o provedor)."""
    messages: list[str] = []
    for err in _iter_asaas_errors(exc.payload):
        code = err["code"]
        if code in _CARD_ERROR_MESSAGES:
            messages.append(_CARD_ERROR_MESSAGES[code])
        elif err["description"]:
            messages.append(err["description"])
    if messages:
        return " · ".join(messages[:3])
    return "Não foi possível validar o cartão. Verifique os dados e tente novamente."


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
