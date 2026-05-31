#!/usr/bin/env bash
# Primeiro deploy em produção: prepara .env, build e sobe backend + frontend.
#
# Uso (notebook): ./scripts/producao/bootstrap.sh
# Por padrão faz rsync + build Docker em 10.10.10.140 (seguser@10.10.10.140).
#
# Pré-requisitos no servidor:
#   - Docker + Docker Compose
#   - Postgres (192.168.1.30), Evolution (:8090), Redis externo (10.10.10.150)
#   - Portas 9001 (API) e 3000 (front) livres
#   - Apache: ProxyPass /api -> :9001 e / -> :3000 em app.marketchat.com.br

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

production_run_remote_unless_on_server "$(basename "$0")"

production_cd
production_require_docker

echo "== MarketChat — bootstrap PRODUÇÃO (primeiro deploy) =="
echo "Diretório: $PRODUCTION_ROOT"
echo ""

if [[ ! -f "$PRODUCTION_ENV_FILE" ]]; then
  if [[ -f "$PRODUCTION_ROOT/.env.production.example" ]]; then
    cp "$PRODUCTION_ROOT/.env.production.example" "$PRODUCTION_ENV_FILE"
    echo "Criado $PRODUCTION_ENV_FILE a partir do example."
    echo "IMPORTANTE: edite segredos (SECRET_KEY, DATABASE_URL, ASAAS_*, etc.) antes de continuar."
    if [[ -z "${PRODUCTION_SKIP_ENV_PROMPT:-}" ]]; then
      echo "Pressione Enter quando terminar a edição, ou Ctrl+C para cancelar."
      read -r _
    fi
  else
    echo "Erro: .env.production.example não encontrado." >&2
    exit 1
  fi
fi

production_require_env

echo ""
echo "1/3 — Build das imagens (pode demorar na primeira vez)..."
production_compose build

echo ""
echo "2/3 — Subindo containers..."
production_check_ports_available || exit 1
production_compose up -d

echo ""
echo "3/3 — Aguardando backend (migrate + gunicorn)..."
sleep 8
production_compose logs backend --tail 30

production_smoke_test

echo ""
echo "Bootstrap produção concluído."
echo "Próximos passos:"
echo "  - Apache em app.marketchat.com.br (ProxyPass /api -> :9001, / -> :3000)"
echo "  - Atualizações: ./scripts/producao/deploy-full.sh"
