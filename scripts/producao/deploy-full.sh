#!/usr/bin/env bash
# Rebuild e restart completo (backend + frontend) em produção.
# Antes do build: backup full do Postgres + versionamento de imagens.
# Uso: ./scripts/producao/deploy-full.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

production_run_remote_unless_on_server "$(basename "$0")" "$@"

production_cd
production_require_docker
production_require_env
production_release_init

DEPLOY_ID="$(release_new_id)"
echo "== MarketChat — deploy produção (full) =="
echo "   DEPLOY_ID=${DEPLOY_ID}"

release_backup_db "$DEPLOY_ID"

echo ""
echo "Build das imagens (tag ${DEPLOY_ID})..."
IMAGE_TAG="$DEPLOY_ID" production_compose build

release_tag_as_current "$DEPLOY_ID"
release_record_after_deploy "$DEPLOY_ID"

echo ""
echo "Subindo containers (IMAGE_TAG=current)..."
production_check_ports_available redeploy || exit 1
IMAGE_TAG=current production_compose up -d

release_prune

echo ""
echo "Aguardando serviços..."
sleep 6
production_compose ps
production_compose logs backend --tail 15

production_smoke_test
echo ""
echo "Deploy full concluído. Release: ${DEPLOY_ID}"
echo "Rollback: ./scripts/producao/rollback.sh"
