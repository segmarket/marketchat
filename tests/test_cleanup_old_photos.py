from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone

from apps.chatbot.models import ChatMessageLog
from apps.sales.models import Cart
from tests.factories import CartFactory, ResidentFactory, TenantFactory


@pytest.mark.django_db
def test_cleanup_old_photos_dry_run():
    tenant = TenantFactory()
    resident = ResidentFactory(tenant=tenant)
    cart = CartFactory(tenant=tenant, resident=resident)
    cart.product_photo.save(
        "cart_old.jpg",
        SimpleUploadedFile("cart_old.jpg", b"fake-image", content_type="image/jpeg"),
        save=True,
    )
    Cart.objects.filter(pk=cart.pk).update(
        created_at=timezone.now() - timedelta(days=40),
    )

    call_command("cleanup_old_photos", "--dry-run")
    cart.refresh_from_db()
    assert cart.product_photo.name


@pytest.mark.django_db
def test_cleanup_old_photos_deletes_file():
    tenant = TenantFactory()
    resident = ResidentFactory(tenant=tenant)
    cart = CartFactory(tenant=tenant, resident=resident)
    cart.product_photo.save(
        "cart_old2.jpg",
        SimpleUploadedFile("cart_old2.jpg", b"fake-image", content_type="image/jpeg"),
        save=True,
    )
    Cart.objects.filter(pk=cart.pk).update(
        created_at=timezone.now() - timedelta(days=40),
    )

    call_command("cleanup_old_photos", "--days=30")
    cart.refresh_from_db()
    assert not cart.product_photo.name
