from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.chatbot.services.inactivity_followup import (
    DEFAULT_MAX_IDLE_MINUTES,
    DEFAULT_MIN_IDLE_MINUTES,
    process_inactivity_followups,
)


class Command(BaseCommand):
    help = (
        "Encerra sessões WhatsApp inativas (5–15 min) em fluxos não-Pix: envia mensagem "
        "educada e reseta o estado para ACTIVE_BOT. Rode a cada 2–3 minutos via cron."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-minutes",
            type=int,
            default=DEFAULT_MIN_IDLE_MINUTES,
            help="Inatividade mínima em minutos (padrão: 5).",
        )
        parser.add_argument(
            "--max-minutes",
            type=int,
            default=DEFAULT_MAX_IDLE_MINUTES,
            help="Não processar sessões inativas há mais que N minutos (padrão: 15).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula sem enviar WhatsApp nem alterar sessões.",
        )

    def handle(self, *args, **options):
        min_minutes = max(1, int(options["min_minutes"]))
        max_minutes = max(min_minutes + 1, int(options["max_minutes"]))
        dry_run = bool(options["dry_run"])

        result = process_inactivity_followups(
            min_idle_minutes=min_minutes,
            max_idle_minutes=max_minutes,
            dry_run=dry_run,
        )

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Sessões analisadas: {result.scanned}. "
                f"Encerradas por inatividade: {result.sent}. "
                f"Ignoradas: {result.skipped}. Erros: {result.errors}.",
            ),
        )
