"""Carrega arquivos `.env` na raiz do projeto (último arquivo da lista tem precedência)."""

from pathlib import Path

import environ

# config/settings/dotenv_loader.py -> raiz do repositório
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def load_env(*filenames: str) -> None:
    for name in filenames:
        path = BASE_DIR / name
        if path.is_file():
            environ.Env.read_env(path, overwrite=True)
