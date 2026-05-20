#!/usr/bin/env bash
# Primeiro deploy em staging: prepara .env, build e sobe backend + frontend.
# O entrypoint do backend já roda migrate e collectstatic no primeiro boot.
#
# Uso (notebook ou servidor): ./scripts/staging/bootstrap.sh
# Por padrão faz rsync + build Docker em 192.168.1.23 (seguser@192.168.1.23).
#
# Pré-requisitos no servidor (192.168.1.23):
#   - Docker + Docker Compose
#   - Postgres (:5432) e Evolution (:8080) no host
#   - Porta 8001 livre para API (Portainer usa 8000) e 3000 para o front
#   - Apache: docs/apache-staging.conf.example

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

staging_run_remote_unless_on_server "$(basename "$0")"

staging_cd
staging_require_docker

echo "== MarketChat — bootstrap staging (primeiro deploy) =="
echo "Diretório: $STAGING_ROOT"
echo ""

if [[ ! -f "$STAGING_ENV_FILE" ]]; then
  if [[ -f "$STAGING_ROOT/.env.staging.example" ]]; then
    cp "$STAGING_ROOT/.env.staging.example" "$STAGING_ENV_FILE"
    echo "Criado $STAGING_ENV_FILE a partir do example."
    echo "IMPORTANTE: edite SECRET_KEY, EVOLUTION_GLOBAL_API_KEY, ASAAS_*, OPENAI_* antes de continuar."
    if [[ -z "${STAGING_SKIP_ENV_PROMPT:-}" ]]; then
      echo "Pressione Enter quando terminar a edição, ou Ctrl+C para cancelar."
      read -r _
    fi
  else
    echo "Erro: .env.staging.example não encontrado." >&2
    exit 1
  fi
fi

staging_require_env

echo ""
echo "1/3 — Build das imagens (pode demorar na primeira vez)..."
staging_compose build

echo ""
echo "2/3 — Subindo containers..."
staging_compose up -d

echo ""
echo "3/3 — Aguardando backend (migrate + gunicorn)..."
sleep 6
staging_compose logs backend --tail 25

staging_smoke_test

echo ""
echo "Bootstrap concluído."
echo "Próximos passos:"
echo "  - Configurar Apache: docs/apache-staging.conf.example"
echo "  - Atualizações futuras: ./scripts/staging/deploy-full.sh"
echo "  - Só API: ./scripts/staging/deploy-backend.sh"
echo "  - Só painel: ./scripts/staging/deploy-frontend.sh"
