#!/usr/bin/env bash
# Funções compartilhadas pelos scripts de deploy em produção.
# Não execute este arquivo diretamente.

set -euo pipefail

PRODUCTION_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PRODUCTION_ENV_FILE="${PRODUCTION_ENV_FILE:-$PRODUCTION_ROOT/.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-$PRODUCTION_ROOT/docker-compose.production.yml}"
PRODUCTION_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$PRODUCTION_SCRIPT_DIR/env.deploy" ]]; then
  # shellcheck disable=SC1091
  set -a && source "$PRODUCTION_SCRIPT_DIR/env.deploy" && set +a
fi

PRODUCTION_SERVER_IP="${PRODUCTION_SERVER_IP:-10.10.10.140}"

production_should_run_local() {
  if [[ "${PRODUCTION_FORCE_LOCAL:-}" == "1" ]]; then
    return 0
  fi
  if [[ "${PRODUCTION_ON_SERVER:-}" == "1" ]]; then
    return 0
  fi
  if hostname -I 2>/dev/null | tr ' ' '\n' | grep -qx "$PRODUCTION_SERVER_IP"; then
    return 0
  fi
  return 1
}

production_run_remote_unless_on_server() {
  local script_name="${1:?}"

  if production_should_run_local; then
    return 0
  fi

  # shellcheck source=remote-lib.sh
  source "$PRODUCTION_SCRIPT_DIR/remote-lib.sh"
  remote_require_tools

  echo "== MarketChat — deploy PRODUÇÃO em $PRODUCTION_SSH (~/$PRODUCTION_PATH) =="
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

production_cd() {
  cd "$PRODUCTION_ROOT"
}

production_require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Erro: Docker não encontrado no PATH." >&2
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "Erro: 'docker compose' não disponível." >&2
    exit 1
  fi
}

production_require_env() {
  if [[ ! -f "$PRODUCTION_ENV_FILE" ]]; then
    echo "Erro: arquivo $PRODUCTION_ENV_FILE não existe." >&2
    echo "Copie o template: cp .env.production.example .env.production" >&2
    exit 1
  fi
  if grep -q 'altere-para-um-valor-aleatorio' "$PRODUCTION_ENV_FILE" 2>/dev/null; then
    echo "Aviso: SECRET_KEY ainda parece ser placeholder em .env.production." >&2
  fi
}

# Lê uma variável do .env sem interpretar $ (evita quebrar ASAAS_API_KEY=$aact_...).
production_env_get() {
  local key="${1:?}"
  local default="${2:-}"
  if [[ ! -f "$PRODUCTION_ENV_FILE" ]]; then
    echo "$default"
    return
  fi
  local raw
  raw="$(grep -E "^${key}=" "$PRODUCTION_ENV_FILE" | tail -1 | cut -d= -f2- || true)"
  raw="${raw%$'\r'}"
  raw="${raw#\"}"
  raw="${raw%\"}"
  raw="${raw#\'}"
  raw="${raw%\'}"
  if [[ -n "$raw" ]]; then
    echo "$raw"
  else
    echo "$default"
  fi
}

# Só exporta VITE_* e PRODUCTION_* para o Compose (build args / portas).
# O restante vai ao container via env_file: .env.production (valor literal, com $).
production_compose() {
  if [[ -f "$PRODUCTION_ENV_FILE" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ "$line" =~ ^[[:space:]]*# ]] && continue
      [[ -z "${line//[[:space:]]/}" ]] && continue
      if [[ "$line" =~ ^(VITE_|PRODUCTION_) ]]; then
        export "$line"
      fi
    done < "$PRODUCTION_ENV_FILE"
  fi
  docker compose -f "$COMPOSE_FILE" "$@"
}

# Retorna 0 se algum container MarketChat publica a porta no host.
production_marketchat_owns_port() {
  local port="${1:?}"
  local name ports
  for name in marketchat_backend_prd marketchat_frontend_prd; do
    ports="$(docker ps --filter "name=^${name}$" --format '{{.Ports}}' 2>/dev/null || true)"
    if [[ -n "$ports" ]] && grep -qE "(^|[, ])[^ ]*:${port}->" <<<"$ports"; then
      return 0
    fi
  done
  return 1
}

# mode=bootstrap (padrão): portas devem estar livres (primeiro deploy).
# mode=redeploy: portas em uso pelos containers MarketChat são aceitas (rolling update).
production_check_ports_available() {
  local mode="${1:-bootstrap}"
  local api_port fe_port label
  api_port="$(production_env_get PRODUCTION_BACKEND_PORT 9001)"
  fe_port="$(production_env_get PRODUCTION_FRONTEND_PORT 3000)"
  local err=0
  if ! command -v ss >/dev/null 2>&1; then
    return 0
  fi
  for label in "API:${api_port}" "front:${fe_port}"; do
    local port="${label#*:}"
    local svc="${label%%:*}"
    if ! ss -tln 2>/dev/null | grep -q ":${port} "; then
      continue
    fi
    if [[ "$mode" == "redeploy" ]] && production_marketchat_owns_port "$port"; then
      echo "Porta ${port} (${svc}) em uso pelos containers MarketChat — redeploy OK."
      continue
    fi
    echo "Erro: porta ${port} (${svc}) já está em uso no servidor." >&2
    echo "  Diagnóstico: ss -tlnp | grep :${port}" >&2
    err=1
  done
  return "$err"
}

production_backend_port() {
  production_env_get PRODUCTION_BACKEND_PORT 9001
}

production_frontend_port() {
  production_env_get PRODUCTION_FRONTEND_PORT 3000
}

production_smoke_test() {
  local fe_code be_code api_port fe_port
  api_port="$(production_backend_port)"
  fe_port="$(production_frontend_port)"
  fe_code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${fe_port}/" 2>/dev/null || echo '000')"
  be_code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${api_port}/api/auth/me/" 2>/dev/null || echo '000')"
  echo ""
  echo "Smoke test (localhost no servidor):"
  echo "  Front :$fe_port       -> HTTP $fe_code (esperado 200)"
  echo "  API   :$api_port      -> HTTP $be_code (esperado 401 sem token)"
}
