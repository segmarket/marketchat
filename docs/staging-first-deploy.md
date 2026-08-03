# Primeiro deploy em staging (192.168.1.23)

## Onde o build acontece?

Por padrão, **todos os scripts em `scripts/staging/`** (exceto `deploy-remote.sh sync`) fazem **rsync do notebook** e rodam `docker compose` no servidor **`192.168.1.23`** (`seguser@192.168.1.23`).

| Comando no notebook | O que acontece |
|---------------------|----------------|
| `./scripts/staging/deploy-full.sh` | rsync → SSH → build no servidor |
| `./scripts/staging/deploy-backend.sh` | idem (só API) |
| `./scripts/staging/deploy-frontend.sh` | idem (só painel) |
| `./scripts/staging/bootstrap.sh` | idem (primeiro deploy) |

| Exceção | Comportamento |
|---------|----------------|
| SSH no próprio servidor e rodar o script | build **local** no host (detecta IP ou `STAGING_ON_SERVER=1`) |
| `STAGING_FORCE_LOCAL=1 ./scripts/staging/deploy-full.sh` | build no notebook (debug) |

**Fluxo recomendado no dia a dia:** edite no notebook → `./scripts/staging/deploy-full.sh` (não precisa mais escolher `deploy-remote.sh`).

---

## O que já existe no servidor

| Serviço | Container | Porta no host |
|---------|-----------|---------------|
| PostgreSQL | `postgres-db` | 5432 |
| Evolution GO | `evolution_go` | 8080 |
| Portainer | `portainer` | **8000** (UI) |
| Apache | host | 80 / 443 |

MarketChat publica:

- **API** → host **8001** → container `8000` (evita conflito com Portainer)
- **Front** → host **3000**

Configure o Apache para `127.0.0.1:8001` na API (ver `docs/apache-staging.conf.example`).

---

## Opção A — Trabalhar direto no servidor (SSH)

```bash
ssh seguser@192.168.1.23
cd ~/marketchat   # após git clone
cp .env.staging.example .env.staging
nano .env.staging
chmod +x scripts/staging/*.sh
./scripts/staging/bootstrap.sh
```

---

## Opção B — Deploy do notebook (recomendado)

**Sem Git no servidor:** `rsync` envia os arquivos da sua máquina e o Docker builda no host `192.168.1.23`.

Configure chave SSH (uma vez):

```bash
ssh-copy-id seguser@192.168.1.23
```

Primeira vez:

```bash
chmod +x scripts/staging/*.sh
./scripts/staging/bootstrap.sh
```

Se faltar `.env.staging` no servidor, o script cria a partir do example e pede para você editar via SSH antes de rodar de novo.

Atualizações (dia a dia):

```bash
./scripts/staging/deploy-full.sh      # sync + backend + frontend no servidor
./scripts/staging/deploy-backend.sh   # só API
./scripts/staging/deploy-frontend.sh  # só painel
./scripts/staging/deploy-remote.sh sync  # só copia arquivos (sem docker)
```

`deploy-remote.sh full|backend|frontend|bootstrap` continua como atalho equivalente.

Variáveis:

```bash
export STAGING_SSH=seguser@192.168.1.23
export STAGING_PATH=marketchat
export PUSH_LOCAL_ENV=1   # opcional: envia seu .env.staging local
./scripts/staging/deploy-remote.sh full
```

O `.env.staging` **não** é sobrescrito no servidor por padrão (segredos ficam só no host).

---

## Passo a passo (primeira vez no servidor)

### 1. `.env.staging` no servidor (primeira vez)

```bash
cp .env.staging.example .env.staging
nano .env.staging
```

Preencha: `SECRET_KEY`, `EVOLUTION_GLOBAL_API_KEY`, `ASAAS_*`, `OPENAI_*`.

`STAGING_BACKEND_PORT=8001` já é o padrão no compose (Portainer usa 8000).

No servidor, `DATABASE_URL` pode usar `127.0.0.1` ou `192.168.1.23` para o Postgres do host.

### 2. Bootstrap (do notebook ou no servidor)

```bash
# Do notebook (rsync + deploy no servidor):
./scripts/staging/deploy-remote.sh bootstrap

# Ou direto no servidor, após rsync manual:
./scripts/staging/bootstrap.sh
```

Cria tabelas (`migrate`), static, sobe Gunicorn — tudo no **entrypoint** do container.

### 3. Apache

[`apache-staging.conf.example`](apache-staging.conf.example):

- app → `:3000`
- API → `:8001`

### 4. Validar no servidor

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/api/auth/me/
```

---

## Deploys seguintes (no servidor)

| Comando | Uso |
|---------|-----|
| `./scripts/staging/deploy-full.sh` | API + painel |
| `./scripts/staging/deploy-backend.sh` | Só Django |
| `./scripts/staging/deploy-frontend.sh` | Só React |

Do notebook: `./scripts/staging/deploy-remote.sh full`

---

## Problemas comuns

- **Porta 8000 em uso**: é o Portainer — use **8001** (já é o padrão no `docker-compose.yml`).
- **Build no notebook**: não sobe no staging; use SSH ou `deploy-remote.sh`.
- **Front com API errada**: altere `VITE_API_BASE_URL` no `.env.staging` e rode `deploy-frontend.sh` no servidor.

### DNS / Cloudflare — `staging-app` mostra outro sistema (ex.: Trackerwise)

O deploy no servidor (`192.168.1.23:3000`) pode estar correto, mas o **DNS público** de `staging-app.marketchat.com.br` pode apontar para **outro host**. Sintomas:

- Título da página ≠ MarketChat; `/register` dá 404 no React.
- Login chama `/api/auth/login/` (outro app), não `/api/auth/token/` do MarketChat.
- `staging.marketchat.com.br` abre a landing nova, mas `staging-app` não.

**Verificação (no notebook):**

```bash
# Deve listar o mesmo JS do container (ex.: index-DLb5zTG2.js), não outro bundle antigo
curl -s https://staging.marketchat.com.br/ | grep -o 'index-[^"]*\.js'
curl -s https://staging-app.marketchat.com.br/ | grep -o 'index-[^"]*\.js'
```

Os dois hosts devem retornar o **mesmo** hash de `index-*.js` após o deploy.

**Correção no Cloudflare:** registro `staging-app` (A ou CNAME) com o **mesmo destino** de `staging.marketchat.com.br` (IP do servidor MarketChat). No Apache, VirtualHost `ServerName staging-app.marketchat.com.br` → `127.0.0.1:3000` (ver `apache-staging.conf.example`). Purge cache do Cloudflare depois.

**API:** o front deve chamar `https://staging-api.marketchat.com.br` (não `staging-app/.../api`). Confira `VITE_API_BASE_URL` no `.env.staging` e refaça `deploy-frontend.sh`.
