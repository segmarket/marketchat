"""Geração do arquivo modelo de importação."""

from __future__ import annotations

import io

from openpyxl import Workbook


def build_template_workbook() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "produtos"
    ws.append(["sku", "name", "search_aliases", "price", "status"])
    ws.append(["SKU-001", "Arroz 5kg", "arroz, arroz branco", "24.90", "Ativo"])
    ws.append(["SKU-002", "Feijão 1kg", "feijao, feijão carioca", "8.50", "Inativo"])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
