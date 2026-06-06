from django.db import models


class PixKeyType(models.TextChoices):
    CPF = "CPF", "CPF"
    CNPJ = "CNPJ", "CNPJ"
    EMAIL = "EMAIL", "E-mail"
    PHONE = "PHONE", "Celular"
    RANDOM = "RANDOM", "Chave aleatória"
