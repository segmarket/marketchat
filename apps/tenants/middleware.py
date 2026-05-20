from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from apps.tenants.context import clear_current_tenant_id, set_current_tenant_id
from apps.tenants.models import Tenant
from apps.tenants.services.panel_access import get_panel_access_denial


class TenantJWTContextMiddleware(MiddlewareMixin):
    """Define contexto de tenant a partir do JWT (antes da view DRF)."""

    def process_request(self, request):
        clear_current_tenant_id()
        auth = JWTAuthentication()
        try:
            result = auth.authenticate(request)
        except (InvalidToken, TokenError, AuthenticationFailed):
            result = None
        if result:
            user, _token = result
            request.user = user
            tid = getattr(user, "tenant_id", None)
            if tid:
                set_current_tenant_id(tid)

    def process_response(self, request, response):
        clear_current_tenant_id()
        return response


BILLING_BYPASS_PREFIXES = (
    "/admin",
    "/api/auth/register",
    "/api/auth/token",
    "/api/auth/me",
    "/api/auth/password/reset",
    "/api/settings/account",
    "/api/settings/billing",
    "/api/billing/webhooks/asaas",
    "/api/webhooks/asaas",
    "/api/integrations/webhooks",
)


class TenantBillingBlockMiddleware(MiddlewareMixin):
    """Bloqueia API quando o tenant está com billing suspenso."""

    def process_request(self, request):
        path = request.path
        for prefix in BILLING_BYPASS_PREFIXES:
            if path == prefix or path.startswith(prefix + "/"):
                return None
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        tid = getattr(user, "tenant_id", None)
        if tid is None:
            return None
        try:
            tenant = Tenant.objects.get(pk=tid)
        except Tenant.DoesNotExist:
            return JsonResponse({"detail": "Tenant inválido."}, status=403)
        denial = get_panel_access_denial(tenant)
        if denial is not None:
            error_code, message = denial
            return JsonResponse(
                {"error": error_code, "message": message, "detail": message},
                status=402,
            )
        return None
