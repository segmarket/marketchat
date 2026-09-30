"""Regra única da carência de inadimplência (painel, bot, check_subscriptions e UI)."""

from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone


def billing_grace_period() -> timedelta:
    return timedelta(days=int(getattr(settings, "BILLING_GRACE_DAYS", 3)))


def grace_deadline(overdue_since: datetime | None) -> datetime | None:
    """Instante exato em que a carência termina (overdue_since + BILLING_GRACE_DAYS)."""
    if overdue_since is None:
        return None
    return overdue_since + billing_grace_period()


def is_within_grace(overdue_since: datetime | None, *, now: datetime | None = None) -> bool:
    deadline = grace_deadline(overdue_since)
    if deadline is None:
        return False
    return (now or timezone.now()) < deadline


def grace_expired(overdue_since: datetime | None, *, now: datetime | None = None) -> bool:
    deadline = grace_deadline(overdue_since)
    if deadline is None:
        return False
    return (now or timezone.now()) >= deadline


def grace_expired_cutoff(*, now: datetime | None = None) -> datetime:
    """Para filtros ORM: overdue_since <= cutoff equivale a grace_expired()."""
    return (now or timezone.now()) - billing_grace_period()
