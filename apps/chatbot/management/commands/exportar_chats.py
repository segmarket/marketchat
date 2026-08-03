from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.chatbot.models import ChatMessageLog

CHUNK_SIZE = 2000

CSV_HEADERS = [
    "Data_Hora",
    "Tenant_Mercado",
    "Condominio",
    "Nome_Morador",
    "Telefone",
    "Remetente",
    "Mensagem",
]

_REMETENTE_BY_DIRECTION = {
    ChatMessageLog.Direction.INBOUND: "MORADOR",
    ChatMessageLog.Direction.OUTBOUND: "BOT",
    ChatMessageLog.Direction.AGENT: "ATENDENTE",
}


class Command(BaseCommand):
    help = (
        "Exporta o histórico completo de chats (ChatMessageLog) de todos os tenants "
        "para um CSV na raiz do projeto, com streaming via iterator (sem OOM)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Caminho do CSV (padrão: export_chats_YYYYMMDD.csv na raiz do projeto).",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=CHUNK_SIZE,
            help=f"Tamanho do lote do iterator (padrão: {CHUNK_SIZE}).",
        )

    def handle(self, *args, **options):
        chunk_size = max(100, int(options["chunk_size"]))
        output = (options.get("output") or "").strip()
        if output:
            out_path = Path(output).expanduser().resolve()
        else:
            stamp = timezone.localtime().strftime("%Y%m%d")
            out_path = Path(settings.BASE_DIR) / f"export_chats_{stamp}.csv"

        out_path.parent.mkdir(parents=True, exist_ok=True)

        qs = (
            ChatMessageLog.all_objects.select_related(
                "tenant",
                "session",
                "resident",
                "market",
            )
            .order_by("created_at", "id")
        )

        total = qs.count()
        self.stdout.write(
            f"Exportando {total} mensagem(ns) para {out_path} "
            f"(chunk_size={chunk_size})..."
        )

        exported = 0
        with out_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(CSV_HEADERS)

            for log in qs.iterator(chunk_size=chunk_size):
                writer.writerow(self._row(log))
                exported += 1
                if exported % chunk_size == 0:
                    self.stdout.write(
                        f"  … {exported}/{total} mensagens exportadas"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído: {exported} mensagem(ns) em {out_path}"
            )
        )

    def _row(self, log: ChatMessageLog) -> list[str]:
        created = log.created_at
        if timezone.is_aware(created):
            created = timezone.localtime(created)
        data_hora = created.strftime("%d/%m/%Y %H:%M")

        tenant_name = ""
        if log.tenant_id and log.tenant is not None:
            tenant_name = log.tenant.name or ""

        condominio = ""
        if log.market_id and log.market is not None:
            condominio = log.market.name or ""

        nome = ""
        telefone = ""
        if log.resident_id and log.resident is not None:
            nome = log.resident.name or ""
            telefone = log.resident.phone_number or ""
        if log.session_id and log.session is not None:
            telefone = telefone or (log.session.phone_number or "")

        remetente = _REMETENTE_BY_DIRECTION.get(log.direction, log.direction)
        mensagem = log.message_text or ""
        if not mensagem and log.message_kind == ChatMessageLog.MessageKind.IMAGE:
            mensagem = "[imagem]"

        return [
            data_hora,
            tenant_name,
            condominio,
            nome,
            telefone,
            remetente,
            mensagem,
        ]
