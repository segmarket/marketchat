from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.models import ChatbotWorkflow
from apps.chatbot.serializers import (
    ChatbotWorkflowDetailSerializer,
    ChatbotWorkflowListSerializer,
    ChatbotWorkflowPatchSerializer,
    ChatbotWorkflowSaveSerializer,
)
from apps.tenants.context import get_current_tenant_id

SYSTEM_DELETE_FORBIDDEN = "Fluxos padrão do sistema não podem ser excluídos."
SYSTEM_RENAME_FORBIDDEN = "Fluxos padrão do sistema não podem ser renomeados."


def _resolve_tenant_id(request: Request) -> int | None:
    tid = get_current_tenant_id()
    if tid is not None:
        return int(tid)
    user_tid = getattr(request.user, "tenant_id", None)
    return int(user_tid) if user_tid is not None else None


def _get_workflow_or_404(pk: int) -> ChatbotWorkflow | None:
    try:
        return ChatbotWorkflow.objects.get(pk=pk)
    except ChatbotWorkflow.DoesNotExist:
        return None


class ChatbotWorkflowListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        workflows = ChatbotWorkflow.objects.order_by("-is_system", "-is_active", "name")
        return Response(ChatbotWorkflowListSerializer(workflows, many=True).data)


class ChatbotWorkflowActiveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        workflow = (
            ChatbotWorkflow.objects.filter(is_active=True)
            .order_by("-is_system", "-updated_at")
            .first()
        )
        if workflow is None:
            return Response({"detail": "Nenhum fluxo ativo encontrado."}, status=404)
        return Response(ChatbotWorkflowDetailSerializer(workflow).data)


class ChatbotWorkflowDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        workflow = _get_workflow_or_404(pk)
        if workflow is None:
            return Response({"detail": "Fluxo não encontrado."}, status=404)
        return Response(ChatbotWorkflowDetailSerializer(workflow).data)

    def patch(self, request: Request, pk: int) -> Response:
        workflow = _get_workflow_or_404(pk)
        if workflow is None:
            return Response({"detail": "Fluxo não encontrado."}, status=404)

        ser = ChatbotWorkflowPatchSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        if workflow.is_system and "name" in data:
            return Response({"detail": SYSTEM_RENAME_FORBIDDEN}, status=status.HTTP_403_FORBIDDEN)

        if "name" in data:
            workflow.name = data["name"]
        if "is_active" in data:
            workflow.is_active = data["is_active"]

        workflow.save()
        return Response(ChatbotWorkflowDetailSerializer(workflow).data)

    def delete(self, request: Request, pk: int) -> Response:
        workflow = _get_workflow_or_404(pk)
        if workflow is None:
            return Response({"detail": "Fluxo não encontrado."}, status=404)
        if workflow.is_system:
            return Response({"detail": SYSTEM_DELETE_FORBIDDEN}, status=status.HTTP_403_FORBIDDEN)
        workflow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatbotWorkflowDuplicateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, pk: int) -> Response:
        workflow = _get_workflow_or_404(pk)
        if workflow is None:
            return Response({"detail": "Fluxo não encontrado."}, status=404)

        tenant_id = _resolve_tenant_id(request)
        if tenant_id is None:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        copy_name = f"Cópia de {workflow.name}"[:255]
        duplicate = ChatbotWorkflow.objects.create(
            tenant_id=tenant_id,
            name=copy_name,
            flow_data=workflow.flow_data,
            is_active=False,
            is_system=False,
            system_key="",
        )
        return Response(
            ChatbotWorkflowDetailSerializer(duplicate).data,
            status=status.HTTP_201_CREATED,
        )


class ChatbotWorkflowSaveView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request) -> Response:
        ser = ChatbotWorkflowSaveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        tenant_id = _resolve_tenant_id(request)
        if tenant_id is None:
            return Response(
                {"detail": "Conta sem empresa vinculada. Não é possível salvar o fluxo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow_id = data.get("id")

        if workflow_id:
            workflow = _get_workflow_or_404(workflow_id)
            if workflow is None:
                return Response({"detail": "Fluxo não encontrado."}, status=404)

            if workflow.is_system:
                new_name = (data.get("name") or "").strip()
                if new_name and new_name != workflow.name:
                    return Response(
                        {"detail": SYSTEM_RENAME_FORBIDDEN},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                workflow.name = workflow.name
            else:
                workflow.name = data.get("name") or workflow.name or "Fluxo principal"

            workflow.flow_data = data["flow_data"]
            if "is_active" in data:
                workflow.is_active = data["is_active"]
            workflow.save()
            return Response(
                ChatbotWorkflowDetailSerializer(workflow).data,
                status=status.HTTP_200_OK,
            )

        workflow = ChatbotWorkflow.objects.create(
            tenant_id=tenant_id,
            name=data.get("name") or "Fluxo principal",
            flow_data=data["flow_data"],
            is_active=data.get("is_active", True),
            is_system=False,
            system_key="",
        )
        return Response(
            ChatbotWorkflowDetailSerializer(workflow).data,
            status=status.HTTP_201_CREATED,
        )
