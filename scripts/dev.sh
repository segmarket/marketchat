#!/usr/bin/env bash
# Sobe o backend Django e o front-end Vite.
# Porta da API: 8001 por padrão (8000 costuma estar com Portainer no Docker).
# Uso: na raiz do repositório: ./scripts/dev.sh
# Requisitos: Python com venv ativado (ou PATH com django), Node/npm no front-end.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DJANGO_PORT="${DJANGO_PORT:-8001}"

cleanup() {
  echo ""
  echo "Encerrando processos..."
  jobs -p 2>/dev/null | while read -r pid; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "== MarketChat dev =="
echo "API:  http://127.0.0.1:${DJANGO_PORT}  (python manage.py runserver)"
echo "Web:  http://127.0.0.1:5173  (npm run dev no front-end — confira o terminal do Vite)"
echo "Configure CORS em .env.development (CORS_ALLOWED_ORIGINS) se desligar CORS_ALLOW_ALL_ORIGINS."
echo ""

python manage.py runserver "0.0.0.0:${DJANGO_PORT}" &
(
  cd "$ROOT/front-end"
  export VITE_DEV_API_PORT="${DJANGO_PORT}"
  npm run dev
) &
wait
