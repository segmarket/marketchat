#!/usr/bin/env bash
# Rebuild e restart apenas do backend Django em staging (servidor 192.168.1.23).
# Uso: ./scripts/staging/deploy-backend.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

staging_run_remote_unless_on_server "$(basename "$0")"

staging_cd
staging_require_docker
staging_require_env

echo "== MarketChat — deploy staging (backend) =="

staging_compose build backend
staging_compose up -d backend --no-deps

echo ""
sleep 4
staging_compose logs backend --tail 20

api_port="$(staging_backend_port)"
be_code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${api_port}/api/auth/me/" 2>/dev/null || echo '000')"
echo ""
echo "API :$api_port -> HTTP $be_code (esperado 401)"
echo "Deploy backend concluído."
