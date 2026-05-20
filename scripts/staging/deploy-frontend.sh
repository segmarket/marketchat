#!/usr/bin/env bash
# Rebuild e restart apenas do frontend React em staging (servidor 192.168.1.23).
# Lê VITE_* do .env.staging para o build.
# Uso: ./scripts/staging/deploy-frontend.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

staging_run_remote_unless_on_server "$(basename "$0")"

staging_cd
staging_require_docker
staging_require_env

echo "== MarketChat — deploy staging (frontend) =="

staging_compose build frontend
staging_compose up -d frontend --no-deps

echo ""
sleep 2
fe_code="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/ 2>/dev/null || echo '000')"
echo "Front :3000 -> HTTP $fe_code (esperado 200)"
echo "Deploy frontend concluído."
