#!/usr/bin/env bash
# Backup avulso do Postgres de produção (sem rebuild).
# Uso: ./scripts/producao/backup-db.sh

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
release_backup_db "$DEPLOY_ID"
echo "Backup avulso: $(release_backups_dir)/${DEPLOY_ID}/db.dump"
