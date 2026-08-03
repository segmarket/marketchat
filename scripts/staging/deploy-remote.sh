#!/usr/bin/env bash
# Atalho para deploy remoto (mesmo comportamento dos outros scripts em scripts/staging/).
#
# Uso:
#   ./scripts/staging/deploy-remote.sh full       # = deploy-full.sh
#   ./scripts/staging/deploy-remote.sh backend
#   ./scripts/staging/deploy-remote.sh frontend
#   ./scripts/staging/deploy-remote.sh bootstrap
#   ./scripts/staging/deploy-remote.sh sync      # só rsync (sem docker)
#   ./scripts/staging/deploy-remote.sh rollback [DEPLOY_ID]
#   ./scripts/staging/deploy-remote.sh backup
#
# Variáveis: STAGING_SSH, STAGING_PATH, PUSH_LOCAL_ENV — ver remote-lib.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-full}"
shift || true

case "$ACTION" in
  sync)
    # shellcheck source=remote-lib.sh
    source "$SCRIPT_DIR/remote-lib.sh"
    remote_require_tools
    remote_sync
    ;;
  bootstrap)
    exec "$SCRIPT_DIR/bootstrap.sh"
    ;;
  full)
    exec "$SCRIPT_DIR/deploy-full.sh"
    ;;
  backend)
    exec "$SCRIPT_DIR/deploy-backend.sh"
    ;;
  frontend)
    exec "$SCRIPT_DIR/deploy-frontend.sh"
    ;;
  rollback)
    exec "$SCRIPT_DIR/rollback.sh" "$@"
    ;;
  backup)
    exec "$SCRIPT_DIR/backup-db.sh"
    ;;
  *)
    echo "Uso: $0 {sync|bootstrap|full|backend|frontend|rollback|backup}" >&2
    exit 1
    ;;
esac
