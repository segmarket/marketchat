import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chatbot.models import ChatMessageLog
from apps.sales.models import Cart
from tests.factories import (
    CartFactory,
    ChatSessionFactory,
    ResidentFactory,
    TenantFactory,
    UserFactory,
)

IMAGE_BYTES = b"\xff\xd8\xfffake-jpeg-cliente"


@pytest.fixture(autouse=True)
def isolated_media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _auth(client, user):
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}",
    )


def _chat_log_with_attachment(tenant, *, with_file=True):
    session = ChatSessionFactory(tenant=tenant)
    log = ChatMessageLog.all_objects.create(
        tenant=tenant,
        session=session,
        direction=ChatMessageLog.Direction.INBOUND,
        message_kind=ChatMessageLog.MessageKind.IMAGE,
        message_text="[Foto dos produtos]",
    )
    if with_file:
        log.attachment.save(
            "foto.jpg",
            SimpleUploadedFile("foto.jpg", IMAGE_BYTES, content_type="image/jpeg"),
            save=True,
        )
    return log


def _cart_with_photo(tenant, *, with_file=True):
    cart = CartFactory(
        tenant=tenant,
        resident=ResidentFactory(tenant=tenant),
        status=Cart.Status.AWAITING_PAYMENT,
    )
    if with_file:
        cart.product_photo.save(
            "foto.jpg",
            SimpleUploadedFile("foto.jpg", IMAGE_BYTES, content_type="image/jpeg"),
            save=True,
        )
    return cart


def _chat_url(obj):
    return reverse("chatbot-message-attachment", kwargs={"pk": obj.pk})


def _cart_url(obj):
    return reverse("sales-cart-security-photo", kwargs={"pk": obj.pk})


MEDIA_CASES = [
    pytest.param(_chat_log_with_attachment, _chat_url, "attachment", id="chat-attachment"),
    pytest.param(_cart_with_photo, _cart_url, "product_photo", id="cart-photo"),
]


@pytest.mark.django_db
@pytest.mark.parametrize("make_obj,url_for,field_name", MEDIA_CASES)
def test_same_tenant_user_receives_file(api_client, make_obj, url_for, field_name):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    obj = make_obj(tenant)

    _auth(api_client, user)
    resp = api_client.get(url_for(obj))

    assert resp.status_code == 200
    assert resp["Content-Type"] == "image/jpeg"
    assert resp["Cache-Control"] == "private, no-store"
    assert resp["X-Content-Type-Options"] == "nosniff"
    assert resp["Content-Disposition"].startswith("inline")
    assert b"".join(resp.streaming_content) == IMAGE_BYTES


@pytest.mark.django_db
@pytest.mark.parametrize("make_obj,url_for,field_name", MEDIA_CASES)
def test_other_tenant_user_gets_404(api_client, make_obj, url_for, field_name):
    owner_tenant = TenantFactory()
    other_user = UserFactory(tenant=TenantFactory())
    obj = make_obj(owner_tenant)

    _auth(api_client, other_user)
    resp = api_client.get(url_for(obj))

    assert resp.status_code == 404
    assert IMAGE_BYTES not in resp.content


@pytest.mark.django_db
@pytest.mark.parametrize("make_obj,url_for,field_name", MEDIA_CASES)
def test_anonymous_user_gets_401(api_client, make_obj, url_for, field_name):
    obj = make_obj(TenantFactory())

    resp = api_client.get(url_for(obj))

    assert resp.status_code == 401
    assert IMAGE_BYTES not in resp.content


@pytest.mark.django_db
@pytest.mark.parametrize("make_obj,url_for,field_name", MEDIA_CASES)
def test_object_without_file_gets_404(api_client, make_obj, url_for, field_name):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    obj = make_obj(tenant, with_file=False)

    _auth(api_client, user)
    resp = api_client.get(url_for(obj))

    assert resp.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("make_obj,url_for,field_name", MEDIA_CASES)
def test_file_missing_from_storage_gets_404(api_client, make_obj, url_for, field_name):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    obj = make_obj(tenant)
    field = getattr(obj, field_name)
    field.storage.delete(field.name)

    _auth(api_client, user)
    resp = api_client.get(url_for(obj))

    assert resp.status_code == 404


@pytest.mark.django_db
def test_nonexistent_object_id_gets_404(api_client):
    user = UserFactory(tenant=TenantFactory())

    _auth(api_client, user)

    assert api_client.get(reverse("chatbot-message-attachment", kwargs={"pk": 999999})).status_code == 404
    assert api_client.get(reverse("sales-cart-security-photo", kwargs={"pk": 999999})).status_code == 404


@pytest.mark.django_db
def test_stored_path_outside_media_root_is_not_served(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    log = _chat_log_with_attachment(tenant, with_file=False)
    ChatMessageLog.all_objects.filter(pk=log.pk).update(attachment="../../etc/passwd")

    _auth(api_client, user)
    resp = api_client.get(_chat_url(log))

    assert resp.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("make_obj,url_for,field_name", MEDIA_CASES)
def test_public_media_route_no_longer_serves_files(api_client, make_obj, url_for, field_name):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    obj = make_obj(tenant)
    stored_name = getattr(obj, field_name).name

    resp_anon = api_client.get(f"/media/{stored_name}")
    _auth(api_client, user)
    resp_auth = api_client.get(f"/media/{stored_name}")

    assert resp_anon.status_code == 404
    assert resp_auth.status_code == 404


@pytest.fixture
def superuser(django_user_model):
    return django_user_model.objects.create_superuser("root-media@example.com", "Testpass123!")


def _admin_photo_url(cart):
    return reverse("admin:sales_cart_security_photo", kwargs={"pk": cart.pk})


@pytest.mark.django_db
def test_cart_admin_change_page_links_authenticated_route(client, superuser):
    cart = _cart_with_photo(TenantFactory())
    client.force_login(superuser)

    resp = client.get(reverse("admin:sales_cart_change", args=[cart.pk]))

    assert resp.status_code == 200
    html = resp.content.decode()
    assert _admin_photo_url(cart) in html
    assert "/media/" not in html
    assert cart.product_photo.name not in html


@pytest.mark.django_db
def test_cart_admin_photo_served_to_superuser(client, superuser):
    cart = _cart_with_photo(TenantFactory())
    client.force_login(superuser)

    resp = client.get(_admin_photo_url(cart))

    assert resp.status_code == 200
    cache_control = {part.strip() for part in resp["Cache-Control"].split(",")}
    assert {"private", "no-store"} <= cache_control
    assert b"".join(resp.streaming_content) == IMAGE_BYTES


@pytest.mark.django_db
def test_cart_admin_photo_requires_admin_login(client):
    cart = _cart_with_photo(TenantFactory())

    resp = client.get(_admin_photo_url(cart))

    assert resp.status_code == 302
    assert reverse("admin:login") in resp["Location"]


@pytest.mark.django_db
def test_cart_admin_photo_denied_to_tenant_user_even_with_jwt(client, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    cart = _cart_with_photo(tenant)

    client.force_login(user)
    resp_session = client.get(_admin_photo_url(cart))
    _auth(api_client, user)
    resp_jwt = api_client.get(_admin_photo_url(cart))

    assert resp_session.status_code == 302
    assert resp_jwt.status_code == 302
    assert IMAGE_BYTES not in resp_session.content + resp_jwt.content


@pytest.mark.django_db
def test_cart_admin_photo_denied_to_staff_without_view_permission(client, django_user_model):
    staff = django_user_model.objects.create_user(
        "staff-noperm@example.com", "Testpass123!", is_staff=True,
    )
    cart = _cart_with_photo(TenantFactory())
    client.force_login(staff)

    resp = client.get(_admin_photo_url(cart))

    assert resp.status_code in (403, 404)
    assert IMAGE_BYTES not in resp.content
