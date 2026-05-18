from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.sales.models import Cart
from apps.sales.services.asaas_payment_webhook import sync_cart_payment_from_asaas


class Command(BaseCommand):
    help = (
        "Consulta o status das cobranças Pix no Asaas para carrinhos em "
        "AWAITING_PAYMENT (útil em dev quando o webhook não alcança o localhost)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--cart-id",
            type=int,
            default=None,
            help="Sincronizar apenas um carrinho específico.",
        )

    def handle(self, *args, **options):
        cart_id = options.get("cart_id")
        qs = Cart.objects.filter(status=Cart.Status.AWAITING_PAYMENT).exclude(
            asaas_billing_id="",
        )
        if cart_id:
            qs = qs.filter(pk=cart_id)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("Nenhum carrinho aguardando pagamento."))
            return

        synced = 0
        for cart in qs.select_related("resident", "tenant").iterator():
            if sync_cart_payment_from_asaas(cart):
                synced += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Carrinho #{cart.id} confirmado (payment={cart.asaas_billing_id}).",
                    ),
                )
            else:
                self.stdout.write(
                    f"Carrinho #{cart.id}: ainda pendente no Asaas ({cart.asaas_billing_id}).",
                )

        self.stdout.write(
            self.style.SUCCESS(f"{synced}/{total} carrinho(s) confirmado(s) via API Asaas."),
        )
