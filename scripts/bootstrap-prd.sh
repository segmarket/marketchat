#!/usr/bin/env bash
# Atalho: rode de qualquer pasta — ex. ./scripts/bootstrap-prd.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/producao/bootstrap.sh" "$@"
