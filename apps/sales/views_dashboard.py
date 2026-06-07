from __future__ import annotations

import mimetypes

from django.http import FileResponse, Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sales.models import Cart
from apps.sales.serializers_dashboard import (
    CartDetailSerializer,
    DashboardMetricsSerializer,
    SalesOrderRowSerializer,
)
from apps.sales.services.dashboard_metrics import (
    build_security_photo_url,
    compute_dashboard_metrics,
    orders_list_queryset,
    paginate_orders,
    parse_dashboard_filters,
)


class SalesDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=400,
            )

        filters = parse_dashboard_filters(int(tenant_id), request.query_params)
        metrics = compute_dashboard_metrics(filters)

        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1

        qs = orders_list_queryset(filters)
        carts, total_count, next_page, prev_page = paginate_orders(qs, page=page)

        results = [
            SalesOrderRowSerializer.from_cart(
                cart,
                security_photo_url=build_security_photo_url(cart, request),
            )
            for cart in carts
        ]

        return Response(
            {
                "metrics": DashboardMetricsSerializer.from_metrics(metrics),
                "orders": {
                    "count": total_count,
                    "next": next_page,
                    "previous": prev_page,
                    "results": results,
                },
            },
        )


class SalesCartDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=400,
            )

        cart = (
            Cart.objects.filter(tenant_id=int(tenant_id), pk=pk)
            .select_related("resident", "resident__market")
            .prefetch_related("items__product")
            .first()
        )
        if cart is None:
            return Response({"detail": "Pedido não encontrado."}, status=404)

        payload = CartDetailSerializer.from_cart(
            cart,
            security_photo_url=build_security_photo_url(cart, request),
        )
        return Response(payload)


class SalesCartSecurityPhotoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> FileResponse:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            raise Http404

        cart = Cart.objects.filter(tenant_id=int(tenant_id), pk=pk).first()
        if cart is None or not cart.product_photo:
            raise Http404

        content_type, _ = mimetypes.guess_type(cart.product_photo.name)
        return FileResponse(
            cart.product_photo.open("rb"),
            content_type=content_type or "image/jpeg",
        )
