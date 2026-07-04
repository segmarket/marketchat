#!/bin/sh
set -e

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

DB_BOOT_MAX_ATTEMPTS="${DB_BOOT_MAX_ATTEMPTS:-12}"
DB_BOOT_RETRY_SECONDS="${DB_BOOT_RETRY_SECONDS:-5}"

retry_db() {
  attempt=1
  while [ "$attempt" -le "$DB_BOOT_MAX_ATTEMPTS" ]; do
    if "$@"; then
      return 0
    fi
    if [ "$attempt" -eq "$DB_BOOT_MAX_ATTEMPTS" ]; then
      return 1
    fi
    echo "[marketchat] Banco indisponível (tentativa ${attempt}/${DB_BOOT_MAX_ATTEMPTS}). Aguardando ${DB_BOOT_RETRY_SECONDS}s..."
    sleep "$DB_BOOT_RETRY_SECONDS"
    attempt=$((attempt + 1))
  done
}

close_db_connections() {
  python - <<'PY'
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django

django.setup()

from django.db import connections

connections.close_all()
PY
}

echo "[marketchat] Boot: DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"

retry_db python manage.py migrate --noinput
echo "[marketchat] Migrations aplicadas."
close_db_connections

python manage.py collectstatic --noinput
echo "[marketchat] Arquivos estáticos coletados."

python - <<'PY'
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django

django.setup()

from django.conf import settings

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
GUNICORN_WORKERS="${GUNICORN_WORKERS:-2}"
GUNICORN_MAX_REQUESTS="${GUNICORN_MAX_REQUESTS:-1000}"
GUNICORN_MAX_REQUESTS_JITTER="${GUNICORN_MAX_REQUESTS_JITTER:-100}"

echo "[marketchat] Iniciando Gunicorn (workers=$GUNICORN_WORKERS, timeout=${GUNICORN_TIMEOUT}s)..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "$GUNICORN_WORKERS" \
  --timeout "$GUNICORN_TIMEOUT" \
  --graceful-timeout 30 \
  --max-requests "$GUNICORN_MAX_REQUESTS" \
  --max-requests-jitter "$GUNICORN_MAX_REQUESTS_JITTER"
