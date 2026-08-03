#!/usr/bin/env bash
# Biblioteca para deploy remoto (rsync + SSH). Não execute diretamente.

set -euo pipefail

REMOTE_LIB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAGING_SSH="${STAGING_SSH:-seguser@192.168.1.23}"
STAGING_PATH="${STAGING_PATH:-marketchat}"
RSYNC_EXCLUDES="${RSYNC_EXCLUDES:-$REMOTE_LIB_ROOT/scripts/staging/rsync-excludes.txt}"

# Envia .env.staging local para o servidor (padrão: não, para não sobrescrever segredos do host).
PUSH_LOCAL_ENV="${PUSH_LOCAL_ENV:-0}"

remote_require_tools() {
  if ! command -v rsync >/dev/null 2>&1; then
    echo "Erro: rsync não encontrado. Instale: sudo dnf install rsync" >&2
    exit 1
  fi
  if ! command -v ssh >/dev/null 2>&1; then
    echo "Erro: ssh não encontrado." >&2
    exit 1
  fi
}

remote_ensure_dir() {
  ssh "$STAGING_SSH" "mkdir -p \"\$HOME/$STAGING_PATH\""
}

remote_sync() {
  echo "== 1/2 Sincronizando código (rsync) -> $STAGING_SSH:~/$STAGING_PATH =="
  remote_ensure_dir

  local -a rsync_args=(
    -az --human-readable --delete
    --exclude-from="$RSYNC_EXCLUDES"
  )

  if [[ "$PUSH_LOCAL_ENV" == "1" && -f "$REMOTE_LIB_ROOT/.env.staging" ]]; then
    echo "   (incluindo .env.staging local — PUSH_LOCAL_ENV=1)"
  else
    rsync_args+=(--exclude '.env.staging')
  fi

  rsync "${rsync_args[@]}" \
    -e ssh \
    "$REMOTE_LIB_ROOT/" \
    "$STAGING_SSH:$STAGING_PATH/"

  echo "   Sincronização concluída."
}

remote_ensure_env_on_server() {
  ssh "$STAGING_SSH" bash -s <<EOF
set -euo pipefail
cd "\$HOME/$STAGING_PATH"
if [[ -f .env.staging ]]; then
  exit 0
fi
if [[ -f .env.staging.example ]]; then
  cp .env.staging.example .env.staging
  echo ""
  echo "AVISO: .env.staging criado no servidor a partir do example."
  echo "Edite no servidor: nano ~/$STAGING_PATH/.env.staging"
  echo "Depois rode novamente o deploy."
  exit 2
fi
echo "Erro: falta .env.staging no servidor." >&2
exit 1
EOF
}

remote_run_deploy_script() {
  local script_name="$1"
  shift
  local quoted_args=""
  local confirm_q
  if [[ "$#" -gt 0 ]]; then
    printf -v quoted_args '%q ' "$@"
  fi
  printf -v confirm_q '%q' "${CONFIRM:-}"
  echo ""
  echo "== 2/2 Build e deploy no servidor ($script_name) =="
  ssh -t "$STAGING_SSH" bash -s <<EOF
set -euo pipefail
cd "\$HOME/$STAGING_PATH"
chmod +x scripts/staging/*.sh scripts/lib/*.sh 2>/dev/null || chmod +x scripts/staging/*.sh
export STAGING_ON_SERVER=1
export STAGING_SKIP_ENV_PROMPT=1
export CONFIRM=${confirm_q}
./scripts/staging/${script_name} ${quoted_args}
EOF
}
