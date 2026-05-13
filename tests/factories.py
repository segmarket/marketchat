from datetime import timedelta

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.tenants.models import Tenant

User = get_user_model()


class TenantFactory(DjangoModelFactory):
    class Meta:
        model = Tenant

    name = factory.Sequence(lambda n: f"Empresa {n}")
    slug = factory.Sequence(lambda n: f"empresa-{n}")
    trial_ends_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    tenant = factory.SubFactory(TenantFactory)
    is_tenant_admin = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "Testpass123!")
        email = kwargs.pop("email")
        return model_class.objects.create_user(email, password=password, **kwargs)
