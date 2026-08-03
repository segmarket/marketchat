#!/usr/bin/env bash
# Rollback staging: restaura dump Postgres + imagens do release alvo.
# Sempre restaura o banco (não há rollback só de container).
#
# Uso:
#   ./scripts/staging/rollback.sh              # ponteiro previous
#   ./scripts/staging/rollback.sh DEPLOY_ID    # release explícito
#   CONFIRM=1 ./scripts/staging/rollback.sh   # sem prompt interativo

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

staging_run_remote_unless_on_server "$(basename "$0")" "$@"

staging_cd
staging_require_docker
staging_require_env
staging_release_init

TARGET="$(release_resolve_rollback_id "${1:-}")"
release_confirm_rollback "$TARGET"

echo "== MarketChat — rollback STAGING -> ${TARGET} =="

echo "Parando backend/frontend..."
IMAGE_TAG=current staging_compose stop backend frontend || true

release_restore_db "$TARGET"
release_tag_as_current "$TARGET"

old_current="$(release_read_pointer current || true)"
if [[ -n "$old_current" && "$old_current" != "$TARGET" ]]; then
  release_write_pointer previous "$old_current"
fi
release_write_pointer current "$TARGET"

echo "Subindo containers com imagens ${TARGET}..."
IMAGE_TAG=current staging_compose up -d

echo ""
echo "Aguardando serviços..."
sleep 5
staging_compose ps
staging_smoke_test

echo ""
echo "Rollback concluído: ${TARGET}"
