from __future__ import annotations

import logging
import time
from datetime import date
from decimal import Decimal

from django.conf import settings

from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient
from apps.billing.services.asaas_webhook_payload import cart_external_reference
from apps.billing.services.asaas_errors import format_asaas_error
from apps.residents.models import Resident
from apps.sales.models import Cart

logger = logging.getLogger(__name__)

PIX_QR_FETCH_RETRIES = 4
PIX_QR_FETCH_DELAY_SECONDS = 1.5


class PixChargeError(Exception):
    pass


def _pix_setup_required_message() -> str:
    return (
        "A conta Asaas de produção não está habilitada para cobranças Pix. "
        "No painel Asaas (Conta → Pix → Minhas chaves), cadastre uma chave Pix "
        "e confirme que a conta pode receber cobranças via Pix."
    )


def _asaas_pix_charge_not_allowed(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    errors = payload.get("errors")
    if not isinstance(errors, list):
        return False
    for item in errors:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").lower()
        description = str(item.get("description") or "").lower()
        if code == "invalid_action" and "pix" in description:
            return True
    return False


def _digits_only(value: str) -> str:
    return "".join(c for c in value if c.isdigit())


def get_or_create_resident_customer(resident: Resident, client: AsaasClient) -> str:
    if resident.asaas_customer_id:
        return resident.asaas_customer_id

    phone = _digits_only(resident.phone_number)
    cpf = _digits_only(getattr(settings, "ASAAS_RESIDENT_DEFAULT_CPF", "11144477735"))
    if len(cpf) not in (11, 14):
        raise PixChargeError(
            "CPF padrão para cobrança inválido. Configure ASAAS_RESIDENT_DEFAULT_CPF no .env "
            "(11 dígitos para CPF válido no sandbox).",
        )
    body = {
        "name": (resident.name or "Morador").strip()[:100],
        "mobilePhone": phone[-11:] if len(phone) >= 11 else phone,
        "cpfCnpj": cpf,
        "notificationDisabled": True,
    }
    try:
        data = client.create_customer(body)
    except AsaasAPIError as exc:
        raise PixChargeError(format_asaas_error(exc)) from exc

    customer_id = str(data.get("id") or "").strip()
    if not customer_id:
        raise PixChargeError("Asaas não retornou o cliente.")

    resident.asaas_customer_id = customer_id
    resident.save(update_fields=["asaas_customer_id", "updated_at"])
    return customer_id


def extract_pix_copy_paste(payment: dict) -> str:
    """Extrai copia e cola de resposta de cobrança ou de GET /pixQrCode."""
    for key in ("pixCopiaECola", "payload", "copyPaste", "emv"):
        val = payment.get(key)
        if isinstance(val, str) and val.strip() and not val.strip().startswith("/9j/"):
            return val.strip()
    pix = payment.get("pixTransaction")
    if isinstance(pix, dict):
        for key in ("payload", "qrCode", "pixCopiaECola", "emv"):
            val = pix.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def fetch_pix_copy_paste(client: AsaasClient, payment_id: str) -> str:
    """O Asaas geralmente exige GET /payments/{id}/pixQrCode após criar a cobrança."""
    if not payment_id:
        return ""
    for attempt in range(PIX_QR_FETCH_RETRIES):
        try:
            qr = client.get_payment_pix_qrcode(payment_id)
        except AsaasAPIError as exc:
            if _asaas_pix_charge_not_allowed(exc.payload):
                logger.warning(
                    "Asaas pixQrCode: cobrança sem Pix habilitado payment=%s",
                    payment_id,
                )
                raise PixChargeError(_pix_setup_required_message()) from exc
            logger.warning(
                "Asaas pixQrCode tentativa %s/%s payment=%s: %s",
                attempt + 1,
                PIX_QR_FETCH_RETRIES,
                payment_id,
                exc.payload,
            )
            if attempt < PIX_QR_FETCH_RETRIES - 1:
                time.sleep(PIX_QR_FETCH_DELAY_SECONDS)
            continue
        pix_code = extract_pix_copy_paste(qr)
        if pix_code:
            return pix_code
        if attempt < PIX_QR_FETCH_RETRIES - 1:
            time.sleep(PIX_QR_FETCH_DELAY_SECONDS)
    return ""


def create_cart_pix_charge(cart: Cart, resident: Resident) -> str:
    """
    Cria cobrança Pix na conta master do Asaas (sem split).
    Retorna o código Pix copia e cola.
    """
    if cart.total_value <= Decimal("0"):
        raise PixChargeError("Carrinho sem valor para cobrança.")

    client = AsaasClient()
    customer_id = get_or_create_resident_customer(resident, client)

    body: dict = {
        "customer": customer_id,
        "billingType": "PIX",
        "value": float(cart.total_value),
        "dueDate": date.today().isoformat(),
        "description": f"Compra mercado — carrinho #{cart.id}",
        "externalReference": cart_external_reference(cart.id),
    }

    try:
        payment = client.create_payment(body)
    except AsaasAPIError as exc:
        logger.warning("Erro Asaas create_payment: %s", exc.payload)
        raise PixChargeError(format_asaas_error(exc)) from exc

    payment_id = str(payment.get("id") or "").strip()
    billing_type = str(payment.get("billingType") or "").upper()
    if billing_type and billing_type != "PIX":
        logger.warning(
            "Asaas create_payment retornou billingType=%s (esperado PIX) payment=%s cart=%s",
            billing_type,
            payment_id,
            cart.id,
        )

    pix_code = extract_pix_copy_paste(payment)
    if not pix_code and payment_id:
        try:
            pix_code = fetch_pix_copy_paste(client, payment_id)
        except PixChargeError:
            raise

    if not pix_code:
        invoice = str(payment.get("invoiceUrl") or "").strip()
        hint = _pix_setup_required_message()
        if invoice:
            raise PixChargeError(
                "Cobrança criada no Asaas, mas o código Pix não foi gerado. "
                f"{hint} "
                f"Link da cobrança: {invoice}"
            )
        raise PixChargeError(hint)

    cart.asaas_billing_id = payment_id
    cart.status = Cart.Status.AWAITING_PAYMENT
    cart.save(update_fields=["asaas_billing_id", "status", "updated_at"])
    return pix_code
