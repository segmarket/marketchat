from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.support.serializers import (
    SupportChatSerializer,
    SupportTicketCreateSerializer,
    SupportTicketDetailSerializer,
    SupportTicketListSerializer,
    SupportTicketMessageSerializer,
    SupportTicketReplySerializer,
    SupportTicketUpdateSerializer,
)
from apps.support.services.copilot import (
    SupportCopilotError,
    SupportCopilotServiceError,
    complete_support_chat,
)
from apps.support.services.tickets import (
    SupportTicketCreateError,
    SupportTicketReplyError,
    SupportTicketUpdateError,
    create_support_ticket,
    update_ticket_status,
    get_ticket_for_tenant,
    reply_to_ticket,
    tenant_tickets_queryset,
    ticket_to_response_payload,
)


def _tenant_id_from_request(request: Request) -> int | None:
    tenant_id = getattr(request.user, "tenant_id", None)
    if tenant_id is None:
        return None
    return int(tenant_id)


def _require_tenant(request: Request) -> int | Response:
    tenant_id = _tenant_id_from_request(request)
    if tenant_id is None:
        return Response(
            {"detail": "Conta sem empresa vinculada."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return tenant_id


class SupportChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = SupportChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            reply = complete_support_chat(
                message=data["message"],
                current_route=data["current_route"],
                chat_history=data.get("chat_history") or [],
            )
        except SupportCopilotServiceError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except SupportCopilotError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"reply": reply})


class SupportTicketCollectionView(APIView):
    """GET lista (tenant) | POST cria chamado."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant_id = _require_tenant(request)
        if isinstance(tenant_id, Response):
            return tenant_id

        tickets = tenant_tickets_queryset(tenant_id)
        return Response(SupportTicketListSerializer(tickets, many=True).data)

    def post(self, request: Request) -> Response:
        tenant_id = _require_tenant(request)
        if isinstance(tenant_id, Response):
            return tenant_id

        serializer = SupportTicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            ticket = create_support_ticket(
                user=request.user,
                subject=data["subject"],
                description=data["description"],
                category_route=data["category_route"],
            )
        except SupportTicketCreateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ticket_to_response_payload(ticket),
            status=status.HTTP_201_CREATED,
        )


class SupportTicketDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        tenant_id = _require_tenant(request)
        if isinstance(tenant_id, Response):
            return tenant_id

        ticket = get_ticket_for_tenant(tenant_id=tenant_id, ticket_id=pk)
        if not ticket:
            return Response({"detail": "Chamado não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        return Response(SupportTicketDetailSerializer(ticket).data)

    def patch(self, request: Request, pk: int) -> Response:
        tenant_id = _require_tenant(request)
        if isinstance(tenant_id, Response):
            return tenant_id

        ticket = get_ticket_for_tenant(tenant_id=tenant_id, ticket_id=pk)
        if not ticket:
            return Response({"detail": "Chamado não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupportTicketUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            ticket = update_ticket_status(
                ticket=ticket,
                status=serializer.validated_data["status"],
            )
        except SupportTicketUpdateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SupportTicketDetailSerializer(ticket).data)


class SupportTicketReplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        tenant_id = _require_tenant(request)
        if isinstance(tenant_id, Response):
            return tenant_id

        ticket = get_ticket_for_tenant(tenant_id=tenant_id, ticket_id=pk)
        if not ticket:
            return Response({"detail": "Chamado não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupportTicketReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            msg = reply_to_ticket(
                ticket=ticket,
                user=request.user,
                message=serializer.validated_data["message"],
            )
        except SupportTicketReplyError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "ticket_id": ticket.pk,
                "status": ticket.status,
                "message": SupportTicketMessageSerializer(msg).data,
            },
            status=status.HTTP_201_CREATED,
        )
