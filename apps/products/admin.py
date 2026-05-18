from django.contrib import admin

from apps.products.models import Product, ProductImportSession


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "price", "status", "tenant", "updated_at")
    list_filter = ("status", "tenant")
    search_fields = ("sku", "name")


@admin.register(ProductImportSession)
class ProductImportSessionAdmin(admin.ModelAdmin):
    list_display = ("token", "tenant", "new_count", "updated_count", "expires_at", "confirmed_at")
    list_filter = ("tenant",)
