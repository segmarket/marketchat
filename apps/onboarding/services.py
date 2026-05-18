"""Sincronização do progresso de onboarding com o estado real do tenant."""

from __future__ import annotations

from dataclasses import dataclass

from apps.integrations.models import WhatsappInstance
from apps.markets.models import Market
from apps.onboarding.models import TenantOnboarding
from apps.products.models import Product
from apps.sales.models import Cart


@dataclass(frozen=True)
class OnboardingStatusPayload:
    step_market_created: bool
    step_product_created: bool
    step_whatsapp_connected: bool
    step_test_order_completed: bool
    onboarding_finished: bool
    completed_count: int
    completion_percent: int
    show_mission_panel: bool


def _compute_live_steps(tenant_id: int) -> dict[str, bool]:
    return {
        "step_market_created": Market.objects.filter(tenant_id=tenant_id).exists(),
        "step_product_created": Product.objects.filter(tenant_id=tenant_id).exists(),
        "step_whatsapp_connected": WhatsappInstance.objects.filter(
            tenant_id=tenant_id,
            connection_status=WhatsappInstance.ConnectionStatus.OPEN,
        ).exists(),
        "step_test_order_completed": Cart.objects.filter(
            tenant_id=tenant_id,
            status=Cart.Status.COMPLETED,
        ).exclude(product_photo="").exists(),
    }


def _merge_steps(record: TenantOnboarding, live: dict[str, bool]) -> list[str]:
    """Promove flags para True; nunca regride para False (exceto onboarding_finished via dismiss)."""
    update_fields: list[str] = []
    for field, live_value in live.items():
        if live_value and not getattr(record, field):
            setattr(record, field, True)
            update_fields.append(field)
    return update_fields


def _completion_metrics(record: TenantOnboarding) -> tuple[int, int]:
    steps = (
        record.step_market_created,
        record.step_product_created,
        record.step_whatsapp_connected,
        record.step_test_order_completed,
    )
    completed_count = sum(1 for step in steps if step)
    completion_percent = round(completed_count / 4 * 100)
    return completed_count, completion_percent


def get_or_create_onboarding(tenant_id: int) -> TenantOnboarding:
    record, _ = TenantOnboarding.objects.get_or_create(tenant_id=tenant_id)
    return record


def sync_tenant_onboarding(tenant_id: int) -> TenantOnboarding:
    record = get_or_create_onboarding(tenant_id)
    live = _compute_live_steps(tenant_id)
    update_fields = _merge_steps(record, live)
    if update_fields:
        record.save(update_fields=[*update_fields, "updated_at"])
    return record


def build_status_payload(record: TenantOnboarding) -> OnboardingStatusPayload:
    completed_count, completion_percent = _completion_metrics(record)
    return OnboardingStatusPayload(
        step_market_created=record.step_market_created,
        step_product_created=record.step_product_created,
        step_whatsapp_connected=record.step_whatsapp_connected,
        step_test_order_completed=record.step_test_order_completed,
        onboarding_finished=record.onboarding_finished,
        completed_count=completed_count,
        completion_percent=completion_percent,
        show_mission_panel=not record.onboarding_finished,
    )


def dismiss_onboarding(tenant_id: int) -> TenantOnboarding:
    record = sync_tenant_onboarding(tenant_id)
    if not all(
        (
            record.step_market_created,
            record.step_product_created,
            record.step_whatsapp_connected,
            record.step_test_order_completed,
        )
    ):
        raise ValueError("Conclua todas as missões antes de finalizar a jornada.")
    if not record.onboarding_finished:
        record.onboarding_finished = True
        record.save(update_fields=["onboarding_finished", "updated_at"])
    return record
