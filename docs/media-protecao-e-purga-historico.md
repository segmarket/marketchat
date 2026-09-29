# Proteção de mídia de clientes e purga do histórico Git

Status: **plano para revisão — nenhuma reescrita de histórico foi executada.**
Levantamento feito em 2026-09-29 sobre `main` (base `cdf496e`, remoto `github.com/segmarket/marketchat`).

## 1. O que mudou na entrega de arquivos

| Antes | Depois |
|---|---|
| `GET /media/<path>` via `django.views.static.serve`, sem autenticação, qualquer caminho sob `MEDIA_ROOT` | Rota removida (responde 404) |
| `ChatMessageLog.attachment` exposto como `/media/chat_logs/...` em `attachment_url` | `GET /api/chatbot/messages/<id>/attachment/` (JWT + tenant do usuário = tenant do log) |
| `Cart.product_photo` já usava `GET /api/sales/carts/<id>/security-photo/` | Mesmo endpoint, agora com o helper comum (arquivo ausente → 404 em vez de 500) |

Regras do helper `apps/core/media.py::protected_file_response`:

- a view busca o objeto por `pk` **filtrando por `tenant_id` do usuário autenticado**; o caminho do arquivo vem do campo no banco, nunca da requisição;
- objeto de outro tenant, objeto sem arquivo, arquivo ausente no storage ou caminho fora de `MEDIA_ROOT` → 404 (não revela existência);
- anônimo → 401;
- `Cache-Control: private, no-store`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'none'; sandbox`;
- só `image/jpeg|png|webp|gif` saem `inline`; qualquer outro tipo sai como `application/octet-stream` + `attachment`.

### Impacto no front

- `attachment_url` continua no payload, mas agora aponta para `/api/chatbot/messages/<id>/attachment/`. Ele não funciona em `<img src>` porque exige o header `Authorization`.
- `InboxChatPane` baixa o anexo com `fetchChatMessageAttachment(msg.id)` (axios, `responseType: "blob"`) e exibe um `blob:` URL, como o `OrderDetailsModal` já fazia com a foto do carrinho. O lightbox e o botão de download funcionam sobre o `blob:` URL.
- `resolveMediaUrl` foi removido de `services/api.ts` (não há mais URLs `/media/`).
- O proxy `/media` do dev server do Vite (`vite.config.ts`) foi removido.

### Django admin

- `CartAdmin` não usa mais o widget padrão de `ImageField`, que linkava `MEDIA_URL`. A foto aparece como o campo somente leitura "Foto de segurança", com link para `/admin/sales/cart/<id>/security-photo/`.
- Essa rota passa por `admin_site.admin_view`: exige sessão de staff ativa e `has_view_permission`. Anônimo e usuário de tenant (mesmo com JWT) são redirecionados ao login; staff sem permissão recebe 404.
- Consequência: o upload/troca da foto pelo admin deixou de existir. A remoção continua pelos fluxos de LGPD e `cleanup_old_photos`.
- `ChatMessageLog` não está registrado no admin.

### Proxy reverso (Apache)

- Os vhosts de API em `docs/staging-marketchat.apache.conf` e `docs/apache-staging.conf.example` ganharam `<Location "/media"> Require all denied </Location>` como defesa em profundidade.
- **A config Apache real de produção não está versionada.** Ela precisa receber o mesmo bloco (ver seção 4).

## 1.1 Verificação pelo proxy (Apache local, 2026-09-29)

Montagem: `httpd` 2.4 local com os vhosts versionados, adaptados só em IP/porta e sem TLS (o `X-Forwarded-Proto: https` do vhost é enviado igual). Atrás dele, gunicorn com os ajustes de proxy de `production.py` (`SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_HOST`, `TRUST_X_FORWARDED_FOR`, WhiteNoise, `DEBUG=False`), SQLite e 2 tenants. Foram testados o vhost do commit base e o novo, cada um nos hosts `staging-api` (`ProxyPass /` → Django) e `app` (formato de produção: `/api` → Django, `/` → SPA).

| Requisição | Resultado nos 4 cenários |
|---|---|
| anexo/foto, anônimo | 401 |
| anexo/foto, JWT do tenant dono | 200, `image/jpeg`, `Cache-Control: private, no-store` |
| anexo/foto, JWT de outro tenant | 404 |
| JWT inválido, ou token em query string | 401 |
| outro tenant + `X-Forwarded-For` forjado | 404 |
| `X-Forwarded-Host` forjado (dono ou não) | 400 (`DisallowedHost`), sem arquivo |
| `/media/<caminho real>`, host `staging-api` | 404 do Django (vhost base) / 403 do Apache (vhost novo) |
| `/media/<caminho real>`, host `app` | 200 com o HTML da SPA, sem bytes da foto |
| variações (`/%6Dedia`, `//media//`, `/static/../media`, traversal via `/api/...`, `/media%2F...`, `/MEDIA`) | nenhum retorno com bytes da foto |
| `attachment_url` gerado atrás do proxy | `https://app.marketchat.com.br/api/chatbot/messages/1/attachment/` |

## 1.2 Exposição atual nos ambientes publicados

Sonda somente leitura em 2026-09-29, apenas com arquivo inexistente:

- `https://app.marketchat.com.br/media/__probe_inexistente__.jpg` responde com a página 404 **do Django** (mesmos headers de `/api/...`: `X-Frame-Options: DENY`, COOP, `Vary: origin,Cookie`), enquanto `/` responde com a SPA. Ou seja, **o Apache real de produção encaminha `/media` ao Django**, diferente do que `scripts/producao` descreve.
- `staging-api.marketchat.com.br/media/...` também chega ao Django.
- Com o código hoje implantado (rota `serve` pública), qualquer foto em `MEDIA_ROOT` de produção/staging é acessível sem login por caminho. Os nomes são previsíveis (`security_photos/AAAA/MM/DD/cart_<id>.jpg`, `chat_logs/AAAA/MM/cart_<id>.jpg`). Nenhum caminho real foi testado.
- Há **Cloudflare** na frente (`server: cloudflare`). Por padrão ele faz cache de `.jpg`, então fotos já requisitadas podem estar no cache de borda. Os endpoints novos não terminam em extensão de imagem e respondem `private, no-store`.

## 2. Imagens já publicadas que exigem avaliação

`media/` e `test_media/` ficaram versionados até o commit `d50fa6e9` (*Stop versioning uploaded media*), que só os retira do índice. **Todo o conteúdo continua acessível no histórico** e foi enviado para `origin/main`.

### 2.1 `media/`: fotos reais (prioridade alta)

São 20 caminhos, mas apenas **6 imagens distintas** (JPEG real, 41–167 KB). Todas foram publicadas no GitHub. As imagens não foram abertas neste levantamento; a avaliação do conteúdo deve ser feita por quem tem responsabilidade sobre os dados (encarregado LGPD / time).

| Blob (SHA-1 completo) | Tamanho | Caminhos no histórico | 1º commit |
|---|---|---|---|
| `f0cabfcd901f4d4e3a723114530317343168e60f` | 54 327 B | `media/carts/2026/05/cart_1.jpg`, `cart_1_AX0Z4Ko.jpg`, `cart_1_uBfv3Gf.jpg`, `cart_4.jpg`; `media/chat_logs/2026/05/cart_5.jpg`*; `media/security_photos/2026/05/19/cart_5.jpg` | `ec7d3cca` (2026-05-17) |
| `7c5131c25ce8938a568e9d088dd49974f33c6eda` | 147 703 B | `media/chat_logs/2026/05/cart_7.jpg`*, `cart_10.jpg`*; `media/security_photos/2026/05/19/cart_7.jpg`, `cart_10.jpg` | `af5f7195` (2026-05-19) |
| `a8e647742a5a79bdac986e8935cc0db9e9a2d09b` | 115 675 B | `media/chat_logs/2026/05/cart_10_M6rkfxO.jpg`*; `media/security_photos/2026/05/24/cart_10.jpg` | `fd3a5906` (2026-05-24) |
| `8072d4cc481592818acd3db7ac71cebb502a4be2` | 65 596 B | `media/chat_logs/2026/05/cart_10_ntqglNo.jpg`*; `media/security_photos/2026/05/24/cart_10_ntqglNo.jpg` | `fd3a5906` (2026-05-24) |
| `2a9b7274a8ff40ef82193c7decb28d65d83677bc` | 167 283 B | `media/chat_logs/2026/05/cart_11.jpg`; `media/security_photos/2026/05/24/cart_11.jpg` | `fd3a5906` (2026-05-24) |
| `99ac7a1ccff5091243f8d134999313b015e1ac6d` | 41 333 B | `media/chat_logs/2026/06/cart_20.jpg`*, `cart_21.jpg`*; `media/security_photos/2026/06/06/cart_20.jpg`, `cart_21.jpg` | `863efdf0` (2026-06-06) |

\* Caminho já apagado da árvore antes de `d50fa6e9`, mas presente em commits antigos.

Commits que tocam `media/`: `ec7d3cca`, `af5f7195`, `fd3a5906`, `863efdf0`, `f3c8daad`, `d50fa6e9`.

Checklist de avaliação por imagem:

1. A imagem mostra pessoa identificável, rosto, documento, placa, endereço/unidade do condomínio ou dado de pagamento?
2. É foto de cliente real (produção/staging) ou foto de teste do time?
3. Qual a visibilidade do repositório no GitHub desde 2026-05-17 (público? quem tem acesso? forks?).
4. Se houver dado pessoal de terceiro: registrar como incidente e avaliar comunicação ao titular e à ANPD (LGPD art. 48), com base no risco.

### 2.2 `test_media/`: placeholders sintéticos (prioridade baixa)

São 87 caminhos, todos com no máximo 16 bytes: 71 são bytes arbitrários (`b"fake-image-bytes"` etc.) e 16 são stubs com cabeçalho JPEG gerados pelos testes. Não contêm imagem real. Entram na purga apenas por higiene e para reduzir ruído.

## 3. Plano de remoção do histórico (para aprovação)

> Reescrever o histórico muda o hash de todos os commits a partir de `ec7d3cca` (2026-05-17), exige force-push em `main` e re-clone por todos os colaboradores e servidores. Executar somente após aprovação explícita.

### 3.1 Preparação

1. Concluir a avaliação da seção 2 e decidir se `test_media/` entra na purga (recomendado: sim).
2. Mergear/fechar PRs abertos e congelar pushes em `main` durante a janela. Avisar o time.
3. Backup de segurança com acesso restrito, destruído após a validação:
   `git clone --mirror https://github.com/segmarket/marketchat.git marketchat-backup.git`
4. Liberar temporariamente o force-push na proteção de branch de `main` (GitHub → Settings → Branches).

### 3.2 Reescrita (em clone novo, nunca no working copy de desenvolvimento)

```bash
pip install git-filter-repo
git clone --mirror https://github.com/segmarket/marketchat.git marketchat-purge.git
cd marketchat-purge.git

# Remove os diretórios de upload de todo o histórico
git filter-repo --invert-paths --path media/ --path test_media/

# Garante que as 6 fotos reais não sobrevivam com outro caminho
cat > ../blobs-to-strip.txt <<'EOF'
f0cabfcd901f4d4e3a723114530317343168e60f
7c5131c25ce8938a568e9d088dd49974f33c6eda
a8e647742a5a79bdac986e8935cc0db9e9a2d09b
8072d4cc481592818acd3db7ac71cebb502a4be2
2a9b7274a8ff40ef82193c7decb28d65d83677bc
99ac7a1ccff5091243f8d134999313b015e1ac6d
EOF
git filter-repo --strip-blobs-with-ids ../blobs-to-strip.txt --force
```

### 3.3 Verificação antes do push

```bash
git log --all --oneline -- media test_media          # deve sair vazio
while read b; do git cat-file -e "$b" 2>/dev/null && echo "AINDA EXISTE $b"; done < ../blobs-to-strip.txt
git count-objects -vH                                 # tamanho deve cair
```

Rodar a suíte de testes e o build do front sobre um checkout do resultado.

### 3.4 Publicação

```bash
git push --force --mirror origin
```

Depois: reativar a proteção de `main`.

### 3.5 Limpeza fora do repositório

- **GitHub:** `refs/pull/*` e visualizações em cache não são reescritos pelo push. Abrir chamado no GitHub Support pedindo remoção de *cached views* e objetos órfãos, citando os 6 SHAs acima. Verificar forks e pedir que sejam apagados/rebaseados.
- **Clones locais e servidores** (dev, staging, produção em `~/marketchat`): re-clonar. Não usar `git pull` sobre o histórico antigo, pois reintroduziria os objetos. Apagar clones antigos.
- **Imagens Docker:** o backend já excluía `media` via `.dockerignore`; `test_media` passa a ser excluído agora. Imagens antigas só continham os placeholders sintéticos, sem ação obrigatória.
- **CI/caches:** invalidar caches de checkout, se houver.
- **Backup do passo 3.1:** destruir após confirmar a purga.

### 3.6 Fora do escopo desta purga

- Os arquivos reais em produção/staging vivem nos volumes Docker `marketchat_media_prd` / `marketchat_media_staging` e **não** são afetados pela purga. A exposição deles é a rota `/media/` pública, removida no código mas **ainda ativa no que está implantado** (seção 1.2).
- As cópias locais em `media/` e `test_media/` continuam no disco de quem as tinha; apagar manualmente se não forem necessárias.

## 4. Pendências de deploy (independentes da purga do histórico)

Os comandos, a ordem de execução, os critérios de sucesso e o rollback estão em
[`runbook-contencao-media/README.md`](runbook-contencao-media/README.md). O Apache e o Docker
ficam em máquinas diferentes. A ordem é:

1. preparar as imagens;
2. bloquear `/media` no Apache real;
3. medir o acesso LAN direto ao backend;
4. purgar o Cloudflare;
5. trocar backend e front juntos.

O rollback dos containers mantém o bloqueio.

1. Implantar backend e front juntos. O front antigo coloca `attachment_url` direto em `<img src>`, sem token: com o backend novo recebe 401 e mostra "Erro ao carregar imagem". O front novo depende do endpoint novo.
2. Sem esperar o deploy, adicionar ao vhost Apache **real** de produção e de staging:
   `<Location "/media"> Require all denied </Location>`
   Isso fecha a exposição imediatamente. O custo é o inbox antigo parar de exibir anexos até o deploy.
3. Cloudflare: purgar o cache de `app.marketchat.com.br/media/*` e `staging-api.marketchat.com.br/media/*`, e considerar uma regra WAF bloqueando `/media/*`.
4. Revisar os logs de acesso do Apache/Cloudflare para `GET /media/` com status 200 desde 2026-05-17 (IPs não internos, varredura sequencial de `cart_<id>`), como insumo da avaliação LGPD.
5. Versionar a config Apache de produção (hoje só descrita em `scripts/producao`).
