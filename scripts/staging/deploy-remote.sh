#!/usr/bin/env bash
# Atalho para deploy remoto (mesmo comportamento dos outros scripts em scripts/staging/).
#
# Uso:
#   ./scripts/staging/deploy-remote.sh full       # = deploy-full.sh
#   ./scripts/staging/deploy-remote.sh backend  # = deploy-backend.sh
#   ./scripts/staging/deploy-remote.sh frontend
#   ./scripts/staging/deploy-remote.sh bootstrap
#   ./scripts/staging/deploy-remote.sh sync      # só rsync (sem docker)
#
# Variáveis: STAGING_SSH, STAGING_PATH, PUSH_LOCAL_ENV — ver remote-lib.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-full}"

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
  *)
    echo "Uso: $0 {sync|bootstrap|full|backend|frontend}" >&2
    exit 1
    ;;
esac
