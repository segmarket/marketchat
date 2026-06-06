#!/usr/bin/env bash
# Rebuild e restart completo (backend + frontend) em produção.
# Uso: ./scripts/producao/deploy-full.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

production_run_remote_unless_on_server "$(basename "$0")"

production_cd
production_require_docker
production_require_env

echo "== MarketChat — deploy produção (full) =="

production_compose build
production_check_ports_available redeploy || exit 1
production_compose up -d

echo ""
echo "Aguardando serviços..."
sleep 6
production_compose ps
production_compose logs backend --tail 15

production_smoke_test
echo ""
echo "Deploy full concluído."
