"""Relatório read-only de instâncias WhatsApp MarketChat vs Evolution (não apaga nada)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient


class Command(BaseCommand):
    help = (
        "Lista instâncias WhatsApp locais e remotas (Evolution GET /instance/all). "
        "Não deleta nem reconecta. Use para diagnosticar webhooks 403 / órfãs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-remote",
            action="store_true",
            help="Só lista o banco MarketChat.",
        )

    def handle(self, *args, **options):
        self.stdout.write("=== MarketChat (banco) ===")
        local_ids: set[str] = set()
        for inst in WhatsappInstance.all_objects.select_related("tenant").order_by("id"):
            local_ids.add((inst.instance_id or "").strip())
            webhook_ok = bool(inst.webhook_url) and bool(inst.webhook_secret)
            self.stdout.write(
                "instanceId={id} instanceName={name} tenant_id={tenant} "
                "user_hint={slug} active={active} status={status} "
                "webhook_url={url_ok} secret={secret} last_webhook={webhook}".format(
                    id=inst.instance_id or "-",
                    name=inst.instance_name,
                    tenant=inst.tenant_id,
                    slug=getattr(inst.tenant, "slug", ""),
                    active=inst.is_active,
                    status=inst.connection_status,
                    url_ok="yes" if webhook_ok else "no",
                    secret="set" if inst.webhook_secret else "missing",
                    webhook=inst.last_webhook_at or "-",
                )
            )

        if options["skip_remote"]:
            return

        self.stdout.write("\n=== Evolution GET /instance/all ===")
        try:
            rows = EvolutionClient().fetch_instances()
        except Exception as exc:
            self.stderr.write(f"Falha ao listar Evolution (não destrutivo): {exc}")
            return

        remote_ids: set[str] = set()
        for row in rows:
            remote_id = str(row.get("instanceId") or row.get("id") or "").strip()
            remote_name = str(row.get("instanceName") or row.get("name") or "")
            connected = row.get("connected")
            logged_in = row.get("loggedIn") if "loggedIn" in row else row.get("logged_in")
            remote_ids.add(remote_id)
            match = "local" if remote_id in local_ids else "ORPHAN_REMOTE"
            self.stdout.write(
                f"instanceId={remote_id or '-'} instanceName={remote_name} "
                f"connected={connected} loggedIn={logged_in} match={match}"
            )

        orphans = {i for i in remote_ids if i and i not in local_ids}
        if orphans:
            self.stdout.write(
                "\nInstâncias remotas sem registro MarketChat (não removidas): "
                + ", ".join(sorted(orphans))
            )
        else:
            self.stdout.write("\nNenhuma instância remota órfã detectada.")
