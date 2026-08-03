import csv
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.chatbot.models import ChatMessageLog
from apps.tenants.context import tenant_scope
from tests.factories import (
    ChatSessionFactory,
    MarketFactory,
    ResidentFactory,
    TenantFactory,
)


@pytest.mark.django_db
def test_exportar_chats_writes_csv_with_expected_columns(tmp_path: Path):
    tenant = TenantFactory(name="Mercado Alpha")
    market = MarketFactory(tenant=tenant, name="Portal das Flores")
    session = ChatSessionFactory(tenant=tenant, phone_number="5511999887766")
    resident = ResidentFactory(
        tenant=tenant,
        market=market,
        phone_number="5511999887766",
        name="Ana Silva",
    )

    with tenant_scope(tenant.id):
        ChatMessageLog.all_objects.create(
            tenant=tenant,
            session=session,
            resident=resident,
            market=market,
            message_text="Oi, produto vencido\nlinha 2",
            direction=ChatMessageLog.Direction.INBOUND,
        )
        ChatMessageLog.all_objects.create(
            tenant=tenant,
            session=session,
            resident=resident,
            market=market,
            message_text="Entendido. Pode enviar uma foto?",
            direction=ChatMessageLog.Direction.OUTBOUND,
        )
        ChatMessageLog.all_objects.create(
            tenant=tenant,
            session=session,
            resident=resident,
            market=market,
            message_text="Vou verificar",
            direction=ChatMessageLog.Direction.AGENT,
        )

    out = tmp_path / "export_chats_test.csv"
    call_command("exportar_chats", output=str(out), chunk_size=2)

    assert out.exists()
    with out.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))

    assert rows[0] == [
        "Data_Hora",
        "Tenant_Mercado",
        "Condominio",
        "Nome_Morador",
        "Telefone",
        "Remetente",
        "Mensagem",
    ]
    assert len(rows) == 4  # header + 3 messages

    by_sender = {r[5]: r for r in rows[1:]}
    assert by_sender["MORADOR"][1] == "Mercado Alpha"
    assert by_sender["MORADOR"][2] == "Portal das Flores"
    assert by_sender["MORADOR"][3] == "Ana Silva"
    assert by_sender["MORADOR"][4] == "5511999887766"
    assert "produto vencido" in by_sender["MORADOR"][6]
    assert "linha 2" in by_sender["MORADOR"][6]
    assert by_sender["BOT"][5] == "BOT"
    assert by_sender["ATENDENTE"][5] == "ATENDENTE"
    # DD/MM/YYYY HH:MM
    assert "/" in by_sender["MORADOR"][0]
