from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.html import format_html

from apps.accounts.models import Lead, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "tenant", "is_tenant_admin", "is_staff", "is_active")
    search_fields = ("email",)
    list_filter = ("is_staff", "is_active", "is_tenant_admin")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Tenant", {"fields": ("tenant", "is_tenant_admin")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas importantes", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "tenant", "is_tenant_admin"),
            },
        ),
    )

    filter_horizontal = ("groups", "user_permissions")


@admin.action(description="Marcar como Em Contato")
def marcar_como_contatado(modeladmin, request, queryset):
    updated = queryset.exclude(status=Lead.Status.CONVERTIDO).update(
        status=Lead.Status.EM_CONTATO,
    )
    modeladmin.message_user(
        request,
        f"{updated} lead(s) marcado(s) como Em Contato.",
        messages.SUCCESS,
    )


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "phone",
        "lead_type",
        "status",
        "created_at",
        "display_whatsapp",
    )
    list_filter = ("lead_type", "status", "created_at")
    search_fields = ("full_name", "email", "phone", "company_name", "company_address", "state")
    readonly_fields = ("created_at", "updated_at", "converted_at", "display_whatsapp")
    list_editable = ("status",)
    actions = [marcar_como_contatado]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.GET.get("status__exact"):
            qs = qs.exclude(status=Lead.Status.CONVERTIDO)
        return qs

    @admin.display(description="WhatsApp")
    def display_whatsapp(self, obj: Lead) -> str:
        digits = (obj.phone or "").strip()
        if not digits:
            return "—"
        return format_html(
            '<a href="https://wa.me/{}" target="_blank" rel="noopener noreferrer">WhatsApp</a>',
            digits,
        )
