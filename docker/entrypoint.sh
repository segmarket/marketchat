#!/bin/sh
set -e

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

echo "[marketchat] Boot: DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"

python manage.py migrate --noinput
echo "[marketchat] Migrations aplicadas."

python manage.py collectstatic --noinput
echo "[marketchat] Arquivos estáticos coletados."

python - <<'PY'
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django

django.setup()

from django.conf import settings
from django.db import connection

try:
    connection.ensure_connection()
    vendor = connection.vendor
    db_name = settings.DATABASES["default"].get("NAME", "?")
    print(f"[marketchat] Banco OK ({vendor}, database={db_name}).")
except Exception as exc:
    print(f"[marketchat] ERRO ao conectar ao banco: {exc}", file=sys.stderr)
    sys.exit(1)

evo_url = getattr(settings, "EVOLUTION_API_BASE_URL", "")
evo_key = getattr(settings, "EVOLUTION_GLOBAL_API_KEY", "")
if evo_url:
    print(f"[marketchat] Evolution API configurada: {evo_url}")
    if not (evo_key or "").strip():
        print(
            "[marketchat] AVISO: EVOLUTION_GLOBAL_API_KEY vazia — WhatsApp retornará 401.",
            file=sys.stderr,
        )
    else:
        try:
            from apps.integrations.services.evolution_client import EvolutionClient

            EvolutionClient().check_global_api_key()
            print("[marketchat] Evolution: chave administrativa OK (GET /instance/all).")
        except Exception as exc:
            print(f"[marketchat] AVISO Evolution (auth/rede): {exc}", file=sys.stderr)
else:
    print("[marketchat] AVISO: EVOLUTION_API_BASE_URL não definida.", file=sys.stderr)
PY

GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"

echo "[marketchat] Iniciando Gunicorn (workers=$GUNICORN_WORKERS, timeout=${GUNICORN_TIMEOUT}s)..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "$GUNICORN_WORKERS" \
  --timeout "$GUNICORN_TIMEOUT" \
  --graceful-timeout 30
