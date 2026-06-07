# Deploy — produção (10.10.10.140)

Scripts espelham `scripts/staging/`: do notebook faz **rsync + SSH**; no servidor roda **docker compose** com `docker-compose.production.yml`.

## Configuração local (uma vez)

```bash
cp scripts/producao/env.deploy.example scripts/producao/env.deploy
chmod +x scripts/producao/*.sh
```

Edite `scripts/producao/env.deploy`:

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `PRODUCTION_SSH` | `seguser@10.10.10.140` | Usuário e host SSH |
| `PRODUCTION_PATH` | `marketchat` | Pasta no home do servidor |
| `PUSH_LOCAL_ENV` | `0` | `1` envia `.env.production` do notebook no rsync |
| `DEPLOY_SSH_PASSWORD` | (vazio) | Opcional; use **chave SSH** em vez de senha no arquivo |

**Não commite** `env.deploy` nem senhas no Git (arquivo já está no `.gitignore`).

### Autenticação SSH (recomendado)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/marketchat_prd
ssh-copy-id -i ~/.ssh/marketchat_prd.pub seguser@10.10.10.140
```

No `~/.ssh/config`:

```
Host marketchat-prd
  HostName 10.10.10.140
  User seguser
  IdentityFile ~/.ssh/marketchat_prd
```

Em `env.deploy`: `PRODUCTION_SSH=marketchat-prd`

### Autenticação por senha (alternativa)

```bash
sudo dnf install sshpass
```

Em `env.deploy` (local, não versionado):

```bash
DEPLOY_SSH_PASSWORD='sua_senha'
```

## Arquivo de ambiente no servidor

`.env.production` fica **só no servidor** (rsync não envia por padrão).

Primeira vez, no notebook:

```bash
PUSH_LOCAL_ENV=1 ./scripts/producao/bootstrap.sh
```

Ou crie/edite no servidor: `nano ~/marketchat/.env.production`

Variáveis importantes:

```bash
PRODUCTION_BACKEND_PORT=9001
PRODUCTION_FRONTEND_PORT=3000
```

## Onde rodar os comandos

Os scripts usam caminhos relativos à **raiz do repositório** (`marketchat/`).

```bash
cd ~/Documentos/marketchat          # raiz do projeto
./scripts/producao/bootstrap.sh
```

Se você já está em `scripts/producao/`:

```bash
cd ~/Documentos/marketchat/scripts/producao
./bootstrap.sh                      # sem o prefixo scripts/producao/
```

Atalhos na pasta `scripts/` (funcionam de qualquer lugar se você passar o caminho completo):

```bash
cd ~/Documentos/marketchat
./scripts/bootstrap-prd.sh
./scripts/deploy-prd.sh full
```

**Erro comum:** estar em `~/Documentos/marketchat/scripts` e rodar `./scripts/producao/bootstrap.sh` — esse caminho não existe dali (viraria `scripts/scripts/producao/...`).

## Comandos

| Comando | Ação |
|---------|------|
| `./scripts/producao/bootstrap.sh` | Primeiro deploy (build + up) |
| `./scripts/producao/deploy-full.sh` | Backend + frontend |
| `./scripts/producao/deploy-backend.sh` | Só API (migrations no entrypoint) |
| `./scripts/producao/deploy-frontend.sh` | Só painel (rebuild VITE_*) |
| `./scripts/producao/deploy-remote.sh sync` | Só rsync, sem Docker |
| `./scripts/bootstrap-prd.sh` | Mesmo que `producao/bootstrap.sh` |
| `./scripts/deploy-prd.sh full` | Mesmo que `deploy-remote.sh full` |

## Redis (cache / chat)

O Redis em `10.10.10.150` é usado para cache Django, dedup de mensagens WhatsApp e histórico do chatbot.

### `Authentication required` ou `AuthenticationError`

O `.env.production` no servidor está **sem senha** ou com senha errada em `REDIS_URL`.

1. Edite no servidor `~/marketchat/.env.production`:
   ```bash
   REDIS_URL=redis://default:SENHA@10.10.10.150:6379/7
   ```
   ou só senha (usuário default): `redis://:SENHA@10.10.10.150:6379/7`

   Se a senha tiver `@`, `#` ou `%`, use [URL encoding](https://www.urlencoder.org/) na senha.

2. Redeploy só backend:
   ```bash
   ./scripts/producao/deploy-backend.sh
   ```

3. Teste no container (deve imprimir `pong`):
   ```bash
   docker exec marketchat_backend_prd python -c "
   import os, django; django.setup()
   from django.core.cache import cache
   cache.set('ping','pong',10); print(cache.get('ping'))
   "
   ```

4. Código usa **RESP2** (`protocol: 2`) para compatibilidade com Redis 7+ autenticado.

Sintomas no log com Redis quebrado: `Falha no dedup de MESSAGE`, `chat_context: falha ao ler/gravar Redis`.

### `HELLO must be called with the client already authenticated`

Mesma causa — corrija `REDIS_URL` como acima.

## Asaas Pix (carrinho WhatsApp)

Erro `Esta cobrança não permite pagamentos via Pix` no `pixQrCode`:

- A **conta master** Asaas (`ASAAS_API_KEY` em produção) precisa ter **chave Pix cadastrada** para **receber cobranças** (não basta transferência/saque).
- Painel Asaas → **Conta → Pix → Minhas chaves** → cadastre e aguarde aprovação.
- Confirme `ASAAS_API_URL=https://api.asaas.com/v3` (produção, não sandbox).

Após cadastrar a chave Pix no Asaas, novas compras no WhatsApp devem retornar o copia-e-cola normalmente.

### Webhook Asaas “interrompido” ou pagamento não confirma no WhatsApp

No painel Asaas → Integrações → Webhooks:

1. **Ative os dois interruptores:**
   - *Este Webhook ficará ativo?* → **Sim**
   - *Fila de sincronização ativada?* → **Sim** (sem isso o status fica “interrompido”)

2. **URL correta** (note o `/asaas/` no final):
   ```text
   https://app.marketchat.com.br/api/billing/webhooks/asaas/
   ```
   Alternativa equivalente: `https://app.marketchat.com.br/api/webhooks/asaas/`

   A URL `.../api/billing/webhooks/` **sem** `asaas` retorna 404.

3. **Token de autenticação** = mesmo valor de `ASAAS_WEBHOOK_TOKEN` no `.env.production` do servidor. O Asaas envia no header **`asaas-access-token`** (não `X-Webhook-Token`).

4. **Eventos de Cobranças** (mínimo para Pix do carrinho WhatsApp):
   - `PAYMENT_RECEIVED`
   - `PAYMENT_CONFIRMED`
   - `PAYMENT_OVERDUE` (Pix expirado)
   - `PAYMENT_DELETED` (opcional)

   Não basta só `PAYMENT_CREATED` — o MarketChat confirma o carrinho em `PAYMENT_RECEIVED` / `PAYMENT_CONFIRMED`.

5. Redeploy backend após alterar token: `./scripts/producao/deploy-backend.sh`

6. Teste manual (substitua `SEU_TOKEN`):
   ```bash
   curl -sI -X POST https://app.marketchat.com.br/api/billing/webhooks/asaas/ \
     -H 'asaas-access-token: SEU_TOKEN' \
     -H 'Content-Type: application/json' \
     -d '{"event":"PAYMENT_RECEIVED","payment":{"id":"pay_test"}}'
   ```
   Esperado: HTTP **200** (corpo vazio).

## Infra esperada no servidor

- **Docker** + Compose
- **API** publicada em `127.0.0.1:9001` → Apache `ProxyPass /api` em `app.marketchat.com.br`
- **Front** em `127.0.0.1:3000` → Apache `ProxyPass /`
- Postgres `192.168.1.30`, Evolution `10.10.10.140:9080` (evoapicloud), Redis `10.10.10.150` (ver `.env.production`)
- WhatsApp/Evolution: `EVOLUTION_API_BASE_URL` + `EVOLUTION_GLOBAL_API_KEY` — ver [docs/production-whatsapp-evolution.md](../../docs/production-whatsapp-evolution.md)
- Fuso: `TZ=America/Sao_Paulo` no container backend; Gunicorn `timeout=120` para provision

## Avisos comuns no log do deploy

### `The "aact_prod_..." variable is not set`

O Docker Compose interpreta `$` no arquivo passado com `--env-file`. Chaves Asaas começam com `$aact_prod_...`.

**Correção aplicada nos scripts:** o Compose só recebe variáveis `VITE_*` e `PRODUCTION_*`; o `.env.production` completo entra no container via `env_file` (valor literal).

No arquivo, mantenha:

```bash
ASAAS_API_KEY=$aact_prod_...
```

(não use `source .env.production` no bash — o `$` quebra no shell também).

### `Erro: porta 9010 (API) já está em uso` no `deploy-full.sh`

Em **redeploy**, as portas 9010/3000 (ou as definidas em `PRODUCTION_*_PORT`) **devem** estar ocupadas pelos containers `marketchat_backend_prd` e `marketchat_frontend_prd`. Isso é esperado.

O `deploy-full.sh` usa `production_check_ports_available redeploy`: só falha se outro processo (não MarketChat) estiver na porta. O `bootstrap.sh` continua exigindo portas livres (primeiro deploy).

Se o erro persistir após atualizar os scripts, confira quem escuta a porta:

```bash
ss -tlnp | grep :9010
docker ps --format 'table {{.Names}}\t{{.Ports}}' | grep -E '9010|3000'
```

### `Bind for 0.0.0.0:9001 failed: port is already allocated`

Outro processo ou container já usa a porta da API (Apache, deploy antigo, etc.).

No servidor `10.10.10.140`:

```bash
ss -tlnp | grep :9001
docker ps --format 'table {{.Names}}\t{{.Ports}}' | grep 9001
```

Opções:

1. Parar o que ocupa a porta (ex.: container antigo `docker stop <nome>`).
2. Ou mudar em `.env.production`: `PRODUCTION_BACKEND_PORT=9002` e ajustar o Apache (`ProxyPass /api` → `:9002`).

Depois:

```bash
cd ~/Documentos/marketchat
./scripts/producao/deploy-full.sh
```

### Outros avisos (podem ignorar)

- `Pseudo-terminal will not be allocated` — SSH sem TTY; não impede o deploy.
- `debconf` / `TERM is not set` — build da imagem Python; normal.
- Avisos CSS do Vite (`Unexpected ")"`) — não impedem o build.
- `Found orphan containers ([evolution-go])` — outro compose no mesmo host; use `--remove-orphans` se quiser limpar.

## Smoke test

Após deploy, no servidor:

```bash
curl -sI http://127.0.0.1:9001/api/auth/me/
curl -sI http://127.0.0.1:3000/
```

Público:

```bash
curl -sI https://app.marketchat.com.br/api/auth/me/
```
