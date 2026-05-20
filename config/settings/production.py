from .dotenv_loader import load_env

# Produção: `.env` opcional + `.env.production` / `.env.staging` (deploy).
load_env(".env", ".env.production", ".env.staging")

from .base import *  # noqa: F403, E402

DEBUG = False

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
]
