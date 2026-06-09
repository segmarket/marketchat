from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.services.registration import RegistrationError, register_tenant_with_admin
from apps.core.emails import send_welcome_trial_email_safe

User = get_user_model()


class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        if user.tenant_id:
            token["tenant_id"] = user.tenant_id
        return token


class CreditCardSerializer(serializers.Serializer):
    holderName = serializers.CharField()
    number = serializers.CharField()
    expiryMonth = serializers.CharField(max_length=2)
    expiryYear = serializers.CharField(max_length=4)
    ccv = serializers.CharField(max_length=4)


class CreditCardHolderSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    cpfCnpj = serializers.CharField(required=False, allow_blank=True, default="")
    postalCode = serializers.CharField()
    address = serializers.CharField()
    addressNumber = serializers.CharField()
    complement = serializers.CharField(required=False, allow_blank=True, default="")
    province = serializers.CharField()
    phone = serializers.CharField()


class AttributionSerializer(serializers.Serializer):
    utm_source = serializers.CharField(required=False, allow_blank=True, default="")
    utm_medium = serializers.CharField(required=False, allow_blank=True, default="")
    utm_campaign = serializers.CharField(required=False, allow_blank=True, default="")
    utm_term = serializers.CharField(required=False, allow_blank=True, default="")
    utm_content = serializers.CharField(required=False, allow_blank=True, default="")
    gclid = serializers.CharField(required=False, allow_blank=True, default="")
    fbclid = serializers.CharField(required=False, allow_blank=True, default="")


class RegisterSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255)
    tenant_slug = serializers.SlugField(required=False, allow_blank=True, max_length=80)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")
    accept_terms = serializers.BooleanField(required=True)
    credit_card = CreditCardSerializer()
    credit_card_holder = CreditCardHolderSerializer()
    attribution = AttributionSerializer(required=False)

    def validate_accept_terms(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "É necessário aceitar a Política de Privacidade e os Termos de Uso."
            )
        return value

    def create(self, validated_data: dict) -> User:
        request = self.context["request"]
        forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        remote_ip = forwarded or request.META.get("REMOTE_ADDR") or ""
        card = validated_data["credit_card"]
        holder = dict(validated_data["credit_card_holder"])
        if not (holder.get("cpfCnpj") or "").strip():
            holder.pop("cpfCnpj", None)
        slug = (validated_data.get("tenant_slug") or "").strip() or None
        attribution = validated_data.pop("attribution", None) or {}
        validated_data.pop("accept_terms", None)
        try:
            tenant, user = register_tenant_with_admin(
                company_name=validated_data["company_name"],
                slug=slug,
                admin_email=validated_data["admin_email"],
                admin_password=validated_data["admin_password"],
                first_name=validated_data.get("first_name") or "",
                last_name=validated_data.get("last_name") or "",
                credit_card=dict(card),
                credit_card_holder_info=holder,
                remote_ip=remote_ip,
                attribution=attribution,
            )
        except RegistrationError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        send_welcome_trial_email_safe(user, tenant)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value: str) -> str:
        validate_password(value, self.context["request"].user)
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs: dict) -> dict:
        try:
            uid = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=int(uid))
        except (User.DoesNotExist, ValueError, TypeError) as exc:
            raise serializers.ValidationError({"detail": "Link inválido."}) from exc
        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"detail": "Token inválido ou expirado."})
        validate_password(attrs["new_password"], user)
        attrs["user"] = user
        return attrs

    def save(self, **kwargs) -> User:
        user: User = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
