#!/usr/bin/env bash
# Rebuild e restart apenas do backend Django em produção.
# Uso: ./scripts/producao/deploy-backend.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

production_run_remote_unless_on_server "$(basename "$0")"

production_cd
production_require_docker
production_require_env

echo "== MarketChat — deploy produção (backend) =="

production_compose build backend
production_compose up -d backend --no-deps

echo ""
sleep 5
production_compose logs backend --tail 25

api_port="$(production_backend_port)"
be_code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${api_port}/api/auth/me/" 2>/dev/null || echo '000')"
echo ""
echo "API :$api_port -> HTTP $be_code (esperado 401)"
echo "Deploy backend concluído."
