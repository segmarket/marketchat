from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.serializers_analytics import serialize_chatbot_analytics
from apps.chatbot.services.chatbot_analytics import (
    AnalyticsFilters,
    compute_chatbot_analytics,
    parse_market_id,
)


class ChatbotAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=400,
            )

        filters = AnalyticsFilters(
            tenant_id=int(tenant_id),
            market_id=parse_market_id(request.query_params),
        )
        payload = compute_chatbot_analytics(filters)
        return Response(serialize_chatbot_analytics(payload))
