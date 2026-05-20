"""Configurações compartilhadas.

Variáveis de ambiente vêm de arquivos carregados em `local.py`, `production.py` ou `test.py`
(ver `dotenv_loader.load_env`). Não chame `read_env` aqui para evitar ordem duplicada.
"""
from datetime import timedelta
import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _resolve_database_url() -> str:
    """DATABASE_URL explícita ou montagem a partir de DB_* (Docker/staging)."""
    explicit = (os.environ.get("DATABASE_URL") or "").strip()
    if explicit:
        return explicit
    host = (os.environ.get("DB_HOST") or "").strip()
    if not host:
        return f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    user = (os.environ.get("DB_USER") or "postgres").strip()
    password = (os.environ.get("DB_PASSWORD") or "postgres").strip()
    port = (os.environ.get("DB_PORT") or "5432").strip()
    name = (os.environ.get("DB_NAME") or "postgres").strip()
    return f"postgres://{user}:{password}@{host}:{port}/{name}"


env = environ.Env(
    DEBUG=(bool, False),
)

SECRET_KEY = env("SECRET_KEY", default="unsafe-dev-key-change-in-production")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "apps.tenants",
    "apps.accounts",
    "apps.billing",
    "apps.integrations",
    "apps.products",
    "apps.markets",
    "apps.residents",
    "apps.chatbot",
    "apps.sales",
    "apps.notifications",
    "apps.onboarding",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.tenants.middleware.TenantJWTContextMiddleware",
    "apps.tenants.middleware.TenantBillingBlockMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": env.db_url_config(_resolve_database_url()),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "marketchat",
    }
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# Admin/login e formulários Django atrás de proxy (staging-app, etc.)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
# Hostname usado só na verificação TLS (SNI) após STARTTLS, quando EMAIL_HOST é CNAME
# e o certificado é emitido para outro nome (ex.: Mailhostbox).
EMAIL_SMTP_TLS_SERVERNAME = env("EMAIL_SMTP_TLS_SERVERNAME", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@localhost")

FRONTEND_PASSWORD_RESET_URL = env(
    "FRONTEND_PASSWORD_RESET_URL",
    default="http://localhost:5173/reset-password",
)

ASAAS_API_URL = env("ASAAS_API_URL", default="https://api-sandbox.asaas.com/v3")
# Chaves Asaas começam com "$aact_...". O django-environ trata "$" no início como "proxy" para outra
# variável de ambiente e acaba devolvendo vazio — ler direto de os.environ (valor já carregado pelo read_env).
ASAAS_API_KEY = os.environ.get("ASAAS_API_KEY", "")
ASAAS_WEBHOOK_TOKEN = env("ASAAS_WEBHOOK_TOKEN", default="")
# Em produção mantenha True e defina ASAAS_WEBHOOK_TOKEN. Em dev pode ser False (ver .env.development).
ASAAS_WEBHOOK_VERIFY = env.bool("ASAAS_WEBHOOK_VERIFY", default=True)

TRIAL_DAYS = env.int("TRIAL_DAYS", default=7)
DEFAULT_SUBSCRIPTION_VALUE = env.float("DEFAULT_SUBSCRIPTION_VALUE", default=29.9)
MARKET_MONTHLY_PRICE = env.float("MARKET_MONTHLY_PRICE", default=59.90)
BILLING_GRACE_DAYS = env.int("BILLING_GRACE_DAYS", default=3)
ASAAS_SUBACCOUNT_INCOME_VALUE = env.float("ASAAS_SUBACCOUNT_INCOME_VALUE", default=5000.0)
# CPF usado ao criar cliente Asaas do morador (sandbox); use um CPF válido de teste.
ASAAS_RESIDENT_DEFAULT_CPF = env("ASAAS_RESIDENT_DEFAULT_CPF", default="11144477735")
# Dev only (com DEBUG=True): cobrança Pix na conta principal, sem split para subconta.
ASAAS_PIX_USE_MAIN_ACCOUNT_IN_DEV = env.bool("ASAAS_PIX_USE_MAIN_ACCOUNT_IN_DEV", default=False)

RESIDENT_CONDO_MATCH_MIN_RATIO = env.float("RESIDENT_CONDO_MATCH_MIN_RATIO", default=0.55)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o-mini")
OPENAI_HISTORY_WINDOW = env.int("OPENAI_HISTORY_WINDOW", default=6)

EVOLUTION_API_BASE_URL = (
    os.environ.get("EVOLUTION_API_BASE_URL")
    or os.environ.get("EVOLUTION_API_URL")
    or "http://127.0.0.1:8080"
)
EVOLUTION_GLOBAL_API_KEY = (
    os.environ.get("EVOLUTION_GLOBAL_API_KEY")
    or os.environ.get("EVOLUTION_DEFAULT_API_KEY")
    or os.environ.get("EVOLUTION_API_TOKEN")
    or ""
)
PUBLIC_WEBHOOK_BASE_URL = env(
    "PUBLIC_WEBHOOK_BASE_URL",
    default="http://host.docker.internal:8001",
)
EVOLUTION_WEBHOOK_EVENTS = env.list(
    "EVOLUTION_WEBHOOK_EVENTS",
    default=["MESSAGE", "CONNECTION", "QRCODE"],
)
WEBHOOK_SHARED_SECRET = env("WEBHOOK_SHARED_SECRET", default="")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
