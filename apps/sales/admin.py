from django.contrib import admin
from django.http import Http404
from django.urls import path, reverse
from django.utils.html import format_html

from apps.core.media import protected_file_response
from apps.sales.models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "resident", "status", "total_value", "created_at")
    list_filter = ("status",)
    inlines = [CartItemInline]
    # O widget padrão de ImageField linka MEDIA_URL, que não é servido publicamente.
    exclude = ("product_photo",)
    readonly_fields = ("security_photo",)

    def get_urls(self):
        custom = [
            path(
                "<int:pk>/security-photo/",
                self.admin_site.admin_view(self.security_photo_view),
                name="sales_cart_security_photo",
            ),
        ]
        return custom + super().get_urls()

    def security_photo_view(self, request, pk: int):
        cart = self.get_queryset(request).filter(pk=pk).only("id", "product_photo").first()
        if cart is None or not self.has_view_permission(request, cart):
            raise Http404
        return protected_file_response(cart.product_photo)

    @admin.display(description="Foto de segurança")
    def security_photo(self, obj: Cart) -> str:
        if not obj.pk or not obj.product_photo:
            return "—"
        url = reverse("admin:sales_cart_security_photo", kwargs={"pk": obj.pk})
        return format_html('<a href="{}" target="_blank" rel="noopener">Abrir foto</a>', url)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "quantity", "unit_price")
