#!/usr/bin/env bash
# Rebuild e restart apenas do frontend React em produção.
# Lê VITE_* do .env.production para o build.
# Uso: ./scripts/producao/deploy-frontend.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

production_run_remote_unless_on_server "$(basename "$0")"

production_cd
production_require_docker
production_require_env

echo "== MarketChat — deploy produção (frontend) =="

production_compose build frontend
production_compose up -d frontend --no-deps

echo ""
sleep 2
fe_port="$(production_frontend_port)"
fe_code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${fe_port}/" 2>/dev/null || echo '000')"
echo "Front :$fe_port -> HTTP $fe_code (esperado 200)"
echo "Deploy frontend concluído."
