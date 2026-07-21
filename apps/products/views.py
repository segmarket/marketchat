from django.db.models import Q
from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product
from apps.products.serializers import (
    ImportConfirmSerializer,
    ProductPatchSerializer,
    ProductSearchSerializer,
    ProductSerializer,
)
from apps.products.services.import_apply import ImportApplyError, confirm_import
from apps.products.services.import_compare import build_import_preview
from apps.products.services.import_session import create_import_session, get_valid_session
from apps.products.services.spreadsheet import SpreadsheetError, parse_upload
from apps.products.services.template import build_template_workbook


def _tenant_id(request: Request) -> int:
    return int(request.user.tenant_id)


class ProductListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        products = Product.objects.order_by("sku")

        name = (request.query_params.get("name") or "").strip()
        if name:
            products = products.filter(name__icontains=name)

        sku = (request.query_params.get("sku") or "").strip()
        if sku:
            products = products.filter(sku__icontains=sku)

        status = (request.query_params.get("status") or "").strip()
        if status in (Product.Status.ACTIVE, Product.Status.INACTIVE):
            products = products.filter(status=status)

        return Response(ProductSerializer(products, many=True).data)


class ProductSearchView(APIView):
    """Busca leve para autocomplete (cobrança no chat)."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 2:
            return Response([])

        products = (
            Product.objects.filter(status=Product.Status.ACTIVE)
            .filter(
                Q(name__icontains=q)
                | Q(sku__icontains=q)
                | Q(search_aliases__icontains=q),
            )
            .order_by("name")[:15]
        )
        return Response(ProductSearchSerializer(products, many=True).data)


class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request: Request, pk: int) -> Response:
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"detail": "Produto não encontrado."}, status=404)

        ser = ProductPatchSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        if not data:
            return Response(
                {"detail": "Informe ao menos um campo: name, price, status ou search_aliases."},
                status=400,
            )

        update_fields = []
        if "name" in data:
            product.name = data["name"]
            update_fields.append("name")
        if "search_aliases" in data:
            product.search_aliases = data["search_aliases"].strip()
            update_fields.append("search_aliases")
        if "price" in data:
            product.price = data["price"]
            update_fields.append("price")
        if "status" in data:
            product.status = data["status"]
            update_fields.append("status")

        if update_fields:
            update_fields.append("updated_at")
            product.save(update_fields=update_fields)

        return Response(ProductSerializer(product).data)


class ProductDownloadTemplateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> HttpResponse:
        content = build_template_workbook()
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="produtos-modelo.xlsx"'
        return response


class ProductUploadPreviewView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request) -> Response:
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "Envie o arquivo no campo file."}, status=400)

        try:
            rows = parse_upload(
                upload,
                filename=upload.name or getattr(upload, "name", "") or "upload.csv",
            )
        except SpreadsheetError as exc:
            return Response({"detail": str(exc)}, status=400)

        preview = build_import_preview(_tenant_id(request), rows)
        session = create_import_session(_tenant_id(request), preview)

        return Response(
            {
                "new_count": preview.new_count,
                "updated_count": preview.updated_count,
                "import_token": str(session.token),
            }
        )


class ProductUploadConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        ser = ImportConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        token = ser.validated_data["import_token"]

        try:
            session = get_valid_session(_tenant_id(request), token)
            result = confirm_import(session)
        except ImportApplyError as exc:
            message = str(exc)
            if "já foi confirmada" in message:
                return Response({"detail": message}, status=409)
            return Response({"detail": message}, status=404)

        return Response(
            {
                "created": result.created,
                "updated": result.updated,
                "import_token": str(session.token),
            }
        )
