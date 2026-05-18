from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.services.tenant_access import user_access_flags, user_can_manage_tenant
from apps.tenants.models import Tenant

User = get_user_model()


def build_account_settings_payload(user: User, tenant: Tenant | None) -> dict:
    tenant_data = None
    if tenant is not None:
        cpf = (tenant.cpf_cnpj or "").strip()
        tenant_data = {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "phone": tenant.phone or "",
            "cpf_cnpj": cpf,
            "cpf_cnpj_editable": not bool(cpf),
        }
    access = user_access_flags(user)
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "phone": user.phone or "",
            "is_tenant_admin": access["is_tenant_admin"],
            "can_manage_integrations": access["can_manage_integrations"],
            "is_platform_superuser": access["is_platform_superuser"],
            "has_tenant": access["has_tenant"],
        },
        "tenant": tenant_data,
    }


class AccountSettingsUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=32)
    tenant_name = serializers.CharField(required=False, max_length=255)
    tenant_phone = serializers.CharField(required=False, allow_blank=True, max_length=32)
    cpf_cnpj = serializers.CharField(required=False, allow_blank=True, max_length=18)

    def validate(self, attrs: dict) -> dict:
        user: User = self.context["user"]
        tenant: Tenant | None = self.context.get("tenant")

        tenant_fields = {"tenant_name", "tenant_phone", "cpf_cnpj"}
        if any(k in attrs for k in tenant_fields) and not user_can_manage_tenant(user):
            raise serializers.ValidationError(
                "Apenas administradores da empresa podem alterar dados da empresa.",
            )

        if "cpf_cnpj" in attrs and tenant is not None:
            new_cpf = (attrs.get("cpf_cnpj") or "").strip()
            existing = (tenant.cpf_cnpj or "").strip()
            if existing and new_cpf and new_cpf != existing:
                raise serializers.ValidationError(
                    {"cpf_cnpj": "CPF/CNPJ não pode ser alterado após o cadastro."},
                )
            if existing and new_cpf == "":
                raise serializers.ValidationError(
                    {"cpf_cnpj": "CPF/CNPJ não pode ser removido após o cadastro."},
                )

        return attrs

    def save(self) -> tuple[User, Tenant | None]:
        user: User = self.context["user"]
        tenant: Tenant | None = self.context.get("tenant")
        validated = self.validated_data

        user_updates: list[str] = []
        for field in ("first_name", "last_name", "phone"):
            if field in validated:
                setattr(user, field, validated[field])
                user_updates.append(field)
        if user_updates:
            user.save(update_fields=user_updates)

        if tenant is not None and user_can_manage_tenant(user):
            tenant_updates: list[str] = []
            if "tenant_name" in validated:
                tenant.name = validated["tenant_name"]
                tenant_updates.append("name")
            if "tenant_phone" in validated:
                tenant.phone = validated["tenant_phone"]
                tenant_updates.append("phone")
            if "cpf_cnpj" in validated:
                cpf = (validated["cpf_cnpj"] or "").strip()
                if cpf and not (tenant.cpf_cnpj or "").strip():
                    tenant.cpf_cnpj = cpf
                    tenant_updates.append("cpf_cnpj")
            if tenant_updates:
                tenant_updates.append("updated_at")
                tenant.save(update_fields=tenant_updates)

        user.refresh_from_db()
        if tenant is not None:
            tenant.refresh_from_db()
        return user, tenant
