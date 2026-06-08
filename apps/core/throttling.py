"""Rate limiting DRF com suporte a proxy reverso (X-Forwarded-For)."""

from __future__ import annotations

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


def get_client_ip(request) -> str:
    """IP do cliente; usa o primeiro hop de X-Forwarded-For quando atrás de proxy."""
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class ForwardedAwareAnonRateThrottle(AnonRateThrottle):
    scope = "anon"

    def get_ident(self, request):
        return get_client_ip(request)


class ForwardedAwareUserRateThrottle(UserRateThrottle):
    scope = "user"

    def get_ident(self, request):
        if request.user and request.user.is_authenticated:
            return str(request.user.pk)
        return get_client_ip(request)


class LoginRateThrottle(ForwardedAwareAnonRateThrottle):
    """Anti brute-force no endpoint de login JWT (5/min por IP)."""

    scope = "login"


class WithdrawRateThrottle(ForwardedAwareUserRateThrottle):
    """Limita solicitações de saque por usuário (5/hour)."""

    scope = "withdraw"
