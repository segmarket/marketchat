from .dotenv_loader import load_env

# Produção: `.env` opcional + `.env.production` (segredos e flags de deploy).
load_env(".env", ".env.production")

from .base import *  # noqa: F403, E402

DEBUG = False
