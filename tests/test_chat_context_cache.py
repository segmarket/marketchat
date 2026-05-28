"""Testes da memória de contexto Redis (gatekeeper)."""

from unittest import mock

import pytest

from apps.chatbot.services.chat_context_cache import (
    append_message,
    clear_context,
    get_recent_messages,
)


@pytest.fixture
def tenant_phone():
    return 99, "5511999887766"


@pytest.fixture(autouse=True)
def _clear_chat_context(tenant_phone):
    tenant_id, phone = tenant_phone
    clear_context(tenant_id, phone)
    yield
    clear_context(tenant_id, phone)


def test_fifo_keeps_last_four_messages(tenant_phone):
    tenant_id, phone = tenant_phone
    for index in range(6):
        append_message(tenant_id, phone, role="user", content=f"msg-{index}")

    history = get_recent_messages(tenant_id, phone)
    assert len(history) == 4
    assert [item["content"] for item in history] == [
        "msg-2",
        "msg-3",
        "msg-4",
        "msg-5",
    ]


def test_graceful_degradation_on_cache_read_failure(tenant_phone):
    tenant_id, phone = tenant_phone
    append_message(tenant_id, phone, role="user", content="oi")

    with mock.patch("apps.chatbot.services.chat_context_cache.cache.get", side_effect=OSError("redis down")):
        assert get_recent_messages(tenant_id, phone) == []


def test_graceful_degradation_on_cache_write_failure(tenant_phone):
    tenant_id, phone = tenant_phone

    with mock.patch("apps.chatbot.services.chat_context_cache.cache.set", side_effect=OSError("redis down")):
        append_message(tenant_id, phone, role="user", content="teste")

    assert get_recent_messages(tenant_id, phone) == []
