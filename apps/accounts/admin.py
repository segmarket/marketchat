from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import User


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
