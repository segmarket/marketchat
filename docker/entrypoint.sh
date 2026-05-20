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
if evo_url:
    print(f"[marketchat] Evolution API configurada: {evo_url}")
else:
    print("[marketchat] AVISO: EVOLUTION_API_BASE_URL não definida.", file=sys.stderr)
PY

echo "[marketchat] Iniciando Gunicorn na porta 8000..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
