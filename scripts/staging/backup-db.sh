#!/usr/bin/env bash
# Backup avulso do Postgres de staging (sem rebuild).
# Uso: ./scripts/staging/backup-db.sh

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
release_backup_db "$DEPLOY_ID"
echo "Backup avulso: $(release_backups_dir)/${DEPLOY_ID}/db.dump"
