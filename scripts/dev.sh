#!/usr/bin/env bash
# Sobe o backend Django (porta 8000) e o front-end Vite (porta padrão do npm, geralmente 5173).
# Uso: na raiz do repositório: ./scripts/dev.sh
# Requisitos: Python com venv ativado (ou PATH com django), Node/npm no front-end.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

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
echo "API:  http://127.0.0.1:8000  (python manage.py runserver)"
echo "Web:  http://127.0.0.1:5173  (npm run dev no front-end — confira o terminal do Vite)"
echo "Configure CORS em .env.development (CORS_ALLOWED_ORIGINS) se desligar CORS_ALLOW_ALL_ORIGINS."
echo ""

python manage.py runserver 0.0.0.0:8000 &
(
  cd "$ROOT/front-end"
  npm run dev
) &
wait
