import pytest
from django.core.cache.backends.locmem import LocMemCache
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

_throttle_cache = LocMemCache("marketchat-test-throttle", {})


@pytest.fixture(autouse=True)
def isolated_throttle_cache(monkeypatch):
    """Contadores de rate limit ficam num cache próprio, zerado a cada teste.

    Sem isso as cotas (anon 10/min, user 60/min) acumulam no cache default entre
    testes e geram 429 aleatórios; o cache default não é tocado.
    """
    monkeypatch.setattr(SimpleRateThrottle, "cache", _throttle_cache)
    _throttle_cache.clear()
    yield
    _throttle_cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()
