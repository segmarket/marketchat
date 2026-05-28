from .dotenv_loader import load_env

# Testes: arquivo opcional (CI/local); variáveis abaixo sobrescrevem o necessário.
load_env(".env.test")

from .base import *  # noqa: F403, E402

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

SECRET_KEY = "test-secret-key-not-for-production"

ASAAS_API_KEY = "test-asaas-key"
ASAAS_API_URL = "https://api-sandbox.asaas.com/v3"
ASAAS_WEBHOOK_TOKEN = "test-webhook-token"
ASAAS_WEBHOOK_VERIFY = False

MEDIA_ROOT = BASE_DIR / "test_media"  # noqa: F405

REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/15")  # noqa: F405
