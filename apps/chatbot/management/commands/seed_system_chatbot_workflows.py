from django.core.management.base import BaseCommand

from apps.chatbot.services.system_workflows import seed_system_workflows
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Cria os 5 fluxos padrão do sistema para todos os tenants (idempotente)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas lista tenants que receberiam seed, sem gravar.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Atualiza flow_data de fluxos sistema já existentes.",
        )

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]
        force: bool = options["force"]
        tenants = Tenant.objects.order_by("id")
        total_created = 0

        for tenant in tenants:
            if dry_run:
                self.stdout.write(f"[dry-run] tenant_id={tenant.pk} ({tenant.name})")
                continue
            created = seed_system_workflows(tenant.pk, force=force)
            total_created += created
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"tenant_id={tenant.pk}: {created} fluxo(s) sistema criado(s)."
                    )
                )

        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry-run: {tenants.count()} tenant(s)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Total criados: {total_created}"))
