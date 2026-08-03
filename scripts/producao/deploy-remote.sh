#!/usr/bin/env bash
# Atalho para deploy remoto em produção.
#
# Uso:
#   ./scripts/producao/deploy-remote.sh full
#   ./scripts/producao/deploy-remote.sh backend
#   ./scripts/producao/deploy-remote.sh frontend
#   ./scripts/producao/deploy-remote.sh bootstrap
#   ./scripts/producao/deploy-remote.sh sync
#
# Configuração: scripts/producao/env.deploy (copie de env.deploy.example)

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
