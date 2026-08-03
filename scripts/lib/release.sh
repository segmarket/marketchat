#!/usr/bin/env bash
# Biblioteca compartilhada: backup Postgres + versionamento de imagens + rollback.
# Não execute diretamente. Source a partir de scripts/staging|producao.
#
# Variáveis obrigatórias antes do source (ou definidas pelo caller):
#   RELEASE_ROOT              raiz do projeto no servidor
#   RELEASE_ENV_FILE          .env.staging ou .env.production
#   RELEASE_BACKEND_IMAGE     ex.: marketchat-backend-prd
#   RELEASE_FRONTEND_IMAGE    ex.: marketchat-frontend-prd
#
# Opcionais:
#   RELEASE_KEEP              quantos releases manter (default 5)
#   RELEASE_POSTGRES_IMAGE    imagem cliente pg_dump/pg_restore (default postgres:16-alpine)

set -euo pipefail

RELEASE_KEEP="${RELEASE_KEEP:-5}"
RELEASE_POSTGRES_IMAGE="${RELEASE_POSTGRES_IMAGE:-postgres:16-alpine}"

release_require_vars() {
  local missing=0
  for key in RELEASE_ROOT RELEASE_ENV_FILE RELEASE_BACKEND_IMAGE RELEASE_FRONTEND_IMAGE; do
    if [[ -z "${!key:-}" ]]; then
      echo "Erro: $key não definido para scripts/lib/release.sh" >&2
      missing=1
    fi
  done
  if [[ "$missing" -ne 0 ]]; then
    exit 1
  fi
}

release_backups_dir() {
  echo "${RELEASE_ROOT}/backups"
}

release_releases_dir() {
  echo "${RELEASE_ROOT}/releases"
}

release_ensure_dirs() {
  mkdir -p "$(release_backups_dir)" "$(release_releases_dir)"
}

release_new_id() {
  local sha
  sha="$(git -C "$RELEASE_ROOT" rev-parse --short HEAD 2>/dev/null || echo local)"
  echo "$(date +%Y%m%d-%H%M%S)-${sha}"
}

release_env_get() {
  local key="${1:?}"
  local default="${2:-}"
  if [[ ! -f "$RELEASE_ENV_FILE" ]]; then
    echo "$default"
    return
  fi
  local raw
  raw="$(grep -E "^${key}=" "$RELEASE_ENV_FILE" | tail -1 | cut -d= -f2- || true)"
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

# Imprime: host port user password dbname (um por linha). Password pode ser vazio.
release_parse_database_url() {
  local url
  url="$(release_env_get DATABASE_URL "")"
  if [[ -z "$url" ]]; then
    echo "Erro: DATABASE_URL ausente em $RELEASE_ENV_FILE" >&2
    exit 1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Erro: python3 necessário para parsear DATABASE_URL." >&2
    exit 1
  fi
  DATABASE_URL="$url" python3 - <<'PY'
from urllib.parse import urlparse, unquote
import os, sys
u = urlparse(os.environ["DATABASE_URL"])
if u.scheme not in ("postgres", "postgresql"):
    print(f"Erro: DATABASE_URL não é postgres: {u.scheme!r}", file=sys.stderr)
    sys.exit(1)
host = u.hostname or "127.0.0.1"
port = u.port or 5432
user = unquote(u.username or "")
password = unquote(u.password or "")
dbname = unquote((u.path or "").lstrip("/").split("?")[0])
if not dbname:
    print("Erro: DATABASE_URL sem nome do banco", file=sys.stderr)
    sys.exit(1)
print(host)
print(port)
print(user)
print(password)
print(dbname)
PY
}

release_read_pointer() {
  local name="${1:?}"
  local path
  path="$(release_releases_dir)/${name}"
  if [[ -f "$path" ]]; then
    tr -d '[:space:]' <"$path"
  fi
}

release_write_pointer() {
  local name="${1:?}"
  local value="${2:?}"
  release_ensure_dirs
  printf '%s\n' "$value" >"$(release_releases_dir)/${name}"
}

release_backup_db() {
  local deploy_id="${1:?}"
  local dest_dir dump_path meta_path
  local host port user password dbname

  release_require_vars
  release_ensure_dirs

  dest_dir="$(release_backups_dir)/${deploy_id}"
  mkdir -p "$dest_dir"
  dump_path="${dest_dir}/db.dump"
  meta_path="${dest_dir}/meta.json"

  echo "== Release: backup Postgres -> ${dump_path} =="

  mapfile -t _db_parts < <(release_parse_database_url)
  host="${_db_parts[0]}"
  port="${_db_parts[1]}"
  user="${_db_parts[2]}"
  password="${_db_parts[3]}"
  dbname="${_db_parts[4]}"

  docker run --rm --network host \
    -e "PGPASSWORD=${password}" \
    -v "${dest_dir}:/backup" \
    "$RELEASE_POSTGRES_IMAGE" \
    pg_dump \
      -h "$host" \
      -p "$port" \
      -U "$user" \
      -d "$dbname" \
      -Fc \
      --no-owner \
      --no-acl \
      -f /backup/db.dump

  if [[ ! -s "$dump_path" ]]; then
    echo "Erro: dump vazio ou ausente em $dump_path" >&2
    exit 1
  fi

  if command -v python3 >/dev/null 2>&1; then
    DEPLOY_ID="$deploy_id" \
      BACKEND_IMAGE="$RELEASE_BACKEND_IMAGE" \
      FRONTEND_IMAGE="$RELEASE_FRONTEND_IMAGE" \
      DB_NAME="$dbname" \
      DUMP_PATH="$dump_path" \
      META_PATH="$meta_path" \
      ROOT="$RELEASE_ROOT" \
      python3 - <<'PY'
import json, os, time, subprocess
sha = "local"
try:
    sha = subprocess.check_output(
        ["git", "-C", os.environ["ROOT"], "rev-parse", "--short", "HEAD"],
        text=True,
    ).strip()
except Exception:
    pass
meta = {
    "deploy_id": os.environ["DEPLOY_ID"],
    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "git_sha": sha,
    "db_name": os.environ["DB_NAME"],
    "dump": "db.dump",
    "backend_image": f'{os.environ["BACKEND_IMAGE"]}:{os.environ["DEPLOY_ID"]}',
    "frontend_image": f'{os.environ["FRONTEND_IMAGE"]}:{os.environ["DEPLOY_ID"]}',
}
with open(os.environ["META_PATH"], "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)
    f.write("\n")
PY
  else
    printf '{"deploy_id":"%s","dump":"db.dump"}\n' "$deploy_id" >"$meta_path"
  fi

  echo "   Backup OK ($(du -h "$dump_path" | awk '{print $1}'))"
}

release_tag_as_current() {
  local deploy_id="${1:?}"
  release_require_vars
  echo "== Release: tag imagens ${deploy_id} -> :current =="
  docker tag "${RELEASE_BACKEND_IMAGE}:${deploy_id}" "${RELEASE_BACKEND_IMAGE}:current"
  docker tag "${RELEASE_FRONTEND_IMAGE}:${deploy_id}" "${RELEASE_FRONTEND_IMAGE}:current"
}

release_record_after_deploy() {
  local deploy_id="${1:?}"
  local prev
  release_ensure_dirs
  prev="$(release_read_pointer current || true)"
  if [[ -n "$prev" && "$prev" != "$deploy_id" ]]; then
    release_write_pointer previous "$prev"
  fi
  release_write_pointer current "$deploy_id"
  echo "   Ponteiros: current=${deploy_id} previous=$(release_read_pointer previous || echo '(nenhum)')"
}

release_prune() {
  local keep="${RELEASE_KEEP}"
  local backups_dir releases_dir
  local -a ids=()
  local current previous id

  release_require_vars
  backups_dir="$(release_backups_dir)"
  releases_dir="$(release_releases_dir)"
  current="$(release_read_pointer current || true)"
  previous="$(release_read_pointer previous || true)"

  if [[ ! -d "$backups_dir" ]]; then
    return 0
  fi

  mapfile -t ids < <(find "$backups_dir" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -r)
  if [[ "${#ids[@]}" -le "$keep" ]]; then
    echo "== Release: prune — ${#ids[@]} release(s), keep=$keep (nada a remover)"
    return 0
  fi

  echo "== Release: prune — mantendo $keep mais recentes (+ current/previous) =="
  local i=0
  for id in "${ids[@]}"; do
    i=$((i + 1))
    if [[ "$i" -le "$keep" ]]; then
      continue
    fi
    if [[ "$id" == "$current" || "$id" == "$previous" ]]; then
      continue
    fi
    echo "   Removendo backup $id"
    rm -rf "${backups_dir}/${id}"
    if docker image inspect "${RELEASE_BACKEND_IMAGE}:${id}" >/dev/null 2>&1; then
      docker image rm -f "${RELEASE_BACKEND_IMAGE}:${id}" >/dev/null 2>&1 || true
    fi
    if docker image inspect "${RELEASE_FRONTEND_IMAGE}:${id}" >/dev/null 2>&1; then
      docker image rm -f "${RELEASE_FRONTEND_IMAGE}:${id}" >/dev/null 2>&1 || true
    fi
  done
}

release_confirm_rollback() {
  local deploy_id="${1:?}"
  if [[ "${CONFIRM:-}" == "1" ]]; then
    return 0
  fi
  echo ""
  echo "ATENÇÃO: rollback SEMPRE restaura o banco (${deploy_id}/db.dump) e as imagens."
  echo "Isso sobrescreve dados gravados depois desse deploy."
  read -r -p "Confirma rollback para ${deploy_id}? digite 'sim': " answer
  if [[ "$answer" != "sim" ]]; then
    echo "Rollback cancelado."
    exit 1
  fi
}

release_restore_db() {
  local deploy_id="${1:?}"
  local dump_path
  local host port user password dbname

  release_require_vars
  dump_path="$(release_backups_dir)/${deploy_id}/db.dump"
  if [[ ! -s "$dump_path" ]]; then
    echo "Erro: dump não encontrado: $dump_path" >&2
    exit 1
  fi

  echo "== Release: restore Postgres a partir de ${dump_path} =="

  mapfile -t _db_parts < <(release_parse_database_url)
  host="${_db_parts[0]}"
  port="${_db_parts[1]}"
  user="${_db_parts[2]}"
  password="${_db_parts[3]}"
  dbname="${_db_parts[4]}"

  set +e
  docker run --rm --network host \
    -e "PGPASSWORD=${password}" \
    -v "$(release_backups_dir)/${deploy_id}:/backup:ro" \
    "$RELEASE_POSTGRES_IMAGE" \
    pg_restore \
      -h "$host" \
      -p "$port" \
      -U "$user" \
      -d "$dbname" \
      --clean \
      --if-exists \
      --no-owner \
      --no-acl \
      /backup/db.dump
  local rc=$?
  set -e
  # pg_restore usa exit 1 para warnings não-fatais.
  if [[ "$rc" -gt 1 ]]; then
    echo "Erro: pg_restore falhou (exit $rc)" >&2
    exit "$rc"
  fi

  echo "   Restore OK (exit ${rc})"
}

release_images_exist() {
  local deploy_id="${1:?}"
  docker image inspect "${RELEASE_BACKEND_IMAGE}:${deploy_id}" >/dev/null 2>&1 \
    && docker image inspect "${RELEASE_FRONTEND_IMAGE}:${deploy_id}" >/dev/null 2>&1
}

release_resolve_rollback_id() {
  local requested="${1:-}"
  local target
  if [[ -n "$requested" ]]; then
    target="$requested"
  else
    target="$(release_read_pointer previous || true)"
  fi
  if [[ -z "$target" ]]; then
    echo "Erro: nenhum release 'previous' registrado. Informe o DEPLOY_ID." >&2
    echo "Dumps disponíveis:" >&2
    ls -1 "$(release_backups_dir)" 2>/dev/null || true
    exit 1
  fi
  if [[ ! -s "$(release_backups_dir)/${target}/db.dump" ]]; then
    echo "Erro: dump ausente para $target" >&2
    exit 1
  fi
  if ! release_images_exist "$target"; then
    echo "Erro: imagens Docker ausentes para $target" >&2
    echo "  Esperado: ${RELEASE_BACKEND_IMAGE}:${target}" >&2
    echo "  Esperado: ${RELEASE_FRONTEND_IMAGE}:${target}" >&2
    exit 1
  fi
  echo "$target"
}
