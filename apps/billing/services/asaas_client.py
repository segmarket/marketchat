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

    def create_customer(self, body: Mapping[str, Any]) -> dict[str, Any]:
        data = self._request("POST", "/customers", dict(body))
        assert isinstance(data, dict)
        return data

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        data = self._request("GET", f"/customers/{customer_id}")
        assert isinstance(data, dict)
        return data

    def create_payment(self, body: Mapping[str, Any]) -> dict[str, Any]:
        data = self._request("POST", "/payments", dict(body))
        assert isinstance(data, dict)
        return data

    def get_payment(self, payment_id: str) -> dict[str, Any]:
        data = self._request("GET", f"/payments/{payment_id}")
        if data is None:
            return {}
        assert isinstance(data, dict)
        return data

    def get_payment_pix_qrcode(self, payment_id: str) -> dict[str, Any]:
        """QR Code Pix dinâmico (payload copia e cola) — chamada separada após criar cobrança."""
        data = self._request("GET", f"/payments/{payment_id}/pixQrCode")
        if data is None:
            return {}
        assert isinstance(data, dict)
        return data

    def tokenize_credit_card(self, body: Mapping[str, Any]) -> dict[str, Any]:
        data = self._request("POST", "/creditCard/tokenizeCreditCard", dict(body))
        assert isinstance(data, dict)
        return data

    def create_subscription(self, body: Mapping[str, Any]) -> dict[str, Any]:
        data = self._request("POST", "/subscriptions", dict(body))
        assert isinstance(data, dict)
        return data

    def list_payments(self, **params: Any) -> dict[str, Any]:
        data = self._request("GET", "/payments", params=params)
        assert isinstance(data, dict)
        return data

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        data = self._request("GET", f"/subscriptions/{subscription_id}")
        assert isinstance(data, dict)
        return data

    def create_subaccount(self, body: Mapping[str, Any]) -> dict[str, Any]:
        data = self._request("POST", "/accounts", dict(body))
        assert isinstance(data, dict)
        return data

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
        assert isinstance(data, dict)
        return data
