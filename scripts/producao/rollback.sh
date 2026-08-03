#!/usr/bin/env bash
# Rollback produção: restaura dump Postgres + imagens do release alvo.
# Sempre restaura o banco (não há rollback só de container).
#
# Uso:
#   ./scripts/producao/rollback.sh              # ponteiro previous
#   ./scripts/producao/rollback.sh DEPLOY_ID    # release explícito
#   CONFIRM=1 ./scripts/producao/rollback.sh   # sem prompt interativo

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

production_run_remote_unless_on_server "$(basename "$0")" "$@"

production_cd
production_require_docker
production_require_env
production_release_init

TARGET="$(release_resolve_rollback_id "${1:-}")"
release_confirm_rollback "$TARGET"

echo "== MarketChat — rollback PRODUÇÃO -> ${TARGET} =="

echo "Parando backend/frontend..."
IMAGE_TAG=current production_compose stop backend frontend || true

release_restore_db "$TARGET"
release_tag_as_current "$TARGET"

# Após rollback, previous aponta para o current anterior (se diferente).
old_current="$(release_read_pointer current || true)"
if [[ -n "$old_current" && "$old_current" != "$TARGET" ]]; then
  release_write_pointer previous "$old_current"
fi
release_write_pointer current "$TARGET"

echo "Subindo containers com imagens ${TARGET}..."
IMAGE_TAG=current production_compose up -d

echo ""
echo "Aguardando serviços..."
sleep 8
production_compose ps
production_smoke_test

echo ""
echo "Rollback concluído: ${TARGET}"
