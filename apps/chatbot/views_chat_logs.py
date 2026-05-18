from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.serializers_chat_logs import (
    ChatAttendanceRowSerializer,
    ChatLogMessageSerializer,
)
from apps.chatbot.services.chat_logs_query import (
    build_attendance_rows,
    conversation_messages,
    filter_logs_queryset,
    grouped_attendance_queryset,
    paginate_grouped,
    parse_list_params,
)
from apps.chatbot.services.chat_logs_query import _parse_date as parse_date_param
from apps.tenants.context import tenant_scope


class ChatLogsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=400,
            )

        params = parse_list_params(request.query_params)
        qs = filter_logs_queryset(
            int(tenant_id),
            resident_name=params["resident_name"],
            phone=params["phone"],
            attendance_date=params["attendance_date"],
            date_from=params["date_from"],
            date_to=params["date_to"],
            market_id=params["market_id"],
            intent_type=params["intent_type"],
        )
        groups_qs = grouped_attendance_queryset(qs)
        page_rows, total_count = paginate_grouped(
            groups_qs,
            page=params["page"],
            page_size=20,
        )
        rows = build_attendance_rows(int(tenant_id), page_rows)
        serializer = ChatAttendanceRowSerializer(rows, many=True)

        page = params["page"]
        page_size = 20
        has_next = page * page_size < total_count
        has_previous = page > 1

        return Response(
            {
                "count": total_count,
                "next": page + 1 if has_next else None,
                "previous": page - 1 if has_previous else None,
                "results": serializer.data,
            },
        )


class ChatLogsConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=400,
            )

        session_id_raw = request.query_params.get("session_id")
        if not session_id_raw:
            return Response({"detail": "session_id é obrigatório."}, status=400)
        try:
            session_id = int(session_id_raw)
        except (TypeError, ValueError):
            return Response({"detail": "session_id inválido."}, status=400)

        attendance_date = parse_date_param(request.query_params.get("date"))
        with tenant_scope(int(tenant_id)):
            header, logs = conversation_messages(
                int(tenant_id),
                session_id=session_id,
                attendance_date=attendance_date,
            )
        if not header:
            return Response({"detail": "Atendimento não encontrado."}, status=404)

        return Response(
            {
                **header,
                "messages": ChatLogMessageSerializer(
                    logs,
                    many=True,
                    context={"request": request},
                ).data,
            },
        )
