import uuid
from datetime import timedelta
from decimal import Decimal

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.billing.models import Subscription
from apps.integrations.models import WhatsappInstance
from apps.markets.models import Market
from apps.products.models import Product
from apps.chatbot.models import ChatbotWorkflow
from apps.billing.models import AsaasSubaccount
from apps.residents.models import ChatSession, Resident
from apps.sales.models import Cart, CartItem
from apps.tenants.models import Tenant

User = get_user_model()


class TenantFactory(DjangoModelFactory):
    class Meta:
        model = Tenant

    name = factory.Sequence(lambda n: f"Empresa {n}")
    slug = factory.Sequence(lambda n: f"empresa-{n}")
    trial_started_at = factory.LazyFunction(timezone.now)
    trial_ends_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    subscription_status = Tenant.SubscriptionStatus.TRIAL


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


class WhatsappInstanceFactory(DjangoModelFactory):
    class Meta:
        model = WhatsappInstance

    tenant = factory.SubFactory(TenantFactory)
    instance_name = factory.Sequence(lambda n: f"mc-test-{n}")
    instance_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    api_key = factory.Sequence(lambda n: f"token-test-{n}")
    webhook_url = "http://localhost/api/integrations/webhooks/evolution/?secret=test"
    webhook_secret = "test-webhook-secret"
    connection_status = WhatsappInstance.ConnectionStatus.CONNECTING
    is_active = True


class MarketFactory(DjangoModelFactory):
    class Meta:
        model = Market

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Condomínio {n}")
    address = factory.Sequence(lambda n: f"Rua Exemplo, {n} — São Paulo, SP")
    status = Market.Status.ACTIVE


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    tenant = factory.SubFactory(TenantFactory)
    sku = factory.Sequence(lambda n: f"SKU-{n:04d}")
    name = factory.Sequence(lambda n: f"Produto {n}")
    price = factory.LazyFunction(lambda: Decimal("10.00"))
    status = Product.Status.ACTIVE


class ResidentFactory(DjangoModelFactory):
    class Meta:
        model = Resident

    tenant = factory.SubFactory(TenantFactory)
    market = factory.SubFactory(MarketFactory, tenant=factory.SelfAttribute("..tenant"))
    phone_number = factory.Sequence(lambda n: f"55119999{n:04d}")
    name = factory.Sequence(lambda n: f"Morador {n}")


class ChatSessionFactory(DjangoModelFactory):
    class Meta:
        model = ChatSession

    tenant = factory.SubFactory(TenantFactory)
    phone_number = factory.Sequence(lambda n: f"55118888{n:04d}")
    state = ChatSession.State.AWAITING_NAME
    temporary_name = ""


class ChatbotWorkflowFactory(DjangoModelFactory):
    class Meta:
        model = ChatbotWorkflow

    tenant = factory.SubFactory(TenantFactory)
    name = "Fluxo principal"
    is_active = True
    flow_data = factory.LazyFunction(dict)


class AsaasSubaccountFactory(DjangoModelFactory):
    class Meta:
        model = AsaasSubaccount

    tenant = factory.SubFactory(TenantFactory)
    name = "Mercado Teste"
    email = factory.Sequence(lambda n: f"pix{n}@example.com")
    cpf_cnpj = "12345678901"
    pix_key_type = AsaasSubaccount.PixKeyType.RANDOM
    pix_key = factory.Sequence(lambda n: f"pix-key-{n}")
    asaas_wallet_id = factory.Sequence(lambda n: f"wal_test_{n}")
    account_status = AsaasSubaccount.AccountStatus.APPROVED


class CartFactory(DjangoModelFactory):
    class Meta:
        model = Cart

    tenant = factory.SubFactory(TenantFactory)
    resident = factory.SubFactory(ResidentFactory, tenant=factory.SelfAttribute("..tenant"))
    status = Cart.Status.OPEN
    total_value = factory.LazyFunction(lambda: Decimal("0"))


class CartItemFactory(DjangoModelFactory):
    class Meta:
        model = CartItem

    cart = factory.SubFactory(CartFactory)
    product = factory.SubFactory(
        ProductFactory,
        tenant=factory.SelfAttribute("..cart.tenant"),
    )
    quantity = 1
    unit_price = factory.LazyAttribute(lambda o: o.product.price)


class SubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = Subscription

    tenant = factory.SubFactory(TenantFactory)
    asaas_customer_id = factory.Sequence(lambda n: f"cus_test_{n}")
    asaas_subscription_id = factory.Sequence(lambda n: f"sub_test_{n}")
    status = Subscription.Status.ACTIVE
    trial_ends_at = factory.LazyAttribute(lambda o: o.tenant.trial_ends_at)
