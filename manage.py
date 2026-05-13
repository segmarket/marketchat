#!/usr/bin/env python
"""Ponto de entrada do Django."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. Ative o venv e instale as dependências."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
