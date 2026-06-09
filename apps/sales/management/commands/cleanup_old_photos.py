from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.chatbot.models import ChatMessageLog
from apps.sales.models import Cart


def _clear_image_field(instance, field_name: str) -> bool:
    field = getattr(instance, field_name)
    if not field or not field.name:
        return False
    field.delete(save=False)
    setattr(instance, field_name, "")
    instance.save(update_fields=[field_name, "updated_at"])
    return True


class Command(BaseCommand):
    help = (
        "Remove fotos de moradores (Photo-Lock e anexos de chat) com mais de N dias "
        "para minimização de dados (LGPD)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Idade mínima em dias para exclusão (padrão: 30).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas conta o que seria removido, sem apagar arquivos.",
        )

    def handle(self, *args, **options):
        days = max(1, int(options["days"]))
        dry_run = bool(options["dry_run"])
        cutoff = timezone.now() - timedelta(days=days)

        cart_qs = Cart.objects.filter(
            created_at__lt=cutoff,
        ).exclude(product_photo="")
        log_qs = ChatMessageLog.objects.filter(
            created_at__lt=cutoff,
        ).exclude(attachment="")

        cart_count = cart_qs.count()
        log_count = log_qs.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[dry-run] Removeria {cart_count} foto(s) de carrinho e "
                    f"{log_count} anexo(s) de chat com mais de {days} dia(s)."
                )
            )
            return

        removed_carts = 0
        for cart in cart_qs.iterator():
            if _clear_image_field(cart, "product_photo"):
                removed_carts += 1

        removed_logs = 0
        for log in log_qs.iterator():
            if _clear_image_field(log, "attachment"):
                removed_logs += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Removidas {removed_carts} foto(s) de carrinho e "
                f"{removed_logs} anexo(s) de chat (>{days} dias)."
            )
        )


# Agendamento sugerido (cron diário às 03:00):
# 0 3 * * * cd /caminho/marketchat && python manage.py cleanup_old_photos
