"""Fecha conexões Django quando o Postgres reporta esgotamento de slots."""

from __future__ import annotations

import logging

from django.db import OperationalError, connections
from django.db.utils import OperationalError as DjangoOperationalError
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


def _is_connection_slot_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return (
        "too many clients" in text
        or "remaining connection slots are reserved" in text
        or "connection slots" in text
    )


class CloseDbConnectionsOnErrorMiddleware(MiddlewareMixin):
    """Evita workers com conexão quebrada após FATAL too many clients."""

    def process_exception(self, request, exception):
        if isinstance(exception, (OperationalError, DjangoOperationalError)) and _is_connection_slot_error(
            exception
        ):
            logger.error(
                "Postgres sem slots de conexão em %s: %s",
                getattr(request, "path", "?"),
                exception,
            )
            connections.close_all()
        return None
