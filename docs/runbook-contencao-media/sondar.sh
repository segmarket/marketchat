#!/usr/bin/env bash
# Sondas por hostname SEM dados de clientes (caminhos inexistentes e ids inexistentes).
#
#   VIA=cf      pelo Cloudflare (DNS público).
#   VIA=apache  direto no host Apache identificado: curl --resolve mantém Host e SNI = hostname.
#   VIA=docker  LAN direto na porta publicada do backend no host Docker (sem Apache/Cloudflare).
#
# Exemplos:
#   HOSTS="app.marketchat.com.br api.marketchat.com.br" VIA=cf ./sondar.sh
#   HOSTS="app.marketchat.com.br" VIA=apache APACHE_IP=203.0.113.10 SCHEMES="https http" ./sondar.sh
#   HOSTS="app.marketchat.com.br 10.10.10.140" VIA=docker DOCKER_URL=http://10.10.10.140:9001 ./sondar.sh
#
# Variáveis:
#   HOSTS         obrigatório; hostnames (em VIA=docker, valores do cabeçalho Host; inclua o IP para testar Host=IP).
#   SCHEMES       VIA=cf/apache: "https" (padrão) ou "https http".
#   APACHE_IP     VIA=apache: IP em que o Apache escuta o hostname.
#   APACHE_HTTPS_PORT / APACHE_HTTP_PORT  VIA=apache: portas do vhost (padrão 443 / 80).
#   CACERT        VIA=apache: CA da origem (ex.: Cloudflare Origin CA). Sem ela, usa -k (SNI/Host continuam o hostname).
#   DOCKER_URL    VIA=docker: ex. http://10.10.10.140:9001
#   EXPECT_MEDIA  status de /media/<probe>. Padrão: 403 (cf/apache) e 404 (docker).
#   EXPECT_NEW    status do endpoint novo de anexo (anônimo e token inválido). Padrão 401;
#                 antes da troca de containers use 404 (rota ainda não existe); "-" pula.
#   SKIP_SPA=1    não testa "/" em nenhum host (automático em VIA=docker).
#   API_HOSTS     hosts (dentre HOSTS) que só servem API: "/" não é testado neles.
#   SPA_HOSTS     hosts (dentre HOSTS) que só servem SPA/landing: testa "/" e /media, pula /api e anexo.
#   CANARY_PATH   opcional: caminho (relativo a /media/) de um arquivo canário sintético que EXISTE
#                 no volume (criado pelo runbook, sem registro no banco). Distingue "rota fechada"
#                 de "arquivo inexistente".
#   EXPECT_CANARY status esperado do canário (padrão = EXPECT_MEDIA). Imagem antiga via docker: 200.
#   PROBE_ID      sufixo do caminho de probe (padrão: timestamp; troque a cada fase, o Cloudflare guarda 404 por 3 min).
set -uo pipefail

: "${HOSTS:?defina HOSTS}"
VIA="${VIA:-cf}"
SCHEMES="${SCHEMES:-https}"
EXPECT_NEW="${EXPECT_NEW:-401}"
PROBE_ID="${PROBE_ID:-$(date +%Y%m%d%H%M%S)}"
case "$VIA" in
  cf|apache) EXPECT_MEDIA="${EXPECT_MEDIA:-403}"; SKIP_SPA="${SKIP_SPA:-0}" ;;
  docker) : "${DOCKER_URL:?defina DOCKER_URL}"; EXPECT_MEDIA="${EXPECT_MEDIA:-404}"; SKIP_SPA=1; SCHEMES=docker ;;
  *) echo "VIA deve ser cf, apache ou docker" >&2; exit 2 ;;
esac
[[ "$VIA" == apache ]] && : "${APACHE_IP:?defina APACHE_IP}"

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
fails=0
PROBE="/media/qa-probe-${PROBE_ID}.jpg"
NEW="/api/chatbot/messages/2147483647/attachment/"

# req <base> <host> <path> [auth]  -> STATUS, HDRS, BODY
req() {
  local base="$1" host="$2" path="$3" auth="${4:-}"
  HDRS="$tmp/h"; BODY="$tmp/b"
  local args=(curl -sS --path-as-is --max-time 15 -D "$HDRS" -o "$BODY" -w '%{http_code}')
  case "$VIA" in
    apache)
      local port="${APACHE_HTTPS_PORT:-443}"; [[ "$base" == http://* ]] && port="${APACHE_HTTP_PORT:-80}"
      args+=(--resolve "${host}:${port}:${APACHE_IP}")
      if [[ -n "${CACERT:-}" ]]; then args+=(--cacert "$CACERT"); else args+=(-k); fi ;;
    docker) args+=(-H "Host: ${host}") ;;
  esac
  [[ -n "$auth" ]] && args+=(-H "Authorization: $auth")
  STATUS="$("${args[@]}" "${base}${path}" 2>"$tmp/e")" || STATUS="ERR($(tr -d '\n' <"$tmp/e" | cut -c1-60))"
}
hdr() { grep -i "^$1:" "$HDRS" 2>/dev/null | tail -1 | cut -d: -f2- | tr -d '\r' | sed 's/^ *//'; }
info() { local s cf x; s="$(hdr server)"; cf="$(hdr cf-cache-status)"; x="$(hdr x-frame-options)"
  echo "${s:+server=$s}${cf:+ cf=$cf}${x:+ xfo=$x}"; }
line() { printf '%-4s  %-24s %-6s %-44s %-8s %s\n' "$1" "$2" "$3" "$4" "$5" "$6"; }
expect() { # expect <host> <scheme> <descr> <esperado>
  if [[ "$STATUS" == "$4" ]]; then line PASS "$1" "$2" "$3" "$STATUS" "$(info)"
  else line FAIL "$1" "$2" "$3" "$STATUS" "esperado=$4 $(info)"; fails=$((fails + 1)); fi
}
not200() {
  if [[ "$STATUS" != 200 ]]; then line PASS "$1" "$2" "$3" "$STATUS" "$(info)"
  else line FAIL "$1" "$2" "$3" "$STATUS" "entregou 200 $(info)"; fails=$((fails + 1)); fi
}

echo "== VIA=$VIA ${APACHE_IP:+apache=$APACHE_IP }${DOCKER_URL:+docker=$DOCKER_URL }expect_media=$EXPECT_MEDIA expect_new=$EXPECT_NEW probe=$PROBE"
for h in $HOSTS; do
  for s in $SCHEMES; do
    base="$s://$h"
    case "$VIA:$s" in
      docker:*) base="$DOCKER_URL" ;;
      apache:https) [[ "${APACHE_HTTPS_PORT:-443}" != 443 ]] && base+=":$APACHE_HTTPS_PORT" ;;
      apache:http) [[ "${APACHE_HTTP_PORT:-80}" != 80 ]] && base+=":$APACHE_HTTP_PORT" ;;
    esac
    if [[ "$SKIP_SPA" != 1 && " ${API_HOSTS:-} " != *" $h "* ]]; then req "$base" "$h" "/"; expect "$h" "$s" "GET /" 200; fi
    spa_only=0; [[ " ${SPA_HOSTS:-} " == *" $h "* ]] && spa_only=1
    if [[ "$spa_only" == 0 ]]; then req "$base" "$h" "/api/auth/me/"; expect "$h" "$s" "GET /api/auth/me/ anônimo" 401; fi
    req "$base" "$h" "$PROBE"; expect "$h" "$s" "GET /media/<probe inexistente>" "$EXPECT_MEDIA"
    if [[ -n "${CANARY_PATH:-}" ]]; then
      req "$base" "$h" "/media/${CANARY_PATH#/}"; expect "$h" "$s" "GET /media/<canário existente>" "${EXPECT_CANARY:-$EXPECT_MEDIA}"
    fi
    for v in "/%6Dedia/qa-probe-${PROBE_ID}.jpg" "//media/qa-probe-${PROBE_ID}.jpg"; do
      req "$base" "$h" "$v"; not200 "$h" "$s" "variante ${v%%qa-probe*}…"
    done
    if [[ "$EXPECT_NEW" != "-" && "$spa_only" == 0 ]]; then
      req "$base" "$h" "$NEW"; expect "$h" "$s" "anexo (id inexistente) anônimo" "$EXPECT_NEW"
      req "$base" "$h" "$NEW" "Bearer token-invalido"; expect "$h" "$s" "anexo com token inválido" "$EXPECT_NEW"
      if [[ "$EXPECT_NEW" == 401 && "$STATUS" == 401 ]]; then
        if grep -q token_not_valid "$BODY"; then line PASS "$h" "$s" "  Authorization chegou ao Django" "" "token_not_valid"
        else line FAIL "$h" "$s" "  Authorization chegou ao Django" "" "sem token_not_valid (proxy removeu o cabeçalho?)"; fails=$((fails + 1)); fi
      fi
    fi
  done
done
echo "== resultado: $fails falha(s)"
exit $(( fails > 0 ))
