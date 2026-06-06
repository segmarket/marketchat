# WhatsApp / Evolution em produção

## Erro 401 `not authorized` no provision

O backend envia header `apikey: <EVOLUTION_GLOBAL_API_KEY>` nas rotas administrativas (`GET /instance/all`, `POST /instance/create`). O Evolution GO (`evoapicloud/evolution-go`) valida contra a variável do **container Evolution**, não do Django.

**Correção:**

1. No **Portainer** → container `evolution-go` → **Environment** → copie o valor de:
   - `GLOBAL_API_KEY` (imagem evoapicloud), **ou**
   - `AUTHENTICATION_API_KEY` (imagem evolution-foundation)

2. No `.env.production` do MarketChat (mesmo valor, caractere por caractere):
   ```bash
   EVOLUTION_API_BASE_URL=http://10.10.10.140:9080
   EVOLUTION_GLOBAL_API_KEY=<mesmo valor do Portainer>
   PUBLIC_WEBHOOK_BASE_URL=https://app.marketchat.com.br
   ```

3. Redeploy **só backend** (não precisa rebuild do Evolution):
   ```bash
   ./scripts/producao/deploy-backend.sh
   ```

4. Validar no boot (log do container) ou manualmente:
   ```bash
   docker exec marketchat_backend_prd printenv EVOLUTION_GLOBAL_API_KEY | wc -c
   # deve ser > 1 (não vazio)

   docker exec marketchat_backend_prd python -c "
   import os, urllib.request
   key = os.environ['EVOLUTION_GLOBAL_API_KEY']
   base = os.environ['EVOLUTION_API_BASE_URL'].rstrip('/')
   req = urllib.request.Request(f'{base}/instance/all', headers={'apikey': key})
   urllib.request.urlopen(req, timeout=15)
   print('OK — chave aceita pelo Evolution')
   "
   ```

Se o teste acima der 401, a chave no Django **não** bate com a do Evolution — ajuste no Portainer ou no `.env.production` até coincidirem.

---

## Erro 502 ou Cloudflare “resposta inválida ou incompleta”

O endpoint `POST /api/integrations/whatsapp/provision/` chama o Evolution várias vezes (criar, conectar, QR). Cada chamada pode levar até **30s**. Gunicorn usa `timeout=120` (ver `docker/entrypoint.sh`).

```bash
./scripts/producao/deploy-backend.sh
```

### Apache (se ainda cortar)

```apache
ProxyTimeout 120
```

---

## Porta do Evolution

No Portainer a imagem `evoapicloud/evolution-go:latest` costuma publicar **9080:9080** (não 8090). Alinhe:

```bash
EVOLUTION_API_BASE_URL=http://10.10.10.140:9080
```

---

## Reconectar WhatsApp (502 / `client disconnected` / `no QR code available`)

Sintomas no log do backend:

```
Evolution HTTP 400 em GET /instance/status: {"error":"client disconnected"}
WhatsApp sessão desconectada no Evolution: mc-...
Evolution HTTP 400 em GET /instance/qr: {"error":"no QR code available..."}
Bad Gateway: /api/integrations/whatsapp/restart/
```

**O Evolution está UP** — isso é sessão WhatsApp caída, não falha de infra.

O painel chama `POST /api/integrations/whatsapp/restart/`, que:

1. Ignora `logout`/`disconnect` com `client disconnected` (sessão já caída — normal)
2. `POST /instance/connect` com `immediate: true` e **sem** `phone` (pairing code bloqueia o QR)
3. Responde **rápido** em `CONNECTING` (evita timeout do Apache) — o painel busca o QR via `GET /api/integrations/whatsapp/qrcode/` com polling

Logs esperados (não são erro fatal):

```
Evolution logout: sessão já desconectada (ok antes de reconectar)
Evolution QR ainda não pronto (tentativa N/M); aguardando 3s
```

Após deploy do backend com essa correção:

```bash
./scripts/producao/deploy-backend.sh
```

Confirme também:

```bash
# URL pública do webhook (Apache → Django)
grep PUBLIC_WEBHOOK_BASE_URL ~/marketchat/.env.production

# Evolution acessível do container backend
docker exec marketchat_backend_prd python -c "
import os, urllib.request
base = os.environ['EVOLUTION_API_BASE_URL'].rstrip('/')
key = os.environ['EVOLUTION_GLOBAL_API_KEY']
urllib.request.urlopen(urllib.request.Request(f'{base}/instance/all', headers={'apikey': key}), timeout=15)
print('Evolution OK')
"
```

Se o QR ainda não aparecer na primeira tentativa, aguarde ~15s e clique em **Reconectar** de novo.

---

## `401: logged out from another device`

Significa que o WhatsApp **invalidou a sessão** (desconectou em outro aparelho ou logout no celular). O Evolution mantém credenciais antigas — só `connect` não gera QR novo.

**O que o backend faz ao clicar em Reconectar:**

1. Detecta logout permanente (`401`, `logged out`, `another device`) ou sessão que já esteve conectada
2. **Apaga e recria** a instância no Evolution (`delete` + `create` + `connect` com novo token)
3. Marca status `CONNECTING` e o painel busca o QR via polling (`GET /qrcode/`)

**Importante:** enquanto o QR não for escaneado, o polling de status **não** reverte para `CLOSE` (Evolution responde `client disconnected` até o QR existir — isso é esperado).

Deploy:

```bash
./scripts/producao/deploy-backend.sh
```

Depois: **Reconectar** → aguardar o QR (ou **Atualizar QR**) → escanear no WhatsApp.

---

## Fuso horário (Brasília)

Containers usam `TZ=America/Sao_Paulo`. Verificar:

```bash
docker exec marketchat_backend_prd date
```
