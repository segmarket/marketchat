#!/usr/bin/env bash
# SOMENTE STAGING: verifica a entrega de mídia por HTTP usando os objetos sintéticos de
# qa_media_seed.py (que não roda em produção). Em produção use qa_media_inprocess.py + sondar.sh.
#
# Uso:
#   BASE_URL=https://app.marketchat.com.br QA_JSON_FILE=qa.json ./verificar-midia.sh
#
# Variáveis:
#   BASE_URL       obrigatório; esquema+host público (sem barra final).
#   QA_JSON_FILE   obrigatório; arquivo com o JSON impresso pelo seed (sem o prefixo QA_JSON=).
#   RESOLVE_IP     opcional; força o IP de origem (curl --resolve), ignorando o Cloudflare.
#   INSECURE=1     opcional; aceita certificado de origem (só com RESOLVE_IP).
#   EXPECT_MEDIA   status esperado para /media/<arquivo QA>. Padrão 403 (Apache bloqueando).
#   CHECKS         all (padrão) | media (só /media, útil antes do deploy) | new (só endpoints novos).
#   SKIP_SPA=1     não testa "/" (hosts só de API, ex.: staging-api).
set -uo pipefail

: "${BASE_URL:?defina BASE_URL}"
: "${QA_JSON_FILE:?defina QA_JSON_FILE}"
EXPECT_MEDIA="${EXPECT_MEDIA:-403}"
CHECKS="${CHECKS:-all}"
SKIP_SPA="${SKIP_SPA:-0}"

host="$(python3 -c 'import sys,urllib.parse as u;p=u.urlsplit(sys.argv[1]);print(p.hostname)' "$BASE_URL")"
port="$(python3 -c 'import sys,urllib.parse as u;p=u.urlsplit(sys.argv[1]);print(p.port or (443 if p.scheme=="https" else 80))' "$BASE_URL")"
CURL=(curl -sS --path-as-is --max-time 20)
if [[ -n "${RESOLVE_IP:-}" ]]; then
  CURL+=(--resolve "${host}:${port}:${RESOLVE_IP}")
  [[ "${INSECURE:-0}" == 1 ]] && CURL+=(-k)
fi

q() { python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$QA_JSON_FILE" "$1"; }
TOKEN_A="$(q token_a)"; TOKEN_B="$(q token_b)"
MSG_OK="$(q msg_ok)"; MSG_EMPTY="$(q msg_empty)"; MSG_MISSING="$(q msg_missing)"; MSG_NONE="$(q msg_nonexistent)"
CART_OK="$(q cart_ok)"; SESSION_ID="$(q session_id)"
CHAT_PATH="$(q chat_path)"; CART_PATH="$(q cart_path)"
CHAT_SHA="$(q chat_sha256)"; CART_SHA="$(q cart_sha256)"

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
fails=0

# fetch <nome> <path> [token] -> define STATUS, HDRS (arquivo), BODY (arquivo)
fetch() {
  local name="$1" path="$2" token="${3:-}"
  HDRS="$tmp/$name.h"; BODY="$tmp/$name.b"
  local args=("${CURL[@]}" -D "$HDRS" -o "$BODY" -w '%{http_code}')
  [[ -n "$token" ]] && args+=(-H "Authorization: Bearer $token")
  STATUS="$("${args[@]}" "${BASE_URL}${path}" 2>"$tmp/$name.err")" || STATUS="ERR"
}
hdr() { grep -i "^$1:" "$HDRS" | tail -1 | cut -d: -f2- | tr -d '\r' | sed 's/^ *//'; }
sha() { sha256sum "$BODY" | cut -d' ' -f1; }
ok()   { printf 'PASS  %-58s %s\n' "$1" "$2"; }
bad()  { printf 'FAIL  %-58s %s\n' "$1" "$2"; fails=$((fails + 1)); }
expect() { # expect <descr> <status esperado>
  local cf; cf="$(hdr cf-cache-status)"
  if [[ "$STATUS" == "$2" ]]; then ok "$1" "status=$STATUS${cf:+ cf=$cf}"; else bad "$1" "status=$STATUS esperado=$2${cf:+ cf=$cf}"; fi
}

echo "== $BASE_URL ${RESOLVE_IP:+(origem $RESOLVE_IP)} checks=$CHECKS expect_media=$EXPECT_MEDIA"

if [[ "$CHECKS" != media ]]; then
  if [[ "$SKIP_SPA" != 1 ]]; then fetch spa "/"; expect "GET / (SPA)" 200; fi
  fetch me "/api/auth/me/"; expect "GET /api/auth/me/ anônimo" 401

  A="/api/chatbot/messages/$MSG_OK/attachment/"
  fetch anon "$A"; expect "anexo chat anônimo" 401
  fetch qtok "$A?token=$TOKEN_A"; expect "anexo chat com token na query" 401
  fetch badtok "$A" "token-invalido"; expect "anexo chat com token inválido" 401
  if [[ "$STATUS" == 401 ]]; then
    grep -q token_not_valid "$BODY" && ok "  Authorization chegou ao Django" "token_not_valid" \
      || bad "  Authorization chegou ao Django" "sem token_not_valid (proxy removeu o cabeçalho?)"
  fi
  fetch own "$A" "$TOKEN_A"; expect "anexo chat dono (tenant A)" 200
  if [[ "$STATUS" == 200 ]]; then
    [[ "$(sha)" == "$CHAT_SHA" ]] && ok "  sha256 do anexo sintético" "confere" || bad "  sha256 do anexo sintético" "$(sha)"
    [[ "$(hdr content-type)" == image/jpeg* ]] && ok "  Content-Type" "$(hdr content-type)" || bad "  Content-Type" "$(hdr content-type)"
    cc="$(hdr cache-control)"
    [[ "$cc" == *private* && "$cc" == *no-store* ]] && ok "  Cache-Control" "$cc" || bad "  Cache-Control" "$cc"
    [[ "$(hdr x-content-type-options)" == nosniff ]] && ok "  nosniff" "" || bad "  nosniff" "$(hdr x-content-type-options)"
    cf="$(hdr cf-cache-status)"
    [[ "$cf" != HIT ]] && ok "  não servido do cache do Cloudflare" "${cf:-sem cf}" || bad "  servido do cache do Cloudflare" "$cf"
  fi
  fetch other "$A" "$TOKEN_B"; expect "anexo chat outro tenant (B)" 404
  fetch empty "/api/chatbot/messages/$MSG_EMPTY/attachment/" "$TOKEN_A"; expect "mensagem sem anexo" 404
  fetch miss "/api/chatbot/messages/$MSG_MISSING/attachment/" "$TOKEN_A"; expect "anexo ausente no storage" 404
  fetch none "/api/chatbot/messages/$MSG_NONE/attachment/" "$TOKEN_A"; expect "id inexistente" 404

  P="/api/sales/carts/$CART_OK/security-photo/"
  fetch canon "$P"; expect "foto carrinho anônimo" 401
  fetch cown "$P" "$TOKEN_A"; expect "foto carrinho dono (tenant A)" 200
  if [[ "$STATUS" == 200 ]]; then
    [[ "$(sha)" == "$CART_SHA" ]] && ok "  sha256 da foto sintética" "confere" || bad "  sha256 da foto sintética" "$(sha)"
  fi
  fetch cother "$P" "$TOKEN_B"; expect "foto carrinho outro tenant (B)" 404

  fetch conv "/api/chatbot/logs/conversation/?session_id=$SESSION_ID" "$TOKEN_A"; expect "conversa QA (inbox)" 200
  if [[ "$STATUS" == 200 ]]; then
    url="$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]));print(next((m.get("attachment_url") or "" for m in d["messages"] if m["id"]==int(sys.argv[2])),""))' "$BODY" "$MSG_OK")"
    [[ "$url" == */api/chatbot/messages/$MSG_OK/attachment/ && "$url" != */media/* ]] && ok "  attachment_url" "$url" || bad "  attachment_url" "$url"
  fi
  fetch cart "/api/sales/carts/$CART_OK/" "$TOKEN_A"; expect "detalhe carrinho QA" 200
  if [[ "$STATUS" == 200 ]]; then
    url="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("security_photo_url") or "")' "$BODY")"
    [[ "$url" == */api/sales/carts/$CART_OK/security-photo/ ]] && ok "  security_photo_url" "$url" || bad "  security_photo_url" "$url"
  fi
fi

if [[ "$CHECKS" != new ]]; then
  fetch m1 "/media/$CHAT_PATH"; expect "/media/<anexo QA> anônimo" "$EXPECT_MEDIA"
  if [[ "$EXPECT_MEDIA" == 200 && "$STATUS" == 200 ]]; then
    [[ "$(sha)" == "$CHAT_SHA" ]] && ok "  exposição confirmada com arquivo sintético" "cf=$(hdr cf-cache-status)" || bad "  corpo difere do sintético" ""
  fi
  fetch m2 "/media/$CHAT_PATH" "$TOKEN_A"; expect "/media/<anexo QA> com JWT" "$EXPECT_MEDIA"
  fetch m3 "/media/$CART_PATH"; expect "/media/<foto QA>" "$EXPECT_MEDIA"
  if [[ "$EXPECT_MEDIA" != 200 ]]; then
    for v in "/%6Dedia/$CHAT_PATH" "//media/$CHAT_PATH" "/api/../media/$CHAT_PATH"; do
      fetch var "$v"
      if [[ "$STATUS" != 200 ]] || [[ "$(sha)" != "$CHAT_SHA" ]]; then ok "variante $v" "status=$STATUS"; else bad "variante $v" "status=200 entregou o arquivo"; fi
    done
  fi
fi

echo "== resultado: $fails falha(s)"
exit $(( fails > 0 ))
