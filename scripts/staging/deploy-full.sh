#!/usr/bin/env bash
# Rebuild e restart completo (backend + frontend) em staging no servidor 192.168.1.23.
# Antes do build: backup full do Postgres + versionamento de imagens.
# Uso: ./scripts/staging/deploy-full.sh
# No notebook: rsync + build Docker no servidor. No servidor: build local.
# Forçar build nesta máquina: STAGING_FORCE_LOCAL=1 ./scripts/staging/deploy-full.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

staging_run_remote_unless_on_server "$(basename "$0")" "$@"

staging_cd
staging_require_docker
staging_require_env
staging_release_init

DEPLOY_ID="$(release_new_id)"
echo "== MarketChat — deploy staging (full) =="
echo "   DEPLOY_ID=${DEPLOY_ID}"

release_backup_db "$DEPLOY_ID"

echo ""
echo "Build das imagens (tag ${DEPLOY_ID})..."
IMAGE_TAG="$DEPLOY_ID" staging_compose build

release_tag_as_current "$DEPLOY_ID"
release_record_after_deploy "$DEPLOY_ID"

echo ""
echo "Subindo containers (IMAGE_TAG=current)..."
IMAGE_TAG=current staging_compose up -d

release_prune

echo ""
echo "Aguardando serviços..."
sleep 5
staging_compose ps
staging_compose logs backend --tail 15

staging_smoke_test
echo ""
echo "Deploy full concluído. Release: ${DEPLOY_ID}"
echo "Rollback: ./scripts/staging/rollback.sh"
