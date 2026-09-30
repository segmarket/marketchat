from __future__ import annotations

import logging
from typing import Any, Mapping

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AsaasAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class AsaasClient:
    """Cliente HTTP mínimo para a API v3 do Asaas."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or settings.ASAAS_API_URL).rstrip("/")
        self.api_key = api_key or settings.ASAAS_API_KEY

    def _headers(self) -> dict[str, str]:
        key = (self.api_key or "").strip()
        if not key:
            raise AsaasAPIError(
                "ASAAS_API_KEY não está definida ou está vazia. "
                "No painel Asaas (Integrações → Chaves de API) gere uma chave e defina no .env da raiz do projeto. "
                "Sandbox: a chave costuma começar com $aact_hmlg_ (o $ faz parte do token).",
            )
        return {
            "Content-Type": "application/json",
            "access_token": key,
        }

    def _request(
        self,
        method: str,
        path: str,
        json: Mapping[str, Any] | None = None,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = requests.request(
                method,
                url,
                json=json,
                params=params,
                headers=self._headers(),
                timeout=90,
            )
        except requests.RequestException as exc:
            raise AsaasAPIError(f"Falha de rede Asaas: {exc}") from exc
        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            logger.warning("Asaas erro HTTP %s: %s", response.status_code, payload)
            raise AsaasAPIError(
                "Erro na API Asaas",
                status_code=response.status_code,
                payload=payload,
            )
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    @staticmethod
    def _require_dict_response(data: Any, *, context: str) -> dict[str, Any]:
        if isinstance(data, dict):
            return data
        raise AsaasAPIError(
            f"Resposta inválida do Asaas ({context})",
            payload=data,
        )

    def create_customer(self, body: Mapping[str, Any]) -> dict[str, Any]:
        data = self._request("POST", "/customers", dict(body))
        return self._require_dict_response(data, context="create_customer")

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        data = self._request("GET", f"/customers/{customer_id}")
        return self._require_dict_response(data, context="get_customer")

    def create_payment(self, body: Mapping[str, Any]) -> dict[str, Any]:
        data = self._request("POST", "/payments", dict(body))
        return self._require_dict_response(data, context="create_payment")

    def get_payment(self, payment_id: str) -> dict[str, Any]:
        data = self._request("GET", f"/payments/{payment_id}")
        if data is None:
            return {}
        return self._require_dict_response(data, context="get_payment")

    def get_payment_pix_qrcode(self, payment_id: str) -> dict[str, Any]:
        """QR Code Pix dinâmico (payload copia e cola) — chamada separada após criar cobrança."""
        data = self._request("GET", f"/payments/{payment_id}/pixQrCode")
        if data is None:
            return {}
        return self._require_dict_response(data, context="get_payment_pix_qrcode")

    def pay_with_credit_card(self, payment_id: str, body: Mapping[str, Any]) -> dict[str, Any]:
        """
        Paga uma cobrança existente na hora (POST /payments/{id}/payWithCreditCard).
        Não repetir sem antes consultar a cobrança: a chamada processa uma transação real.
        """
        data = self._request("POST", f"/payments/{payment_id}/payWithCreditCard", dict(body))
        return self._require_dict_response(data, context="pay_with_credit_card")

    def tokenize_credit_card(self, body: Mapping[str, Any]) -> dict[str, Any]:
        data = self._request("POST", "/creditCard/tokenizeCreditCard", dict(body))
        return self._require_dict_response(data, context="tokenize_credit_card")

    def create_subscription(self, body: Mapping[str, Any]) -> dict[str, Any]:
        data = self._request("POST", "/subscriptions", dict(body))
        return self._require_dict_response(data, context="create_subscription")

    def list_payments(self, **params: Any) -> dict[str, Any]:
        data = self._request("GET", "/payments", params=params)
        return self._require_dict_response(data, context="list_payments")

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        data = self._request("GET", f"/subscriptions/{subscription_id}")
        return self._require_dict_response(data, context="get_subscription")

    def cancel_subscription(self, subscription_id: str) -> dict[str, Any]:
        data = self._request("DELETE", f"/subscriptions/{subscription_id}")
        if data is None:
            return {"deleted": True, "id": subscription_id}
        return self._require_dict_response(data, context="cancel_subscription")

    def update_subscription(
        self,
        subscription_id: str,
        body: Mapping[str, Any],
    ) -> dict[str, Any]:
        data = self._request("PUT", f"/subscriptions/{subscription_id}", dict(body))
        if data is None:
            return {}
        return self._require_dict_response(data, context="update_subscription")

    def create_transfer(self, body: Mapping[str, Any]) -> dict[str, Any]:
        data = self._request("POST", "/transfers", dict(body))
        return self._require_dict_response(data, context="create_transfer")

    def update_subscription_credit_card(
        self,
        subscription_id: str,
        body: Mapping[str, Any],
    ) -> dict[str, Any]:
        data = self._request(
            "PUT",
            f"/subscriptions/{subscription_id}/creditCard",
            dict(body),
        )
        if data is None:
            return {}
        return self._require_dict_response(data, context="update_subscription_credit_card")
