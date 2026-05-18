from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.sales.models import Cart
from apps.sales.services.cart_session import unlock_resident_chat_session


class Command(BaseCommand):
    help = (
        "Cancela carrinhos abandonados (OPEN, AWAITING_PHOTO, AWAITING_PAYMENT) "
        "com mais de 15 minutos e libera a sessão WhatsApp do morador."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=15,
            help="Idade mínima do carrinho em minutos (padrão: 15).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas lista o que seria cancelado, sem gravar.",
        )

    def handle(self, *args, **options):
        minutes = max(1, int(options["minutes"]))
        dry_run = bool(options["dry_run"])
        cutoff = timezone.now() - timedelta(minutes=minutes)

        stale_statuses = (
            Cart.Status.OPEN,
            Cart.Status.AWAITING_PHOTO,
            Cart.Status.AWAITING_PAYMENT,
        )
        qs = (
            Cart.objects.filter(status__in=stale_statuses, created_at__lt=cutoff)
            .select_related("resident")
            .order_by("created_at")
        )

        count = qs.count()
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[dry-run] {count} carrinho(s) seriam cancelados (criados antes de {cutoff}).",
                ),
            )
            for cart in qs[:50]:
                self.stdout.write(
                    f"  cart={cart.id} status={cart.status} resident={cart.resident.phone_number}",
                )
            return

        updated = 0
        for cart in qs.iterator():
            cart.status = Cart.Status.CANCELLED
            cart.save(update_fields=["status", "updated_at"])
            resident = cart.resident
            unlock_resident_chat_session(resident=resident, clear_cart_link=True)
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{updated} carrinho(s) cancelado(s) e sessões liberadas (limite {minutes} min).",
            ),
        )
