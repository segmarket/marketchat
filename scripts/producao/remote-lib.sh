#!/usr/bin/env bash
# Biblioteca para deploy remoto em produção (rsync + SSH). Não execute diretamente.

set -euo pipefail

REMOTE_LIB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROD_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$PROD_SCRIPT_DIR/env.deploy" ]]; then
  # shellcheck disable=SC1091
  set -a && source "$PROD_SCRIPT_DIR/env.deploy" && set +a
fi

PRODUCTION_SSH="${PRODUCTION_SSH:-seguser@10.10.10.140}"
PRODUCTION_PATH="${PRODUCTION_PATH:-marketchat}"
RSYNC_EXCLUDES="${RSYNC_EXCLUDES:-$PROD_SCRIPT_DIR/rsync-excludes.txt}"
PUSH_LOCAL_ENV="${PUSH_LOCAL_ENV:-0}"

prod_ssh_cmd() {
  if [[ -n "${DEPLOY_SSH_PASSWORD:-}" ]]; then
    if ! command -v sshpass >/dev/null 2>&1; then
      echo "Erro: DEPLOY_SSH_PASSWORD definido mas sshpass não está instalado." >&2
      echo "  sudo dnf install sshpass   ou use chave SSH e remova a senha de env.deploy" >&2
      exit 1
    fi
    sshpass -p "$DEPLOY_SSH_PASSWORD" ssh "$@"
  else
    ssh "$@"
  fi
}

prod_rsync_cmd() {
  if [[ -n "${DEPLOY_SSH_PASSWORD:-}" ]]; then
    if ! command -v sshpass >/dev/null 2>&1; then
      echo "Erro: DEPLOY_SSH_PASSWORD definido mas sshpass não está instalado." >&2
      exit 1
    fi
    RSYNC_RSH="sshpass -p ${DEPLOY_SSH_PASSWORD} ssh"
  else
    RSYNC_RSH="ssh"
  fi
}

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
  prod_ssh_cmd "$PRODUCTION_SSH" "mkdir -p \"\$HOME/$PRODUCTION_PATH\""
}

remote_sync() {
  echo "== 1/2 Sincronizando código (rsync) -> $PRODUCTION_SSH:~/$PRODUCTION_PATH =="
  remote_ensure_dir

  local -a rsync_args=(
    -az --human-readable --delete
    --exclude-from="$RSYNC_EXCLUDES"
  )

  if [[ "$PUSH_LOCAL_ENV" == "1" && -f "$REMOTE_LIB_ROOT/.env.production" ]]; then
    echo "   (incluindo .env.production local — PUSH_LOCAL_ENV=1)"
  else
    rsync_args+=(--exclude '.env.production')
  fi

  prod_rsync_cmd
  rsync "${rsync_args[@]}" \
    -e "$RSYNC_RSH" \
    "$REMOTE_LIB_ROOT/" \
    "$PRODUCTION_SSH:$PRODUCTION_PATH/"

  echo "   Sincronização concluída."
}

remote_ensure_env_on_server() {
  prod_ssh_cmd "$PRODUCTION_SSH" bash -s <<EOF
set -euo pipefail
cd "\$HOME/$PRODUCTION_PATH"
if [[ -f .env.production ]]; then
  exit 0
fi
if [[ -f .env.production.example ]]; then
  cp .env.production.example .env.production
  echo ""
  echo "AVISO: .env.production criado no servidor a partir do example."
  echo "Edite no servidor: nano ~/$PRODUCTION_PATH/.env.production"
  echo "Depois rode novamente o deploy."
  exit 2
fi
echo "Erro: falta .env.production no servidor." >&2
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
  prod_ssh_cmd -t "$PRODUCTION_SSH" bash -s <<EOF
set -euo pipefail
cd "\$HOME/$PRODUCTION_PATH"
chmod +x scripts/producao/*.sh scripts/lib/*.sh 2>/dev/null || chmod +x scripts/producao/*.sh
export PRODUCTION_ON_SERVER=1
export PRODUCTION_SKIP_ENV_PROMPT=1
export CONFIRM=${confirm_q}
./scripts/producao/${script_name} ${quoted_args}
EOF
}
