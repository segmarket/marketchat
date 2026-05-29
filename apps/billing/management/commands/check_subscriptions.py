from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.billing.services.subscription_enforcement import (
    enforce_tenant_suspension,
    iter_tenants_pending_suspension,
    suspension_reason_for_tenant,
)
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = (
        "Suspende tenants com trial vencido ou fatura em atraso (fora da carência), "
        "desconecta WhatsApp na Evolution e envia e-mail ao administrador."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Lista tenants elegíveis sem suspender.",
        )
        parser.add_argument(
            "--tenant-id",
            type=int,
            default=None,
            help="Processa apenas um tenant (debug).",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        tenant_id = options.get("tenant_id")
        now = timezone.now()

        pending = list(iter_tenants_pending_suspension(now=now))
        if tenant_id is not None:
            tenant = Tenant.objects.filter(pk=tenant_id).first()
            if tenant is None:
                self.stderr.write(self.style.ERROR(f"Tenant {tenant_id} não encontrado."))
                return
            reason = suspension_reason_for_tenant(tenant, now=now)
            if not reason:
                self.stdout.write(
                    self.style.WARNING(
                        f"Tenant {tenant_id} não está elegível para suspensão no momento.",
                    ),
                )
                return
            from apps.billing.services.subscription_enforcement import PendingSuspension

            pending = [PendingSuspension(tenant=tenant, reason=reason)]

        if not pending:
            self.stdout.write(self.style.SUCCESS("Nenhum tenant elegível para suspensão."))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"[dry-run] {len(pending)} tenant(s) seriam suspensos:"),
            )
            for item in pending:
                self.stdout.write(
                    f"  tenant_id={item.tenant.pk} slug={item.tenant.slug} reason={item.reason}",
                )
            return

        suspended = 0
        skipped = 0
        for item in pending:
            if enforce_tenant_suspension(item.tenant, reason=item.reason, send_email=True):
                suspended += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído: {suspended} suspenso(s), {skipped} ignorado(s) (falha Evolution ou já processado).",
            ),
        )


# Agendamento sugerido (cron diário às 02:00):
# 0 2 * * * cd /caminho/marketchat && python manage.py check_subscriptions
