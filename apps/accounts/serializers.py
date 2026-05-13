from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.html import escape
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.services.registration import RegistrationError, register_tenant_with_admin

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


class RegisterSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255)
    tenant_slug = serializers.SlugField(required=False, allow_blank=True, max_length=80)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")
    credit_card = CreditCardSerializer()
    credit_card_holder = CreditCardHolderSerializer()

    def create(self, validated_data: dict) -> User:
        request = self.context["request"]
        forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        remote_ip = forwarded or request.META.get("REMOTE_ADDR") or ""
        card = validated_data["credit_card"]
        holder = dict(validated_data["credit_card_holder"])
        if not (holder.get("cpfCnpj") or "").strip():
            holder.pop("cpfCnpj", None)
        slug = (validated_data.get("tenant_slug") or "").strip() or None
        try:
            _tenant, user = register_tenant_with_admin(
                company_name=validated_data["company_name"],
                slug=slug,
                admin_email=validated_data["admin_email"],
                admin_password=validated_data["admin_password"],
                first_name=validated_data.get("first_name") or "",
                last_name=validated_data.get("last_name") or "",
                credit_card=dict(card),
                credit_card_holder_info=holder,
                remote_ip=remote_ip,
            )
        except RegistrationError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
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


def send_password_reset_email(user: User) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    base = (settings.FRONTEND_PASSWORD_RESET_URL or "").strip().rstrip("/")
    link = f"{base}?uid={uid}&token={token}"
    safe_href = escape(link)
    text_body = (
        "Olá,\n\n"
        "Recebemos um pedido para redefinir a senha da sua conta MarketChat.\n\n"
        f"Acesse o link abaixo para escolher uma nova senha (válido por tempo limitado):\n{link}\n\n"
        "Se você não solicitou isso, ignore este e-mail.\n\n"
        "— MarketChat"
    )
    html_body = f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:24px;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  font-size:16px;line-height:1.5;color:#1f2937;background:#f9fafb;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;margin:0 auto;">
    <tr><td style="background:#fff;border-radius:12px;padding:32px;border:1px solid #e5e7eb;">
      <p style="margin:0 0 16px;">Olá,</p>
      <p style="margin:0 0 16px;">Recebemos um pedido para <strong>redefinir a senha</strong> da sua conta
        MarketChat.</p>
      <p style="margin:0 0 24px;">Clique no botão abaixo para escolher uma nova senha. O link expira após
        algum tempo por segurança.</p>
      <p style="margin:0 0 24px;text-align:center;">
        <a href="{safe_href}" style="display:inline-block;padding:12px 24px;background:#465fff;
          color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">Redefinir senha</a>
      </p>
      <p style="margin:0 0 8px;font-size:14px;color:#6b7280;">Se o botão não funcionar, copie e cole no
        navegador:</p>
      <p style="margin:0 0 24px;font-size:13px;word-break:break-all;color:#4b5563;">{safe_href}</p>
      <p style="margin:0;font-size:14px;color:#6b7280;">Se você não solicitou isso, pode ignorar este e-mail.</p>
    </td></tr>
    <tr><td style="padding:16px 8px;text-align:center;font-size:12px;color:#9ca3af;">MarketChat</td></tr>
  </table>
</body>
</html>"""
    send_mail(
        "Recuperação de senha — MarketChat",
        text_body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
        html_message=html_body,
    )
