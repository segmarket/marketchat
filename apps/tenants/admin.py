from django.contrib import admin

from apps.tenants.models import DemoNote, Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "trial_ends_at", "billing_blocked_at", "created_at")
    search_fields = ("name", "slug")


@admin.register(DemoNote)
class DemoNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "tenant", "created_at")
