#!/usr/bin/env bash
# MÁQUINA: host Docker do MarketChat (backend + front). NÃO o host Apache.
# Descoberta SOMENTE LEITURA: portas publicadas e em que interface, imagens em uso, rota /media
# no backend em execução, firewall e agendamentos que chamam manage.py. Não para, não reinicia,
# não altera nada. Grava em $OUT.
#
#   sudo OUT=/root/mc-docker-discovery BACKEND=marketchat_backend_prd FRONTEND=marketchat_frontend_prd ./descobrir-docker.sh
#   (staging: BACKEND=marketchat_backend_staging FRONTEND=marketchat_frontend_staging)
set -uo pipefail

OUT="${OUT:-/tmp/mc-docker-discovery-$(hostname -s)-$(date +%Y%m%dT%H%M%S)}"
BACKEND="${BACKEND:-marketchat_backend_prd}"
FRONTEND="${FRONTEND:-marketchat_frontend_prd}"
mkdir -p "$OUT" && chmod 700 "$OUT"

run() { # run <arquivo> <comando...>
  local f="$OUT/$1"; shift
  { echo "\$ $*"; "$@"; echo "[exit=$?]"; } >"$f" 2>&1
}

run 00-host.txt bash -c 'hostname -f; date -Is; id; ip -br addr 2>/dev/null || hostname -I'
run 01-listen.txt bash -c 'ss -tlnp | grep -E ":(80|443|3000|3001|8000|8001|9001|5432|6379)\b" || true'
run 02-docker-ps.txt docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
run 03-images.txt docker images --format '{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}'
for c in "$BACKEND" "$FRONTEND"; do
  run "04-inspect-$c.txt" docker inspect --format \
    'image={{.Config.Image}} imageid={{.Image}} started={{.State.StartedAt}} restart={{.HostConfig.RestartPolicy.Name}} log={{.HostConfig.LogConfig.Type}}{{"\n"}}ports={{json .HostConfig.PortBindings}}{{"\n"}}mounts={{range .Mounts}}{{.Type}}:{{.Source}}->{{.Destination}} {{end}}{{"\n"}}labels.project={{index .Config.Labels "com.docker.compose.project"}} workdir={{index .Config.Labels "com.docker.compose.project.working_dir"}} files={{index .Config.Labels "com.docker.compose.project.config_files"}}' "$c"
done

# Portas publicadas em 0.0.0.0/:: ficam acessíveis na LAN sem passar pelo Apache.
docker ps --format '{{.Names}}\t{{.Ports}}' | awk -F'\t' '{n = split($2, a, ", "); for (i = 1; i <= n; i++) if (a[i] ~ /^(0\.0\.0\.0|\[::\]|::):/) print $1 "\t" a[i]}' >"$OUT/05-portas-todas-interfaces.txt" 2>&1 || true

ROUTE_CHECK="from django.urls import get_resolver; print('ROTA /media PRESENTE' if any(str(p.pattern).startswith('media') for p in get_resolver().url_patterns) else 'ROTA /media AUSENTE')"
run 06-rota-media.txt docker exec "$BACKEND" python manage.py shell -c "$ROUTE_CHECK"
run 07-front-bundle.txt docker exec "$FRONTEND" sh -c 'grep -rlE "/attachment/|security-photo" /app/dist 2>/dev/null | head -5; echo "arquivos com endpoints novos: $(grep -rlE "/attachment/" /app/dist 2>/dev/null | wc -l)"'

run 10-firewall.txt bash -c 'firewall-cmd --state 2>/dev/null && firewall-cmd --list-all-zones 2>/dev/null | grep -vE "^\s*$"; echo "== DOCKER-USER"; iptables -S DOCKER-USER 2>/dev/null; nft list chain ip filter DOCKER-USER 2>/dev/null; true'
run 11-agendamentos.txt bash -c 'for u in root $(awk -F: "\$3>=1000 && \$3<65000 {print \$1}" /etc/passwd); do l="$(crontab -l -u "$u" 2>/dev/null | grep -vE "^\s*(#|$)")"; [[ -n "$l" ]] && printf "### crontab %s\n%s\n" "$u" "$l"; done; grep -rsnE "manage\.py|docker (compose )?exec" /etc/cron.d /etc/crontab 2>/dev/null; systemctl list-timers --all --no-pager 2>/dev/null | head -40; true'

{
  echo "Host Docker: $(hostname -f)"
  echo "IPs: $(ip -br addr 2>/dev/null | awk '$1!="lo"{print $1"="$3}' | tr '\n' ' ')"
  echo; echo "== Containers"; sed '1d;$d' "$OUT/02-docker-ps.txt"
  echo; echo "== Portas publicadas em todas as interfaces (acesso LAN direto)"; cat "$OUT/05-portas-todas-interfaces.txt"
  echo; echo "== Imagens dos containers"; grep -h '^image=' "$OUT"/04-inspect-*.txt
  echo; echo "== Rota /media no backend em execução"; grep -E 'ROTA|Error|exit' "$OUT/06-rota-media.txt"
  echo; echo "== Front"; tail -2 "$OUT/07-front-bundle.txt"
  echo; echo "== Agendamentos que chamam manage.py / docker exec"; grep -vE '^\$ ' "$OUT/11-agendamentos.txt" | grep -E 'manage\.py|docker' || echo "(nenhum encontrado em cron; ver timers em 11)"
} >"$OUT/99-resumo.txt"

cat "$OUT/99-resumo.txt"
echo; echo "Evidências em: $OUT"
