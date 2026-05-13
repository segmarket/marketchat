import logging

from .dotenv_loader import BASE_DIR, load_env

# Opcional: `.env` (compartilhado) e depois `.env.development` (sobrescreve chaves de dev).
# Só chaves presentes no segundo arquivo substituem as do primeiro; chaves só no primeiro permanecem.
load_env(".env", ".env.development")

from .base import *  # noqa: F403, E402

logger = logging.getLogger(__name__)
if not ASAAS_API_KEY.strip():  # noqa: F405
    logger.warning(
        "ASAAS_API_KEY está vazia após carregar %s/.env e %s/.env.development. "
        "Defina a chave em um dos dois arquivos (na raiz do projeto, junto de manage.py). "
        "Se .env contém ASAAS_API_KEY= sem valor, adicione a chave também em .env.development "
        "ou remova a linha vazia do .env.",
        BASE_DIR,
        BASE_DIR,
    )

DEBUG = True
# True = qualquer origem (lista CORS_ALLOWED_ORIGINS é ignorada pelo django-cors-headers).
# False = use apenas CORS_ALLOWED_ORIGINS do .env.development (ex.: só o Vite).
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)
