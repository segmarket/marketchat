from .dotenv_loader import load_env

# Produção: `.env` opcional + `.env.production` / `.env.staging` (deploy).
load_env(".env", ".env.production", ".env.staging")

from .base import *  # noqa: F403, E402

DEBUG = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
TRUST_X_FORWARDED_FOR = True

DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000

# Conexões com Postgres: em produção use PgBouncer (pool) na frente do banco.
# Com PgBouncer em transaction pooling, mantenha DB_CONN_MAX_AGE=0 (padrão).
_db = DATABASES["default"]  # noqa: F405
_db["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=0)  # noqa: F405
_db["CONN_HEALTH_CHECKS"] = env.bool("DB_CONN_HEALTH_CHECKS", default=True)  # noqa: F405
_db.setdefault("OPTIONS", {})
_db["OPTIONS"]["connect_timeout"] = env.int("DB_CONNECT_TIMEOUT", default=10)  # noqa: F405

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
]
