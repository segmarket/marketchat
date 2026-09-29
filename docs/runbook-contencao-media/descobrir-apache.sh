#!/usr/bin/env bash
# MÁQUINA: host do Apache/reverse proxy (NÃO o host Docker).
# Descoberta SOMENTE LEITURA do proxy que atende os hostnames do MarketChat. Rode com sudo no
# host candidato (o que recebe o tráfego do Cloudflare). Não altera configuração; grava
# evidências em $OUT (padrão: /tmp/mc-apache-discovery-*).
#
#   sudo OUT=/root/mc-discovery HOSTNAMES_RE='marketchat' ./descobrir-apache.sh
#
# Resultado principal: 30-vhosts.tsv (por vhost: endereço, arquivo:linha, nomes, destinos
# ProxyPass/RewriteRule[P], se já há regra /media) e 31-destinos.txt (alcance, a partir deste
# host, de cada destino no host Docker: GET /api/auth/me/ e GET /).
set -uo pipefail

OUT="${OUT:-/tmp/mc-apache-discovery-$(hostname -s)-$(date +%Y%m%dT%H%M%S)}"
HOSTNAMES_RE="${HOSTNAMES_RE:-marketchat}"
mkdir -p "$OUT" && chmod 700 "$OUT"
PATTERN='ServerName|ServerAlias|<VirtualHost|ProxyPass|ProxyPassMatch|ProxyPassReverse|RewriteRule|RewriteCond|Alias|<Location|<LocationMatch|<Proxy|Require|Include|DocumentRoot|CustomLog|ErrorLog|RemoteIP|/media|:9001|:8001|:8000|:3000|10\.10\.10\.140|192\.168\.1\.23|marketchat'

run() { # run <arquivo> <comando...>
  local f="$OUT/$1"; shift
  { echo "\$ $*"; "$@"; echo "[exit=$?]"; } >"$f" 2>&1
}

run 00-host.txt bash -c 'hostname -f; date -Is; cat /etc/os-release; id; ip -br addr 2>/dev/null || hostname -I'
run 01-listen.txt bash -c 'ss -tlnp | grep -E ":(80|443|8080|8443)\b" || true'
run 02-processos.txt bash -c 'ps -eo pid,user,cmd | grep -E "[h]ttpd|[a]pache2|[n]ginx|[c]addy|[t]raefik|[h]aproxy|[c]loudflared" || true'
run 03-systemd.txt bash -c 'for u in apache2 httpd nginx cloudflared caddy traefik haproxy; do printf "%-12s %s\n" "$u" "$(systemctl is-active "$u" 2>/dev/null)"; done'
run 04-containers.txt bash -c 'command -v docker >/dev/null && docker ps --format "{{.ID}} {{.Image}} {{.Names}} {{.Ports}}" || echo "docker ausente"'
# Peers em :80/:443 — se forem faixas do Cloudflare (https://www.cloudflare.com/ips/), este host é a origem.
{
  echo "\$ ss -tn state established '( sport = :443 or sport = :80 )'  (peers agrupados)"
  ss -tn state established '( sport = :443 or sport = :80 )' \
    | awk 'NR>1 {p=$4; sub(/:[0-9]+$/, "", p); print p}' | sort | uniq -c | sort -rn | head -30
} >"$OUT/06-conexoes.txt" 2>&1

# Processo mestre em execução: é ele que define qual config está ativa (-f/-d/-D).
MASTER="$(ps -C httpd,apache2 -o pid=,ppid=,euid=,args= 2>/dev/null | awk -v u="$(id -u "${MASTER_USER:-root}")" '$3==u{print; exit}')"
echo "${MASTER:-sem processo httpd/apache2 root}" >"$OUT/05-master.txt"
if [[ -n "$MASTER" ]]; then
  MPID="$(awk '{print $1}' <<<"$MASTER")"
  ps -o lstart= -p "$MPID" >>"$OUT/05-master.txt"
  tr '\0' ' ' <"/proc/$MPID/cmdline" >>"$OUT/05-master.txt"; echo >>"$OUT/05-master.txt"
fi

# Debian/Ubuntu: apache2ctl carrega /etc/apache2/envvars. RHEL/Fedora: o apachectl é
# um wrapper do systemd sem -S/-M/-D, então usa-se o binário com os flags do mestre.
FLAGS=()
if command -v apache2ctl >/dev/null; then
  CTL="$(command -v apache2ctl)"
elif [[ -n "$MASTER" ]]; then
  read -r -a ARGV <<<"$(tr '\0' ' ' <"/proc/$MPID/cmdline")"
  CTL="${ARGV[0]}"
  for ((i = 1; i < ${#ARGV[@]}; i++)); do
    case "${ARGV[i]}" in
      -f|-d|-C|-c) FLAGS+=("${ARGV[i]}" "${ARGV[i+1]}"); i=$((i + 1)) ;;
      -D) [[ "${ARGV[i+1]}" != FOREGROUND ]] && FLAGS+=(-D "${ARGV[i+1]}"); i=$((i + 1)) ;;
    esac
  done
else
  CTL="$(command -v httpd || true)"
fi
if [[ -z "$CTL" ]]; then
  echo "Apache não encontrado neste host. Veja 01..04 (proxy pode ser outro/containers)." | tee "$OUT/99-resumo.txt"
  exit 2
fi

run 10-apachectl-V.txt "$CTL" "${FLAGS[@]}" -V
run 11-apachectl-S.txt "$CTL" "${FLAGS[@]}" -S
run 12-apachectl-M.txt "$CTL" "${FLAGS[@]}" -M
run 13-dump-includes.txt "$CTL" "${FLAGS[@]}" -t -D DUMP_INCLUDES
run 14-dump-run-cfg.txt "$CTL" "${FLAGS[@]}" -t -D DUMP_RUN_CFG
run 15-configtest.txt "$CTL" "${FLAGS[@]}" -t

# Lista de arquivos efetivamente carregados (pela árvore de includes, não por palpite).
awk '/^[[:space:]]*\([0-9*]+\)/ {print $NF}' "$OUT/13-dump-includes.txt" | sort -u >"$OUT/20-arquivos-carregados.txt"

: >"$OUT/21-sha256.txt"; : >"$OUT/22-diretivas-relevantes.txt"
while read -r f; do
  [[ -f "$f" ]] || continue
  sha256sum "$f" >>"$OUT/21-sha256.txt"
  hits="$(grep -nE "$PATTERN" "$f" 2>/dev/null | grep -vE '^[0-9]+:[[:space:]]*#')"
  [[ -n "$hits" ]] && printf '### %s\n%s\n\n' "$f" "$hits" >>"$OUT/22-diretivas-relevantes.txt"
done <"$OUT/20-arquivos-carregados.txt"

xargs -r grep -lE 'marketchat' <"$OUT/20-arquivos-carregados.txt" 2>/dev/null >"$OUT/23-arquivos-marketchat.txt" || true

# Config em disco pode divergir da carregada se alguém editou sem reload.
{
  echo "== Últimos start/graceful registrados no ErrorLog"
  zgrep -hE 'AH00489|AH00493|AH00094|resuming normal operations|Graceful restart' \
    /var/log/apache2/error.log* /var/log/httpd/error_log* 2>/dev/null | tail -5
  if [[ -n "${MPID:-}" ]]; then
    echo "== Arquivos carregados modificados depois do start do mestre ($(ps -o lstart= -p "$MPID"))"
    while read -r f; do [[ "$f" -nt "/proc/$MPID" ]] && ls -l --time-style=long-iso "$f"; done <"$OUT/20-arquivos-carregados.txt"
  fi
} >"$OUT/16-config-vs-processo.txt" 2>&1
# Mapa por vhost do MarketChat, a partir do -S (arquivo:linha) e do bloco <VirtualHost> em disco.
if command -v python3 >/dev/null; then
  python3 - "$OUT" "$HOSTNAMES_RE" >"$OUT/30-vhosts.tsv" 2>"$OUT/30-vhosts.err" <<'PY'
import glob, os, re, sys
out, pat = sys.argv[1], re.compile(sys.argv[2], re.I)
vhosts, addr, cur = {}, "", None
for l in open(os.path.join(out, "11-apachectl-S.txt"), errors="replace").read().splitlines():
    m = re.match(r"^(\S+:\d+)\s+is a NameVirtualHost", l)
    if m:
        addr = m.group(1); continue
    m = re.match(r"^(\S+:\d+)\s+(\S+) \((.+):(\d+)\)$", l)
    if m:
        addr = m.group(1)
        cur = vhosts.setdefault((m.group(3), int(m.group(4))), {"addr": addr, "names": []})
        cur["names"].append(m.group(2)); continue
    m = re.match(r"^\s+(?:default server|port \d+ namevhost) (\S+) \((.+):(\d+)\)$", l)
    if m:
        cur = vhosts.setdefault((m.group(2), int(m.group(3))), {"addr": addr, "names": []})
        if m.group(1) not in cur["names"]:
            cur["names"].append(m.group(1))
        continue
    m = re.match(r"^\s+(?:wild )?alias (\S+)$", l)
    if m and cur is not None and m.group(1) not in cur["names"]:
        cur["names"].append(m.group(1))
KEEP = re.compile(r"^\s*(ProxyPass|ProxyPassMatch|RewriteRule|Include|IncludeOptional|Alias|AliasMatch|<Location|<LocationMatch|Require|SSLEngine|CustomLog|RemoteIPHeader)\b", re.I)
PROXY = re.compile(r"^\s*(ProxyPass|ProxyPassMatch|RewriteRule)\b", re.I)
print("\t".join(["endereco", "arquivo:linha", "nomes", "destinos_proxy", "regra_media", "diretivas"]))
for (f, n), v in sorted(vhosts.items()):
    if not any(pat.search(x) for x in v["names"]):
        continue
    try:
        src = open(f, errors="replace").read().splitlines()
    except OSError as e:
        print("\t".join([v["addr"], f"{f}:{n}", ",".join(v["names"]), "?", "?", f"ilegível: {e}"])); continue
    block = []
    for i in range(n - 1, len(src)):
        if not src[i].lstrip().startswith("#"):
            block.append((i + 1, src[i]))
        if re.match(r"^\s*</VirtualHost>", src[i], re.I):
            break
    proxied = "\n".join(s for _, s in block if PROXY.match(s))
    dests = sorted(set(re.findall(r"(?:https?|h2c?|wss?)://[^\s\"$]+", proxied)))
    text = [s for _, s in block]
    for s in list(text):
        m = re.match(r"^\s*Include(?:Optional)?\s+\"?([^\"\s]+)", s, re.I)
        if m:
            for inc in sorted(glob.glob(m.group(1))):
                try:
                    text += [x for x in open(inc, errors="replace").read().splitlines() if not x.lstrip().startswith("#")]
                except OSError:
                    pass
    joined = "\n".join(text)
    media = []
    if re.search(r"<Location(?:Match)?\s+\"?[^>]*media[^>]*>\s*\n(?:(?!</Location).*\n)*?\s*Require all denied", joined, re.I):
        media.append("bloqueio")
    if any("/media" in s and PROXY.match(s) for s in text):
        media.append("proxy")
    media = "+".join(media) or "nenhuma"
    dirs = [f"{i}:{s.strip()}" for i, s in block if KEEP.match(s)]
    print("\t".join([v["addr"], f"{f}:{n}", ",".join(v["names"]), " ".join(dests) or "-", media, " | ".join(dirs)]))
PY
  # Alcance de cada destino (host Docker) a partir deste host. GETs somente leitura.
  {
    echo "destino | resolve | GET /api/auth/me/ | GET /"
    tail -n +2 "$OUT/30-vhosts.tsv" | cut -f4 | tr ' ' '\n' | grep -oE '^[a-z0-9]+://[^/]+' | sort -u | while read -r base; do
      h="${base#*://}"; h="${h%:*}"
      printf '%s | %s | %s | %s\n' "$base" "$(getent hosts "$h" | awk '{print $1}' | head -1)" \
        "$(curl -s -o /dev/null -m 5 -w '%{http_code}' "$base/api/auth/me/")" \
        "$(curl -s -o /dev/null -m 5 -w '%{http_code}' "$base/")"
    done
  } >"$OUT/31-destinos.txt" 2>&1
else
  echo "python3 ausente: preencher o mapa manualmente a partir de 11 e 22." >"$OUT/30-vhosts.tsv"
fi

run 24-logrotate.txt bash -c 'cat /etc/logrotate.d/apache2 /etc/logrotate.d/httpd 2>/dev/null; grep -E "^(weekly|daily|monthly|rotate)" /etc/logrotate.conf'
run 25-logs.txt bash -c 'ls -la --time-style=long-iso /var/log/apache2 /var/log/httpd 2>/dev/null | head -200'
run 26-cloudflared.txt bash -c 'for f in /etc/cloudflared/config.yml /etc/cloudflared/config.yaml ~/.cloudflared/config.yml; do [[ -f $f ]] && { echo "### $f"; grep -vE "^\s*#" "$f"; }; done; true'

{
  echo "Host: $(hostname -f)  comando: $CTL ${FLAGS[*]}"
  echo "Mestre: ${MASTER:-(nenhum)}"
  grep -E 'Server version|HTTPD_ROOT|SERVER_CONFIG_FILE' "$OUT/10-apachectl-V.txt"
  echo "IPs: $(ip -br addr 2>/dev/null | awk '$1!="lo"{print $1"="$3}' | tr '\n' ' ')"
  echo; echo "== VirtualHosts (apachectl -S)"; sed -n '/^VirtualHost configuration:/,/^ServerRoot:/p' "$OUT/11-apachectl-S.txt" | sed '1d;$d'
  echo; echo "== Vhosts que casam com /$HOSTNAMES_RE/ (endereço | arquivo:linha | nomes | destinos | regra /media)"
  cut -f1-5 "$OUT/30-vhosts.tsv" | tail -n +2 | tr '\t' '|'
  echo; echo "== Alcance dos destinos (host Docker) a partir deste host"; cat "$OUT/31-destinos.txt" 2>/dev/null
  echo; echo "== Arquivos carregados que citam marketchat"; cat "$OUT/23-arquivos-marketchat.txt"
  echo; echo "== Já existe regra para /media?"; grep -n '/media' "$OUT/22-diretivas-relevantes.txt" || echo "(nenhuma)"
  echo; echo "== mod_remoteip / headers"; grep -E 'remoteip|headers' "$OUT/12-apachectl-M.txt" || echo "(não carregados)"
  echo; cat "$OUT/16-config-vs-processo.txt"
} >"$OUT/99-resumo.txt"

cat "$OUT/99-resumo.txt"
echo; echo "Evidências em: $OUT"
