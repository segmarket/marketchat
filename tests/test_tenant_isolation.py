import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenants.models import DemoNote
from tests.factories import TenantFactory, UserFactory


@pytest.mark.django_db
def test_demo_notes_isolated_between_two_tenants(api_client):
    t1 = TenantFactory()
    t2 = TenantFactory()
    u1 = UserFactory(tenant=t1, email="iso1@example.com")
    u2 = UserFactory(tenant=t2, email="iso2@example.com")
    DemoNote.all_objects.create(tenant=t1, title="Note A")
    DemoNote.all_objects.create(tenant=t2, title="Note B")

    url = reverse("demo-note-list")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u1).access_token}")
    r1 = api_client.get(url)
    assert r1.status_code == 200
    assert [n["title"] for n in r1.json()] == ["Note A"]

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u2).access_token}")
    r2 = api_client.get(url)
    assert r2.status_code == 200
    assert [n["title"] for n in r2.json()] == ["Note B"]
