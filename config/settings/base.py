"""Configurações compartilhadas.

Variáveis de ambiente vêm de arquivos carregados em `local.py`, `production.py` ou `test.py`
(ver `dotenv_loader.load_env`). Não chame `read_env` aqui para evitar ordem duplicada.
"""
from datetime import timedelta
import hashlib
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


def _jwt_signing_key() -> str:
    """
    Chave dedicada para assinar JWT (evita reutilizar SECRET_KEY curta e alertas PyJWT).
    Use JWT_SIGNING_KEY no .env em produção (mín. 32 bytes para HS256).
    """
    dedicated = (env("JWT_SIGNING_KEY", default="") or "").strip()
    key = dedicated or SECRET_KEY
    if len(key.encode("utf-8")) < 32:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()
    return key
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
    "apps.support",
    "apps.core",
    "apps.financial",
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

REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CHAT_CONTEXT_TTL_SECONDS = env.int("CHAT_CONTEXT_TTL_SECONDS", default=1200)
CHAT_CONTEXT_MAX_MESSAGES = env.int("CHAT_CONTEXT_MAX_MESSAGES", default=4)
PRODUCT_FUZZY_MATCH_THRESHOLD = env.float("PRODUCT_FUZZY_MATCH_THRESHOLD", default=0.65)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Redis 7+ com senha: redis-py RESP3 envia HELLO antes de AUTH e falha.
            "CONNECTION_POOL_KWARGS": {"protocol": 2},
        },
    }
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ALGORITHM": "HS256",
    "SIGNING_KEY": _jwt_signing_key(),
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
# Remetente dos e-mails transacionais. Deve ser um endereço autorizado no SMTP (mesmo domínio/conta
# que EMAIL_HOST_USER). Se vazio, usa DEFAULT_FROM_EMAIL com nome "MarketChat".
_transactional_from = env("TRANSACTIONAL_FROM_EMAIL", default="").strip()
if _transactional_from:
    TRANSACTIONAL_FROM_EMAIL = _transactional_from
elif DEFAULT_FROM_EMAIL and "<" not in DEFAULT_FROM_EMAIL:
    TRANSACTIONAL_FROM_EMAIL = f"MarketChat <{DEFAULT_FROM_EMAIL.strip()}>"
else:
    TRANSACTIONAL_FROM_EMAIL = DEFAULT_FROM_EMAIL

MARKETING_PUBLIC_ORIGIN = env("MARKETING_PUBLIC_ORIGIN", default="http://localhost:5173").rstrip("/")
# Painel React (rotas /signin, /reset-password). Em dev use app.localhost (mesma porta do Vite).
FRONTEND_APP_ORIGIN = env("FRONTEND_APP_ORIGIN", default="http://app.localhost:5173").rstrip("/")
FRONTEND_SIGNIN_URL = env(
    "FRONTEND_SIGNIN_URL",
    default=f"{FRONTEND_APP_ORIGIN}/signin",
).rstrip("/")
FRONTEND_PASSWORD_RESET_URL = env(
    "FRONTEND_PASSWORD_RESET_URL",
    default=f"{FRONTEND_APP_ORIGIN}/reset-password",
).rstrip("/")

# Logo nos e-mails: anexo inline (CID) se o arquivo existir; senão URL pública.
EMAIL_BRAND_LOGO_CID = "marketchat-logo"
EMAIL_BRAND_LOGO_PATH = env(
    "EMAIL_BRAND_LOGO_PATH",
    default=str(
        BASE_DIR
        / "front-end"
        / "public"
        / "images"
        / "brand"
        / "logotipo_marketchat_completo_PRETO.gif"
    ),
)
EMAIL_BRAND_LOGO_URL = env("EMAIL_BRAND_LOGO_URL", default="").strip()
if not EMAIL_BRAND_LOGO_URL:
    EMAIL_BRAND_LOGO_URL = (
        f"{MARKETING_PUBLIC_ORIGIN}/images/brand/logotipo_marketchat_completo_PRETO.gif"
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
# CPF usado ao criar cliente Asaas do morador (sandbox); use um CPF válido de teste.
ASAAS_RESIDENT_DEFAULT_CPF = env("ASAAS_RESIDENT_DEFAULT_CPF", default="11144477735")
# Taxa da plataforma sobre vendas Pix (credita líquido = bruto - taxa%).
FINANCIAL_PLATFORM_FEE_PERCENT = env.float("FINANCIAL_PLATFORM_FEE_PERCENT", default=2.0)

RESIDENT_CONDO_MATCH_MIN_RATIO = env.float("RESIDENT_CONDO_MATCH_MIN_RATIO", default=0.55)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o-mini")
OPENAI_HISTORY_WINDOW = env.int("OPENAI_HISTORY_WINDOW", default=6)
SUPPORT_COPILOT_HISTORY_MAX = env.int("SUPPORT_COPILOT_HISTORY_MAX", default=20)
SUPPORT_COPILOT_MAX_TOKENS = env.int("SUPPORT_COPILOT_MAX_TOKENS", default=500)
SUPPORT_COPILOT_TEMPERATURE = env.float("SUPPORT_COPILOT_TEMPERATURE", default=0.3)

# Inatividade: ao receber mensagem após este intervalo, carrinho e FSM são resetados.
CHAT_SESSION_LAZY_EXPIRY_MINUTES = env.int("CHAT_SESSION_LAZY_EXPIRY_MINUTES", default=30)

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
