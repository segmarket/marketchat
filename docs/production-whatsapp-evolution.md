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

## Fuso horário (Brasília)

Containers usam `TZ=America/Sao_Paulo`. Verificar:

```bash
docker exec marketchat_backend_prd date
```
