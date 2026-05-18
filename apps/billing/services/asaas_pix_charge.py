from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from django.conf import settings

from apps.billing.models import AsaasSubaccount
from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient
from apps.billing.services.asaas_webhook_payload import cart_external_reference
from apps.billing.services.asaas_subaccount import format_asaas_error
from apps.residents.models import Resident
from apps.sales.models import Cart

logger = logging.getLogger(__name__)


class PixChargeError(Exception):
    pass


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
    try:
        qr = client.get_payment_pix_qrcode(payment_id)
    except AsaasAPIError as exc:
        logger.warning("Asaas pixQrCode falhou payment=%s: %s", payment_id, exc.payload)
        return ""
    return extract_pix_copy_paste(qr)


def use_main_account_pix_dev() -> bool:
    """
    Cobrança na conta principal (sem split). Só ativo com DEBUG=True e flag explícita.
    Nunca use em produção.
    """
    if not getattr(settings, "DEBUG", False):
        return False
    return bool(getattr(settings, "ASAAS_PIX_USE_MAIN_ACCOUNT_IN_DEV", False))


def _validate_subaccount_for_pix(subaccount: AsaasSubaccount) -> None:
    if subaccount.account_status == AsaasSubaccount.AccountStatus.REJECTED:
        raise PixChargeError(
            "A conta Pix do mercado foi rejeitada no Asaas. Atualize os dados em Configurações.",
        )
    if subaccount.account_status == AsaasSubaccount.AccountStatus.PENDING:
        raise PixChargeError(
            "A subconta Pix do mercado ainda está em análise no Asaas (sandbox pode levar alguns "
            "minutos após o cadastro). Enquanto isso, o QR Code Pix pode não ser gerado. "
            "Confira o painel Asaas → Minha conta / Subcontas.",
        )


def create_cart_pix_charge(cart: Cart, resident: Resident) -> str:
    """
    Cria cobrança Pix no Asaas.
    Produção: split 100% para wallet da subconta do tenant.
    Dev (opcional): conta principal sem split — ver ASAAS_PIX_USE_MAIN_ACCOUNT_IN_DEV.
    Retorna o código Pix copia e cola.
    """
    if cart.total_value <= Decimal("0"):
        raise PixChargeError("Carrinho sem valor para cobrança.")

    dev_main_account = use_main_account_pix_dev()
    subaccount: AsaasSubaccount | None = None

    if not dev_main_account:
        try:
            subaccount = resident.tenant.asaas_subaccount
        except AsaasSubaccount.DoesNotExist as exc:
            raise PixChargeError(
                "Pagamento Pix ainda não está configurado para este mercado.",
            ) from exc

        wallet_id = (subaccount.asaas_wallet_id or "").strip()
        if not wallet_id:
            raise PixChargeError(
                "Configure o recebimento Pix em Configurações antes de finalizar compras.",
            )
        _validate_subaccount_for_pix(subaccount)
    else:
        logger.warning(
            "DEV: Pix carrinho #%s sem split (conta principal Asaas). "
            "Desative ASAAS_PIX_USE_MAIN_ACCOUNT_IN_DEV em produção.",
            cart.id,
        )

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
    if not dev_main_account and subaccount is not None:
        wallet_id = (subaccount.asaas_wallet_id or "").strip()
        body["split"] = [
            {
                "walletId": wallet_id,
                "percentualValue": 100,
            },
        ]

    try:
        payment = client.create_payment(body)
    except AsaasAPIError as exc:
        logger.warning("Erro Asaas create_payment: %s", exc.payload)
        raise PixChargeError(format_asaas_error(exc)) from exc

    payment_id = str(payment.get("id") or "").strip()
    pix_code = extract_pix_copy_paste(payment)
    if not pix_code and payment_id:
        pix_code = fetch_pix_copy_paste(client, payment_id)

    if not pix_code:
        invoice = str(payment.get("invoiceUrl") or "").strip()
        if invoice:
            raise PixChargeError(
                "Cobrança criada, mas o Pix ainda não está disponível. "
                f"Tente pelo link: {invoice}"
            )
        raise PixChargeError(
            "Pix não disponível. Verifique no painel Asaas se a subconta Pix está aprovada "
            "e se a chave Pix está ativa.",
        )

    cart.asaas_billing_id = payment_id
    cart.status = Cart.Status.AWAITING_PAYMENT
    cart.save(update_fields=["asaas_billing_id", "status", "updated_at"])
    return pix_code
