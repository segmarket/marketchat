from django.contrib import admin

from apps.markets.models import Market


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "tenant", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "address")
