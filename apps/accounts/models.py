from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório")
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuário deve ter is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuário deve ter is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField("e-mail", unique=True)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )
    is_tenant_admin = models.BooleanField(default=False)
    phone = models.CharField(max_length=32, blank=True, default="")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    def __str__(self) -> str:
        return self.email


class Lead(models.Model):
    """Lead capturado no cadastro para recuperação de vendas (funil F1/F2)."""

    class LeadType(models.TextChoices):
        F1 = "F1", "F1"
        F2 = "F2", "F2"

    class Status(models.TextChoices):
        NOVO = "NOVO", "Novo"
        EM_CONTATO = "EM_CONTATO", "Em Contato"
        SEM_INTERESSE = "SEM_INTERESSE", "Sem Interesse"
        AGUARDANDO_RETORNO = "AGUARDANDO_RETORNO", "Aguardando Retorno"
        CONVERTIDO = "CONVERTIDO", "Convertido"

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20)
    lead_type = models.CharField(
        max_length=2,
        choices=LeadType.choices,
        default=LeadType.F1,
    )
    company_name = models.CharField(max_length=255, blank=True, default="")
    company_address = models.CharField(max_length=512, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    state = models.CharField(max_length=2, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOVO,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"
