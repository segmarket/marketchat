#!/usr/bin/env bash
# Atalho: ./scripts/deploy-prd.sh {full|backend|frontend|bootstrap|sync|rollback|backup}
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/producao/deploy-remote.sh" "$@"
