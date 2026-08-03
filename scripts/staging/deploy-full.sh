#!/usr/bin/env bash
# Rebuild e restart completo (backend + frontend) em staging no servidor 192.168.1.23.
# Uso: ./scripts/staging/deploy-full.sh
# No notebook: rsync + build Docker no servidor. No servidor: build local.
# Forçar build nesta máquina: STAGING_FORCE_LOCAL=1 ./scripts/staging/deploy-full.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

staging_run_remote_unless_on_server "$(basename "$0")"

staging_cd
staging_require_docker
staging_require_env

echo "== MarketChat — deploy staging (full) =="

staging_compose build
staging_compose up -d

echo ""
echo "Aguardando serviços..."
sleep 5
staging_compose ps
staging_compose logs backend --tail 15

staging_smoke_test
echo ""
echo "Deploy full concluído."
