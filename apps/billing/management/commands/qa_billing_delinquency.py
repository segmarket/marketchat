from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.billing.services import qa_delinquency as qa
from apps.billing.services.asaas_client import AsaasAPIError

READ_ONLY_ACTIONS = ("diagnose", "validate", "replay-webhook")
MUTATING_ACTIONS = (
    "generate-charges",
    "force-overdue",
    "confirm-payment",
    "advance-grace",
    "run-check",
    "restore",
)


class Command(BaseCommand):
    help = (
        "SOMENTE QA (staging + Asaas sandbox): simula o ciclo de inadimplência de um tenant "
        "fictício. Recusa produção e URL/chave Asaas fora do sandbox. Ações que alteram "
        "estado exigem --confirm-slug e aceitam --dry-run."
    )

    def add_arguments(self, parser):
        parser.add_argument("action", choices=READ_ONLY_ACTIONS + MUTATING_ACTIONS)
        parser.add_argument("--tenant-id", type=int, required=True, help="Tenant fictício alvo.")
        parser.add_argument(
            "--confirm-slug",
            default="",
            help="Slug do tenant, obrigatório nas ações que alteram estado.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Mostra o plano sem alterar nada.")
        parser.add_argument("--payment-id", default="", help="Cobrança pay_… da assinatura do tenant.")
        parser.add_argument(
            "--wait",
            type=int,
            default=0,
            help="Segundos aguardando o webhook real do Asaas (force-overdue/confirm-payment).",
        )
        parser.add_argument("--until", default="", help="AAAA-MM (generate-charges).")
        parser.add_argument(
            "--ends-in-minutes",
            type=int,
            default=0,
            help="advance-grace: novo fim da carência = agora + N minutos (0 = encerra já).",
        )
        parser.add_argument(
            "--simulate-logout-failure",
            action="store_true",
            help="run-check: força falha no logout Evolution para registrar a pendência.",
        )
        parser.add_argument("--expect", choices=("grace", "blocked", "active"), help="validate.")
        parser.add_argument("--control-tenant-id", type=int, default=None, help="validate: tenant que deve seguir ativo.")
        parser.add_argument("--mode", choices=("duplicate", "stale"), help="replay-webhook.")
        parser.add_argument("--snapshot-id", type=int, default=None, help="restore: snapshot específico.")

    def handle(self, *args, **options):
        action = options["action"]
        try:
            qa.assert_qa_environment()
            tenant = qa.load_tenant(options["tenant_id"])
            if action in MUTATING_ACTIONS and options["confirm_slug"] != tenant.slug:
                raise qa.QaActionError(
                    f"'{action}' altera estado: informe --confirm-slug {tenant.slug} para confirmar o tenant.",
                )
            report = qa.Report(write=self.stdout.write)
            self._dispatch(action, tenant, report, options)
        except (qa.QaEnvironmentError, qa.QaActionError) as exc:
            raise CommandError(str(exc)) from exc
        except AsaasAPIError as exc:
            raise CommandError(f"Asaas sandbox: {qa.asaas_error_text(exc)}") from exc

        if report.failed:
            raise CommandError(f"{len(report.failed)} verificação(ões) falharam.")

    def _dispatch(self, action: str, tenant, report: qa.Report, options) -> None:
        dry_run = bool(options["dry_run"])
        if action == "diagnose":
            qa.diagnose(report, tenant)
        elif action == "generate-charges":
            qa.generate_charges(report, tenant, until=options["until"], dry_run=dry_run)
        elif action == "force-overdue":
            qa.force_overdue(
                report,
                tenant,
                payment_id=options["payment_id"],
                dry_run=dry_run,
                wait=options["wait"],
            )
        elif action == "confirm-payment":
            qa.confirm_payment(
                report,
                tenant,
                payment_id=options["payment_id"],
                dry_run=dry_run,
                wait=options["wait"],
            )
        elif action == "advance-grace":
            qa.advance_grace(report, tenant, ends_in_minutes=options["ends_in_minutes"], dry_run=dry_run)
        elif action == "run-check":
            qa.run_check(
                report,
                tenant,
                dry_run=dry_run,
                simulate_logout_failure=bool(options["simulate_logout_failure"]),
                stdout=self.stdout,
                stderr=self.stderr,
            )
        elif action == "restore":
            qa.restore(report, tenant, snapshot_id=options["snapshot_id"], dry_run=dry_run)
        elif action == "validate":
            if not options["expect"]:
                raise qa.QaActionError("validate exige --expect grace|blocked|active.")
            control = None
            if options["control_tenant_id"] is not None:
                if options["control_tenant_id"] == tenant.pk:
                    raise qa.QaActionError("--control-tenant-id precisa ser outro tenant.")
                control = qa.load_tenant(options["control_tenant_id"])
            qa.validate(report, tenant, expect=options["expect"], control_tenant=control)
        elif action == "replay-webhook":
            if not options["mode"]:
                raise qa.QaActionError("replay-webhook exige --mode duplicate|stale.")
            qa.replay_webhook(report, tenant, mode=options["mode"], payment_id=options["payment_id"])
