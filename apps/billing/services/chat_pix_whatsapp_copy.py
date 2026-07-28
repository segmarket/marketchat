"""Textos WhatsApp para cobrança PIX gerada no chat (duas mensagens)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def _format_brl(value: str | Decimal) -> str:
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    return f"R$ {amount:.2f}".replace(".", ",")


def format_items_summary(items_summary: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in items_summary:
        name = str(item.get("name") or "").strip()
        try:
            qty = int(item.get("quantity") or 0)
        except (TypeError, ValueError):
            qty = 0
        if name == "Cobrança avulsa" and qty == 1:
            parts.append("cobrança avulsa")
        elif name:
            parts.append(f"{name} ({qty}x)")
    return ", ".join(parts)


def build_chat_pix_summary_message(
    *,
    amount: str,
    invoice_url: str,
    items_summary: list[dict[str, Any]],
) -> str:
    """Mensagem 1: resumo, total, link e instrução (sem BR Code)."""
    items_label = format_items_summary(items_summary)
    total = _format_brl(amount)
    lines = ["Aqui está o resumo do seu pedido."]
    if items_label:
        lines.append(items_label)
    lines.append(f"Total: {total}")

    url = (invoice_url or "").strip()
    if url:
        lines.append("")
        lines.append(f"Acesse o link de pagamento: {url}")

    lines.append("")
    lines.append(
        "Ou utilize o código PIX Copia e Cola que enviei na mensagem abaixo ⬇️",
    )
    return "\n".join(lines)


def build_chat_pix_code_message(pix_copia_e_cola: str) -> str:
    """Mensagem 2: apenas o payload PIX."""
    return (pix_copia_e_cola or "").strip()
