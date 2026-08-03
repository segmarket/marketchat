#!/usr/bin/env bash
# Funções compartilhadas pelos scripts de deploy em staging.
# Não execute este arquivo diretamente.

set -euo pipefail

STAGING_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAGING_ENV_FILE="${STAGING_ENV_FILE:-$STAGING_ROOT/.env.staging}"
COMPOSE_FILE="${COMPOSE_FILE:-$STAGING_ROOT/docker-compose.yml}"
STAGING_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Host de staging (build Docker sempre nesta máquina, exceto STAGING_FORCE_LOCAL=1 no notebook).
STAGING_SERVER_IP="${STAGING_SERVER_IP:-192.168.1.23}"

# Retorna 0 se o docker compose deve rodar nesta máquina (já estamos no servidor ou modo local forçado).
staging_should_run_local() {
  if [[ "${STAGING_FORCE_LOCAL:-}" == "1" ]]; then
    return 0
  fi
  if [[ "${STAGING_ON_SERVER:-}" == "1" ]]; then
    return 0
  fi
  if hostname -I 2>/dev/null | tr ' ' '\n' | grep -qx "$STAGING_SERVER_IP"; then
    return 0
  fi
  return 1
}

# Do notebook: rsync + SSH no servidor. No servidor: segue o script chamador (return 0).
staging_run_remote_unless_on_server() {
  local script_name="${1:?}"

  if staging_should_run_local; then
    return 0
  fi

  # shellcheck source=remote-lib.sh
  source "$STAGING_SCRIPT_DIR/remote-lib.sh"
  remote_require_tools

  echo "== MarketChat — deploy no servidor $STAGING_SSH (~/$STAGING_PATH) =="
  echo "   (docker compose roda no host remoto, não nesta máquina)"
  echo ""

  remote_sync

  if [[ "$script_name" == "bootstrap.sh" ]]; then
    set +e
    remote_ensure_env_on_server
    local env_rc=$?
    set -e
    if [[ "$env_rc" -eq 2 ]]; then
      exit 2
    fi
    if [[ "$env_rc" -ne 0 ]]; then
      exit "$env_rc"
    fi
  else
    remote_ensure_env_on_server
  fi

  remote_run_deploy_script "$script_name"
  exit 0
}

staging_cd() {
  cd "$STAGING_ROOT"
}

staging_require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Erro: Docker não encontrado no PATH." >&2
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "Erro: 'docker compose' não disponível." >&2
    exit 1
  fi
}

staging_require_env() {
  if [[ ! -f "$STAGING_ENV_FILE" ]]; then
    echo "Erro: arquivo $STAGING_ENV_FILE não existe." >&2
    echo "Copie o template: cp .env.staging.example .env.staging" >&2
    exit 1
  fi
  if grep -q 'altere-para-um-valor-aleatorio' "$STAGING_ENV_FILE" 2>/dev/null; then
    echo "Aviso: SECRET_KEY ainda parece ser o placeholder em .env.staging." >&2
  fi
}

staging_compose() {
  # --env-file alimenta interpolação ${VITE_*} no build do front.
  docker compose --env-file "$STAGING_ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

staging_backend_port() {
  # Porta publicada no host (compose: STAGING_BACKEND_PORT:8000). Default 8001 evita Portainer.
  if [[ -f "$STAGING_ENV_FILE" ]]; then
  # shellcheck disable=SC1090
    set -a && source "$STAGING_ENV_FILE" && set +a
  fi
  echo "${STAGING_BACKEND_PORT:-8001}"
}

staging_smoke_test() {
  local fe_code be_code api_port
  api_port="$(staging_backend_port)"
  fe_code="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/ 2>/dev/null || echo '000')"
  be_code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${api_port}/api/auth/me/" 2>/dev/null || echo '000')"
  echo ""
  echo "Smoke test (localhost no servidor):"
  echo "  Front :3000       -> HTTP $fe_code (esperado 200)"
  echo "  API   :$api_port  -> HTTP $be_code (esperado 401 sem token)"
}
