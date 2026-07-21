"""Re-subscribe webhooks Evolution nas instâncias ativas (ex.: incluir PRESENCE)."""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient
from apps.integrations.services.provisioning import build_webhook_base_url
from apps.integrations.services.restart import _instance_webhook_url


class Command(BaseCommand):
    help = (
        "Reaplica EVOLUTION_WEBHOOK_EVENTS (connect_instance) em todas as "
        "instâncias WhatsApp ativas, sem recriar a sessão. Use após adicionar "
        "PRESENCE ao default para clientes já provisionados."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Lista instâncias sem chamar a API Evolution.",
        )
        parser.add_argument(
            "--tenant-id",
            type=int,
            default=None,
            help="Limitar a um tenant específico.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        tenant_id = options.get("tenant_id")
        events = list(
            getattr(settings, "EVOLUTION_WEBHOOK_EVENTS", None)
            or EvolutionClient.DEFAULT_EVENTS
        )

        qs = WhatsappInstance.objects.filter(is_active=True).order_by("id")
        if tenant_id is not None:
            qs = qs.filter(tenant_id=tenant_id)

        total = qs.count()
        self.stdout.write(f"Instâncias ativas: {total}; events={events}")
        if dry_run:
            for inst in qs.iterator():
                self.stdout.write(
                    f"  [dry-run] id={inst.id} tenant={inst.tenant_id} "
                    f"name={inst.instance_name}",
                )
            return

        client = EvolutionClient()
        ok = 0
        failed = 0
        for inst in qs.iterator():
            webhook_url = _instance_webhook_url(inst)
            if not webhook_url:
                webhook_url = EvolutionClient.build_webhook_url(
                    build_webhook_base_url(),
                    inst.webhook_secret,
                )
            if not (inst.api_key or "").strip():
                self.stderr.write(
                    self.style.WARNING(
                        f"Skip id={inst.id}: sem api_key",
                    ),
                )
                failed += 1
                continue
            try:
                client.connect_instance(
                    instance_api_key=inst.api_key,
                    webhook_url=webhook_url,
                    events=events,
                    phone="",
                    immediate=False,
                )
                ok += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"OK id={inst.id} tenant={inst.tenant_id} "
                        f"name={inst.instance_name}",
                    ),
                )
            except Exception as exc:
                failed += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"FAIL id={inst.id} name={inst.instance_name}: {exc}",
                    ),
                )

        self.stdout.write(f"Concluído: ok={ok} failed={failed}")
