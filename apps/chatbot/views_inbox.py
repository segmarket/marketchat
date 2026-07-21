"""Views do inbox de atendimento (listagem de sessões)."""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.serializers_inbox import ChatSessionInboxRowSerializer
from apps.chatbot.services.chat_inbox_query import list_inbox_sessions, parse_bot_active_param
from apps.tenants.context import tenant_scope


class ChatSessionInboxListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=400,
            )

        try:
            page = max(1, int(request.query_params.get("page") or 1))
        except (TypeError, ValueError):
            page = 1

        bot_active = parse_bot_active_param(request.query_params.get("bot_active"))
        q = (request.query_params.get("q") or "").strip()

        with tenant_scope(int(tenant_id)):
            rows, total = list_inbox_sessions(
                int(tenant_id),
                bot_active=bot_active,
                q=q,
                page=page,
                page_size=50,
            )

        page_size = 50
        has_next = page * page_size < total
        has_previous = page > 1

        return Response(
            {
                "count": total,
                "next": page + 1 if has_next else None,
                "previous": page - 1 if has_previous else None,
                "results": ChatSessionInboxRowSerializer(rows, many=True).data,
            },
        )
