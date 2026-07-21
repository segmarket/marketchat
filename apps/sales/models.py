from decimal import Decimal

from django.db import models

from apps.tenants.models import Tenant


class Cart(models.Model):
    """Carrinho de compra do morador via WhatsApp."""

    class Status(models.TextChoices):
        OPEN = "OPEN", "Aberto"
        AWAITING_PHOTO = "AWAITING_PHOTO", "Aguardando foto"
        AWAITING_PAYMENT = "AWAITING_PAYMENT", "Aguardando pagamento"
        COMPLETED = "COMPLETED", "Concluído"
        EXPIRED = "EXPIRED", "Pix expirado"
        CANCELLED = "CANCELLED", "Cancelado"

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="carts",
    )
    resident = models.ForeignKey(
        "residents.Resident",
        on_delete=models.CASCADE,
        related_name="carts",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.OPEN,
    )
    total_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
    )
    product_photo = models.ImageField(
        upload_to="security_photos/%Y/%m/%d/",
        blank=True,
        default="",
    )
    asaas_billing_id = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "resident", "status"]),
            models.Index(fields=["asaas_billing_id"]),
        ]

    def __str__(self) -> str:
        return f"Cart({self.resident_id}, {self.status})"

    def recalculate_total(self) -> Decimal:
        total = Decimal("0")
        for item in self.items.all():
            if item.quantity > 0:
                total += item.unit_price * item.quantity
        self.total_value = total
        self.save(update_fields=["total_value", "updated_at"])
        return total


class CartItem(models.Model):
    """Item do carrinho (produto do catálogo ou linha avulsa do chat)."""

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="cart_items",
        null=True,
        blank=True,
    )
    item_name = models.CharField(max_length=255, blank=True, default="")
    quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"],
                condition=models.Q(product__isnull=False),
                name="uniq_cart_item_cart_product",
            ),
        ]

    def __str__(self) -> str:
        label = self.display_name
        return f"{label} x{self.quantity}"

    @property
    def display_name(self) -> str:
        if (self.item_name or "").strip():
            return self.item_name.strip()
        if self.product_id and self.product:
            return self.product.name or self.product.sku
        return "Item"

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity
