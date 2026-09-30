from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.billing.services.subscription_enforcement import (
    PendingSuspension,
    attempt_pending_whatsapp_logout,
    block_canceled_tenant,
    enforce_tenant_suspension,
    iter_canceled_tenants_pending_block,
    iter_tenants_pending_suspension,
    iter_tenants_pending_suspension_email,
    iter_tenants_pending_whatsapp_logout,
    send_suspension_email,
    suspension_reason_for_tenant,
)
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = (
        "Ciclo de inadimplência: (1) suspende tenants com trial vencido ou fatura em atraso "
        "fora da carência e envia e-mail; (2) bloqueia CANCELED após o trial; (3) envia o "
        "e-mail de suspensão a quem foi suspenso sem aviso (ex.: na request); (4) reexecuta "
        "logouts Evolution pendentes. Idempotente: pode rodar a cada hora."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Lista o que seria feito sem alterar nada.",
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

        if tenant_id is not None and not Tenant.objects.filter(pk=tenant_id).exists():
            self.stderr.write(self.style.ERROR(f"Tenant {tenant_id} não encontrado."))
            return

        pending = self._pending_suspensions(now=now, tenant_id=tenant_id)
        canceled = [
            t
            for t in iter_canceled_tenants_pending_block(now=now)
            if tenant_id is None or t.pk == tenant_id
        ]
        if dry_run:
            logouts = [
                t
                for t in iter_tenants_pending_whatsapp_logout()
                if tenant_id is None or t.pk == tenant_id
            ]
            prefix = "[dry-run] "
            self.stdout.write(self.style.WARNING(f"{prefix}{len(pending)} suspensão(ões):"))
            for item in pending:
                self.stdout.write(
                    f"  tenant_id={item.tenant.pk} slug={item.tenant.slug} reason={item.reason}",
                )
            self.stdout.write(
                self.style.WARNING(f"{prefix}{len(canceled)} cancelado(s) a bloquear após o trial:"),
            )
            for t in canceled:
                self.stdout.write(f"  tenant_id={t.pk} slug={t.slug}")
            emails = self._pending_emails(tenant_id)
            self.stdout.write(
                self.style.WARNING(f"{prefix}{len(emails)} e-mail(s) de suspensão pendente(s) (já suspensos):"),
            )
            for t in emails:
                self.stdout.write(self._email_line(t))
            self.stdout.write(self.style.WARNING(f"{prefix}{len(logouts)} logout(s) Evolution pendente(s):"))
            for t in logouts:
                self.stdout.write(self._logout_line(t))
            return

        suspended = sum(
            1
            for item in pending
            if enforce_tenant_suspension(
                item.tenant,
                reason=item.reason,
                send_email=True,
                attempt_logout=False,
            )
        )
        blocked = sum(1 for t in canceled if block_canceled_tenant(t, attempt_logout=False))

        email_failures: list[Tenant] = []
        emailed = 0
        for t in self._pending_emails(tenant_id):
            if send_suspension_email(t):
                emailed += 1
            else:
                email_failures.append(t)

        results: dict[str, list[Tenant]] = {}
        for t in iter_tenants_pending_whatsapp_logout():
            if tenant_id is not None and t.pk != tenant_id:
                continue
            outcome = attempt_pending_whatsapp_logout(t)
            results.setdefault(outcome, []).append(t)

        failed = results.get("failed", [])
        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído: {suspended} suspenso(s), {blocked} cancelado(s) bloqueado(s); "
                f"e-mail de suspensão pendente: {emailed} enviado(s), {len(email_failures)} falha(s); "
                f"logout Evolution: {len(results.get('done', []))} ok, {len(failed)} falha(s), "
                f"{len(results.get('cancelled_regularized', []))} descartado(s) por regularização.",
            ),
        )
        for t in email_failures:
            self.stderr.write(self.style.ERROR("E-mail de suspensão pendente: " + self._email_line(t)))
        for t in failed:
            self.stderr.write(self.style.ERROR("Logout Evolution pendente: " + self._logout_line(t)))

    def _pending_suspensions(self, *, now, tenant_id: int | None) -> list[PendingSuspension]:
        if tenant_id is None:
            return list(iter_tenants_pending_suspension(now=now))
        tenant = Tenant.objects.get(pk=tenant_id)
        reason = suspension_reason_for_tenant(tenant, now=now)
        return [PendingSuspension(tenant=tenant, reason=reason)] if reason else []

    @staticmethod
    def _pending_emails(tenant_id: int | None) -> list[Tenant]:
        return [t for t in iter_tenants_pending_suspension_email() if tenant_id is None or t.pk == tenant_id]

    @staticmethod
    def _email_line(t: Tenant) -> str:
        blocked = t.billing_blocked_at.isoformat() if t.billing_blocked_at else "-"
        notified = t.billing_suspension_notified_at.isoformat() if t.billing_suspension_notified_at else "-"
        return f"tenant_id={t.pk} slug={t.slug} bloqueado_em={blocked} ultimo_aviso={notified}"

    @staticmethod
    def _logout_line(t: Tenant) -> str:
        since = t.whatsapp_logout_pending_since.isoformat() if t.whatsapp_logout_pending_since else "-"
        return (
            f"tenant_id={t.pk} slug={t.slug} status={t.subscription_status} "
            f"pendente_desde={since} tentativas={t.whatsapp_logout_attempts} "
            f"ultimo_erro={t.whatsapp_logout_last_error or '-'}"
        )
