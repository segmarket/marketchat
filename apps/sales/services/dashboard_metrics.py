"""Métricas e consultas do painel de vendas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from django.core.paginator import Paginator
from django.db.models import Count, QuerySet, Sum

from apps.sales.models import Cart


@dataclass
class DashboardFilters:
    tenant_id: int
    date_from: date | None = None
    date_to: date | None = None
    market_id: int | None = None
    status: str = ""
    resident_name: str = ""


@dataclass
class DashboardMetrics:
    total_revenue: Decimal
    total_orders: int
    average_ticket: Decimal
    conversion_rate: float
    abandoned_orders: int


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def parse_dashboard_filters(
    tenant_id: int,
    query_params: Any,
) -> DashboardFilters:
    market_id = None
    raw_market = query_params.get("market_id")
    if raw_market not in (None, ""):
        try:
            market_id = int(raw_market)
        except (TypeError, ValueError):
            market_id = None

    return DashboardFilters(
        tenant_id=tenant_id,
        date_from=_parse_date(query_params.get("date_from")),
        date_to=_parse_date(query_params.get("date_to")),
        market_id=market_id,
        status=(query_params.get("status") or "").strip().upper(),
        resident_name=(query_params.get("resident_name") or "").strip(),
    )


def _apply_scope_filters(qs: QuerySet, filters: DashboardFilters) -> QuerySet:
    qs = qs.filter(tenant_id=filters.tenant_id)
    if filters.date_from:
        qs = qs.filter(created_at__date__gte=filters.date_from)
    if filters.date_to:
        qs = qs.filter(created_at__date__lte=filters.date_to)
    if filters.market_id:
        qs = qs.filter(resident__market_id=filters.market_id)
    if filters.resident_name:
        qs = qs.filter(resident__name__icontains=filters.resident_name)
    return qs


def metrics_queryset(filters: DashboardFilters) -> QuerySet:
    """Base para KPIs: data/mercado/nome — sem filtro de status da tabela."""
    return _apply_scope_filters(Cart.objects.all(), filters)


def orders_list_queryset(filters: DashboardFilters) -> QuerySet:
    """Listagem paginada: aplica também filtro de status se informado."""
    qs = metrics_queryset(filters).select_related("resident", "resident__market")
    if filters.status and filters.status in Cart.Status.values:
        qs = qs.filter(status=filters.status)
    return qs.order_by("-created_at")


def compute_dashboard_metrics(filters: DashboardFilters) -> DashboardMetrics:
    base = metrics_queryset(filters)

    completed_qs = base.filter(status=Cart.Status.COMPLETED)
    agg = completed_qs.aggregate(
        revenue=Sum("total_value"),
        orders=Count("id"),
    )
    revenue = agg["revenue"] or Decimal("0")
    orders = int(agg["orders"] or 0)
    average = (revenue / orders) if orders else Decimal("0")

    abandoned = base.filter(
        status__in=(Cart.Status.CANCELLED, Cart.Status.EXPIRED),
    ).count()

    # Denominador: carrinhos do escopo que representam tentativas de venda ativas ou finalizadas.
    funnel_statuses = (
        Cart.Status.COMPLETED,
        Cart.Status.CANCELLED,
        Cart.Status.EXPIRED,
        Cart.Status.AWAITING_PAYMENT,
        Cart.Status.OPEN,
        Cart.Status.AWAITING_PHOTO,
    )
    funnel_total = base.filter(status__in=funnel_statuses).count()
    conversion = (orders / funnel_total) if funnel_total else 0.0

    return DashboardMetrics(
        total_revenue=revenue,
        total_orders=orders,
        average_ticket=average.quantize(Decimal("0.01")),
        conversion_rate=round(conversion, 4),
        abandoned_orders=abandoned,
    )


def paginate_orders(
    qs: QuerySet,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Cart], int, int | None, int | None]:
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)
    next_page = page_obj.next_page_number() if page_obj.has_next() else None
    prev_page = page_obj.previous_page_number() if page_obj.has_previous() else None
    return list(page_obj.object_list), paginator.count, next_page, prev_page


def build_security_photo_url(cart: Cart, request: Any) -> str:
    if not cart.product_photo:
        return ""
    try:
        url = cart.product_photo.url
    except ValueError:
        return ""
    if request:
        return request.build_absolute_uri(url)
    return url
