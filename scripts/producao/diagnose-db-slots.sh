#!/usr/bin/env bash
# Diagnóstico rápido de slots Postgres (produção).
# Uso (na LAN, com DATABASE_URL no .env.production):
#   ./scripts/producao/diagnose-db-slots.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
set -a
source "$ROOT/.env.production"
set +a

python3 - <<'PY'
import os, re, json
from urllib.parse import urlparse, unquote
import psycopg2

url = os.environ["DATABASE_URL"]
u = urlparse(url)
conn = psycopg2.connect(
    host=u.hostname,
    port=u.port or 5432,
    dbname=u.path.lstrip("/"),
    user=u.username,
    password=unquote(u.password or ""),
    connect_timeout=8,
)
conn.autocommit = True
cur = conn.cursor()
cur.execute("SHOW max_connections")
max_c = int(cur.fetchone()[0])
cur.execute("SHOW superuser_reserved_connections")
reserved = int(cur.fetchone()[0])
cur.execute("SELECT count(*) FROM pg_stat_activity")
total = int(cur.fetchone()[0])
cur.execute(
    """
    SELECT coalesce(datname,'?'), count(*)
    FROM pg_stat_activity GROUP BY 1 ORDER BY 2 DESC
    """
)
by_db = [{"db": r[0], "count": int(r[1])} for r in cur.fetchall()]
payload = {
    "max_connections": max_c,
    "reserved": reserved,
    "total": total,
    "available_approx": max_c - reserved - total,
    "by_db": by_db,
}
print(json.dumps(payload, indent=2, ensure_ascii=False))
cur.close()
conn.close()
PY
