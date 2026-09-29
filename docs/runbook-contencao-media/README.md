# Runbook — contenção de `/media` e publicação de d50fa6e9, c680ae2a, 4035136c

Status: **para revisão; nada foi executado em servidor, Cloudflare ou remoto Git.**

Objetivo:

- fechar o acesso a `/media/*` (fotos de clientes em `Cart.product_photo` e `ChatMessageLog.attachment`) em produção e staging;
- publicar o código que entrega essas fotos só por endpoints autenticados e verificados por tenant;
- levantar o que já pode ter sido acessado desde 17/05/2026.

## Máquinas envolvidas

O Apache (reverse proxy) e o Docker (backend e front) ficam em **máquinas diferentes**. Todo
comando deste runbook diz em qual delas roda.

| Papel | Produção | Staging | Como é confirmado |
| --- | --- | --- | --- |
| **Estação do operador** (notebook na LAN) | — | — | Tem o repositório, o token do Cloudflare e guarda as evidências em `$EVID` |
| **Host Apache** | **desconhecido** (`APACHE_PRD_SSH`/`APACHE_PRD_IP`) | desconhecido (docs citam `saos101ws01p`) | P0: DNS/túnel do Cloudflare, `descobrir-apache.sh` e probe com id único achado no access log |
| **Host Docker** | `seguser@10.10.10.140` (de `scripts/producao`) | `seguser@192.168.1.23` (de `scripts/staging`) | P0: `descobrir-docker.sh` e destino dos `ProxyPass` do Apache |

`10.10.10.140` é o host **Docker**. Não presuma que ele também seja o Apache; se a descoberta
mostrar que é, as duas colunas apontam para a mesma máquina e nada mais muda.

## Arquivos deste diretório

| Arquivo | Máquina | O que faz |
| --- | --- | --- |
| `descobrir-apache.sh` | host Apache (sudo) | Somente leitura. Config carregada pelo processo em execução e mapa por vhost (`30-vhosts.tsv`: endereço, arquivo:linha, nomes, destinos `ProxyPass`/`RewriteRule [P]`, regra `/media` existente). Também testa, a partir do Apache, o alcance de cada destino no host Docker (`31-destinos.txt`) |
| `descobrir-docker.sh` | host Docker (sudo) | Somente leitura. IPs, portas publicadas em `0.0.0.0`, imagens, rota `/media` no backend em execução, bundle do front, firewall e cron que chama `manage.py` |
| `marketchat-media-block.conf` | host Apache | Bloco `<Location "/media"> Require all denied` a incluir em cada vhost do MarketChat |
| `sondar.sh` | estação, host Apache ou host Docker | Sondas por hostname **sem dados de clientes**: `VIA=cf` (Cloudflare), `VIA=apache` (IP do Apache, Host e SNI preservados), `VIA=docker` (LAN direto na porta do backend). Opcionalmente testa um canário sintético |
| `qa_media_inprocess.py` | container backend (produção e staging) | Verificação sintética **segura para produção**: tudo numa transação revertida, arquivos em diretório temporário e rede bloqueada fora de banco/cache |
| `qa_media_seed.py` | container backend, **só staging** | Cria tenants QA commitados, JPEGs sintéticos e tokens; recusa rodar fora de staging |
| `verificar-midia.sh` | estação (staging) | Verificação HTTP completa com os objetos do seed |
| `qa_media_cleanup.py` | container backend (staging) | Remove o que o seed criou (idempotente) |
| `analisar-logs-media.py` | host Apache (sudo) | Requisições a `/media` nos logs de acesso (texto/.gz) desde uma data |
| `cf_media_analytics.py` | estação | Requisições a `/media` no GraphQL do Cloudflare, limitado à retenção do plano |
| `mapear-caminhos.py` | container backend | Converte caminhos vistos nos logs em tenant/objeto, sem abrir arquivos |

## Ensaios locais já feitos

O ambiente de teste foi removido depois dos ensaios.

**Montagem:**

- Apache 2.4.68 num processo separado, fazendo o papel do host Apache, com dois vhosts: um com `ProxyPass` e outro com `RewriteRule [P]`;
- gunicorn fazendo o papel do backend no host Docker: primeiro o código de `cdf496e`, depois HEAD;
- o `dist` do front servido à parte;
- settings no estilo staging (hosts `staging-*` e Asaas sandbox) com SQLite temporário.

| Cenário | Resultado |
| --- | --- |
| **Linha de base** (sem bloqueio, imagem antiga) | O `sondar.sh VIA=apache` reprova: `/media` chega ao gunicorn (404 do Django). O `verificar-midia.sh CHECKS=media` entrega o arquivo QA com 200, inclusive em `/%6Dedia`, `//media` e `/api/../media` |
| **P2** (bloqueio no Apache, imagem antiga) | `configtest` e graceful OK. `/media`, variantes e canário dão 403 nos dois vhosts; o arquivo QA dá 403. O mapa do `descobrir-apache.sh` passa a mostrar `bloqueio` em cada vhost |
| **P3** (LAN direto no backend, imagem antiga) | Canário **200** direto na porta do backend e 403 pelo Apache. O route check diz `ROTA /media PRESENTE`: é a exposição LAN que dura até a P5 |
| **P5** (troca para HEAD) | 0 falhas pelo Apache e pela LAN direta: anexo 401, `token_not_valid` chega ao Django, canário 404 direto no backend. `verificar-midia.sh` completo: 0 falhas. Route check: `ROTA /media AUSENTE` |
| **Rollback dos containers** (volta a imagem antiga, bloqueio mantido) | Apache segue em 403 para `/media` e o canário volta a dar 200 direto no backend, confirmando o que o rollback documenta |
| **`qa_media_inprocess.py`** | HEAD: 25/25 PASS, com settings de teste e com settings de staging. `cdf496e`: 8 FAIL, entre eles `/media/<arquivo> -> 200` e `URLconf sem rota /media: PRESENTE`, com saída 1. Nenhum resíduo: 0 tenants, 0 arquivos no MEDIA_ROOT real, diretório temporário removido, 0 tentativas de rede |
| **Travas do `qa_media_seed.py`** | Recusa sem `QA_CONFIRM_STAGING=1`, recusa com hostname de produção em `ALLOWED_HOSTS` e recusa com Asaas fora do sandbox, sem criar nada. Em staging: seed, verificação e cleanup (idempotente) sem resíduos |
| **Host/SNI no `VIA=apache`** | Um servidor TLS de teste registrou `sni=app.marketchat.com.br` e `Host: app.marketchat.com.br` |
| **`compose run` da imagem nova** | Com Compose v5.5.1: stdin via pipe funciona, o container de teste usa nome próprio, não publica portas e não toca no container em execução |

Não testado aqui:

- as chamadas à API do Cloudflare, por falta de credenciais;
- `config/settings/production.py`, que nunca é importado localmente;
- um Apache real com `mod_ssl` e vários vhosts por SNI;
- o formato do `httpd -S` no RHEL do servidor (assume-se igual ao do Fedora).

## 0. Contexto que muda a execução

- **Duas exposições distintas:**
  - **Git:** as fotos estão no histórico desde `ec7d3cca` (17/05/2026).
  - **HTTP:** a rota pública `serve` do Django entrou em `2c7cc003` (30/07/2026); antes, `static()` só servia com `DEBUG=True`. A exposição HTTP começa no primeiro deploy após 30/07, a menos que o Apache já servisse `/media` por outro caminho. Os logs são consultados desde 17/05 mesmo assim.
- **O deploy troca só imagens:** não há migrações entre `cdf496e` e `4035136c`. O rollback de código é voltar às imagens anteriores.
- **O deploy não usa Git no servidor:** é rsync `--delete` da estação para `~/marketchat` no host Docker, seguido de `docker compose build/up`. O container recriado perde o `docker logs` anterior. O gunicorn não tem access log, então "quem baixou" só aparece no Apache e no Cloudflare.
- **Três caminhos até o backend,** fechados por mecanismos diferentes:

  | Caminho | Fechado por | A partir de |
  | --- | --- | --- |
  | Internet → Cloudflare → Apache → Docker | bloqueio no Apache, mais a purga do cache do Cloudflare | P2 (origem) e P4 (cache) |
  | LAN → Apache (IP da origem) → Docker | bloqueio no Apache | P2 |
  | LAN → host Docker `:9001` direto (compose publica em `0.0.0.0`) | backend novo, que não tem a rota | P5 |

- **Nada legítimo usa `/media`:** os dois campos acima são os únicos `ImageField`/`FileField`, e nem integrações (Evolution, e-mail) nem o front novo geram URLs `/media`. Bloquear o prefixo inteiro é seguro.

### Ordem da contenção e janela de imagens do inbox

A contenção vem **antes** da troca de código:

1. **P1:** validar o ambiente e preparar as imagens, sem reiniciar nada.
2. **P2:** bloquear `/media` no Apache real e verificar.
3. **P3:** verificar o acesso direto às portas do backend.
4. **P4:** purgar `/media` no Cloudflare.
5. **P5:** trocar backend e front juntos e validar os endpoints autenticados.

| Estado | `/media` pela internet | `/media` pela LAN `:9001` | Imagens no inbox e nos pedidos |
| --- | --- | --- | --- |
| Hoje | exposto (e em cache no Cloudflare) | exposto | funcionam |
| Depois da P2 (bloqueio, imagens antigas) | 403 na origem; cópias em cache até a P4 | exposto | **quebradas** |
| Depois da P4 (purga) | 403 | exposto | **quebradas** |
| Depois da P5 (backend e front novos) | 403 | 404 (rota não existe) | funcionam; aba já aberta precisa de F5 |

> **Janela declarada de imagens indisponíveis.** Do reload do Apache na P2 até o fim da P5, o
> front antigo pede `<img src="/media/…">` e recebe 403. Nesse intervalo, **as fotos de
> conversas no inbox e as fotos de segurança dos carrinhos não aparecem**; o link "Abrir foto"
> do admin antigo também falha. Os arquivos não são alterados e mensagens e fotos novas continuam
> sendo gravadas: só a exibição falha. **Duração-alvo: 15 a 20 minutos** (P2 a P5 sem pausas).
> Depois da P5, quem estava com o inbox aberto precisa recarregar a página (F5). Avise o suporte
> antes da P2: "Durante a manutenção de hoje, entre HH:MM e HH:MM, as imagens do inbox podem não
> aparecer; depois, atualize a página."

| Fase | Duração estimada |
| --- | --- |
| P2: include, configtest, graceful e sondas | 4–6 min |
| P3: sondas LAN e route check | 2–3 min |
| P4: purga e sondas | 2–3 min |
| P5: `up -d` (30–90 s, com `migrate` e `collectstatic`), smoke e verificações | 5–8 min |

Se a P1 falhar, a P2 não começa e a janela não abre.

### Revisão do `qa_media_seed.py`: por que o seed completo fica só em staging

A pergunta era se o seed pode criar dados **commitados** em produção sem acionar cobrança,
WhatsApp, sinais ou outras integrações. **Não é possível demonstrar isso.**

1. **Comandos periódicos selecionam por estado,** e o agendamento (cron/timers) **não está versionado**. Não dá para saber se, quando e com que argumentos rodam:

   | Comando | Seleciona | Efeito externo |
   | --- | --- | --- |
   | `provision_tenant_default_asaas_customers` | tenants com Market e sem `asaas_default_customer_id` | cria cliente no Asaas |
   | `check_subscriptions` | trial vencido | suspende o tenant, desconecta a Evolution e envia e-mail |
   | `send_inactivity_followups` | sessões ociosas de 5 a 15 min com `inactivity_notified=False` | envia WhatsApp (se houver `WhatsappInstance`) |
   | `cleanup_expired_carts` | carrinhos OPEN/AWAITING_* com mais de 15 min | cancela e desbloqueia a sessão |
   | `sync_pending_cart_payments` | carrinhos AWAITING_PAYMENT com id de cobrança | consulta o Asaas |
   | `cleanup_old_photos` | fotos com mais de 30 dias | apaga arquivos |

2. **Sinais:** o único receiver em modelos tocados é `seed_chatbot_workflows_for_new_tenant` (post_save de Tenant), que só escreve no banco. Mas o seed commitado deixa esses workflows em produção até o cleanup.
3. **Views com integrações** (`markets/views`: `on_commit` de sync/provisionamento; `facebook_capi` em thread) não são chamadas pelo seed. Ainda assim, dados commitados ficam visíveis para relatórios, admin, métricas e qualquer worker ou código futuro.
4. **Conta real:** o seed cria um usuário com senha e tokens válidos em produção durante a janela.

As mitigações do seed (sem Market, carrinho CANCELLED, sessão com `inactivity_notified=True`,
sem `WhatsappInstance`, trial válido por 1 dia) reduzem o risco, mas não o provam. Por isso o
seed agora **recusa rodar** se:

- faltar `QA_CONFIRM_STAGING=1`;
- `ALLOWED_HOSTS` tiver `app.`, `api.` ou `marketchat.com.br`;
- `ASAAS_API_URL` não for sandbox.

**Verificação sintética proposta para produção**, sem dados commitados:

| Verificação | O que prova | Por que é segura |
| --- | --- | --- |
| `qa_media_inprocess.py`: na imagem nova antes da troca (`compose run`, P1) e no container novo depois (`docker exec`, P5) | Stack completo do Django com o Host público: anexo e foto 401 anônimo, 401 `token_not_valid`, 401 com token na query, 200 para o dono (sha256, `image/jpeg`, `private, no-store`, `nosniff`), 404 para outro tenant e casos 404; URLs geradas apontam para `/api/...`; `/media/<arquivo>` 404; URLconf sem rota `/media` | Uma transação revertida: nada é commitado, então cron, workers e outras conexões nunca veem os dados e os callbacks `on_commit` são descartados. `MEDIA_ROOT` temporário; e-mail locmem; throttle em cache local. Socket bloqueado fora de banco, cache e loopback (autoteste incluso), e qualquer tentativa reprova. Receivers de sinais fora do esperado reprovam. Único efeito: consome valores de sequência (lacunas de id) e segura locks de linha por cerca de 2 s |
| `sondar.sh` via Cloudflare, via IP do Apache e via LAN no host Docker | Trajeto real por hostname: `/media` 403, variantes não entregam, `/api/auth/me/` 401, anexo 401 com `token_not_valid` (o `Authorization` atravessa Cloudflare e Apache) | Só caminhos e ids inexistentes |
| **Canário** `/app/media/qa-canary/canario-$TS.txt` (texto sintético, sem registro no banco) | Distingue "rota fechada" de "arquivo inexistente": 403 no Apache; na LAN, 200 com a imagem antiga e 404 com a nova | Nenhum código lê ou varre `MEDIA_ROOT` (conferido: nenhum `os.walk`/`listdir`/`glob` em `apps/`). Não é pedido pelo Cloudflare antes do bloqueio, e `.txt` não está na lista padrão de cache. Removido na P5 |
| Route check e bundle do front | O container em execução não tem a rota e o front novo usa `/attachment/` | Somente leitura |

A verificação **na interface** (imagem visível no inbox) é feita em staging com o usuário QA.
Em produção ela é opcional e só vale com um tenant **interno** da equipe, nunca com conta de
cliente.

## 1. Variáveis (estação do operador; fixe uma vez por janela)

```bash
export TS=$(date +%Y%m%dT%H%M%S)
export RB=$HOME/Documentos/marketchat/docs/runbook-contencao-media
export EVID=$HOME/mc-incidente-media && mkdir -p "$EVID" && chmod 700 "$EVID"

# Host Docker (confirmados pelos scripts de deploy)
export DOCKER_PRD_SSH=seguser@10.10.10.140 DOCKER_PRD_IP=10.10.10.140
export DOCKER_STG_SSH=seguser@192.168.1.23 DOCKER_STG_IP=192.168.1.23
# Host Apache (preencher na P0; o IP é o que a estação alcança e em que o vhost escuta)
export APACHE_PRD_SSH= APACHE_PRD_IP=
export APACHE_STG_SSH= APACHE_STG_IP=
# Destino dos ProxyPass no host Docker (preencher na P0; o compose publica 9001/3000)
export DOCKER_PRD_API=http://10.10.10.140:9001 DOCKER_STG_API=

# Hostnames (a P0 confirma e acrescenta; api.* e o apex entram mesmo que pareçam ociosos)
export PRD_HOSTS="app.marketchat.com.br api.marketchat.com.br marketchat.com.br www.marketchat.com.br"
export PRD_API_HOSTS="api.marketchat.com.br"                          # só API: "/" não é testado
export PRD_SPA_HOSTS="marketchat.com.br www.marketchat.com.br"        # só SPA/landing: pula /api
export STG_HOSTS="staging-api.marketchat.com.br staging-app.marketchat.com.br staging.marketchat.com.br"
export STG_API_HOSTS="staging-api.marketchat.com.br" STG_SPA_HOSTS="staging-app.marketchat.com.br staging.marketchat.com.br"

export CF_API_TOKEN=            # Zone:Read, Analytics:Read, Cache Purge, Zone WAF:Edit, Cloudflare Tunnel:Read
export CF_ZONE_ID= CF_ACCOUNT_ID=
export CF=https://api.cloudflare.com/client/v4
cfapi() { curl -sS -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" "$@"; }
export CANARY=qa-canary/canario-$TS.txt
```

## 2. P0 — Descoberta (somente leitura, por máquina)

Não presuma que `docs/*.apache.conf` está em uso. O que vale é o que o processo Apache em execução
carregou e o que o Cloudflare de fato encaminha.

### P0.1 Estação: para onde o Cloudflare manda cada hostname

```bash
cfapi "$CF/zones/$CF_ZONE_ID/dns_records?per_page=500" \
  | jq -r '.result[] | select(.type|test("^(A|AAAA|CNAME)$")) | select(.name|test("marketchat")) | [.name,.type,.content,(.proxied|tostring)] | @tsv' \
  | sort | tee "$EVID/p0-cf-dns-$TS.tsv"
cfapi "$CF/zones/$CF_ZONE_ID/settings/ssl" | jq -r .result.value | tee "$EVID/p0-cf-ssl-$TS.txt"   # flexible => origem em :80

# Túneis: CNAME <uuid>.cfargotunnel.com
for t in $(awk -F'\t' '$3 ~ /cfargotunnel\.com$/ {sub(/\.cfargotunnel\.com$/, "", $3); print $3}' "$EVID/p0-cf-dns-$TS.tsv" | sort -u); do
  echo "== túnel $t"
  cfapi "$CF/accounts/$CF_ACCOUNT_ID/cfd_tunnel/$t" | jq -r '.result | "nome=\(.name) status=\(.status) config_remota=\(.remote_config)"'
  cfapi "$CF/accounts/$CF_ACCOUNT_ID/cfd_tunnel/$t/connections" | jq -r '.result[]? | .conns[]? | "conector origin_ip=\(.origin_ip) colo=\(.colo_name) desde=\(.opened_at)"'
  cfapi "$CF/accounts/$CF_ACCOUNT_ID/cfd_tunnel/$t/configurations" | jq -r '.result.config.ingress[]? | "\(.hostname // "*") -> \(.service)"'
done | tee "$EVID/p0-cf-tunnels-$TS.txt"
```

Como interpretar:

- **`A`/`AAAA`:** o conteúdo é o IP de origem. Se for público com NAT, a equipe de rede indica o host interno. Esse é o candidato a host Apache.
- **Túnel:** o host Apache é o `service:` do ingress (ex.: `https://apache-interno:443`). O `origin_ip` dos conectores identifica onde roda o `cloudflared`. Com config local, ela está em `/etc/cloudflared` no conector, e o `descobrir-apache.sh` a registra em `26-cloudflared.txt` se o conector for o próprio host Apache.
- **SSL `flexible`:** o Cloudflare fala com a origem em `:80`, então o vhost `:80` também recebe o bloqueio e as sondas usam `SCHEMES="https http"`.
- **`proxied=false`:** o hostname vai direto à origem, e purga e WAF não se aplicam a ele. Anote na tabela.

### P0.2 Host Apache: configuração efetiva e mapa por vhost

Rode em **cada** candidato da P0.1. As saídas vão para `/root` no próprio host e uma cópia vem para a estação.

```bash
scp "$RB/descobrir-apache.sh" "$APACHE_PRD_SSH:/tmp/"
ssh -t "$APACHE_PRD_SSH" "sudo OUT=/root/mc-discovery-$TS HOSTNAMES_RE=marketchat bash /tmp/descobrir-apache.sh \
  && sudo tar -C /root -czf /tmp/mc-discovery-$TS.tgz mc-discovery-$TS && sudo chown \$USER /tmp/mc-discovery-$TS.tgz"
scp "$APACHE_PRD_SSH:/tmp/mc-discovery-$TS.tgz" "$EVID/p0-apache-prd-$TS.tgz" && ssh "$APACHE_PRD_SSH" "rm -f /tmp/mc-discovery-$TS.tgz"
tar -xzf "$EVID/p0-apache-prd-$TS.tgz" -C "$EVID" && column -t -s$'\t' <(cut -f1-5 "$EVID/mc-discovery-$TS/30-vhosts.tsv")
cat "$EVID/mc-discovery-$TS/31-destinos.txt"
# Não capture a saída de "ssh -t": o TTY mistura \r e o prompt do sudo.
```

O que sai:

- **`30-vhosts.tsv`:** uma linha por vhost cujo nome casa com `marketchat`, com endereço:porta, arquivo:linha do `<VirtualHost>`, nomes, destinos de `ProxyPass`/`RewriteRule [P]` e a coluna `regra_media` (`nenhuma`, `proxy`, `bloqueio` ou `bloqueio+proxy`). `proxy` significa que o vhost repassa `/media` explicitamente.
- **`31-destinos.txt`:** a partir do host Apache, `GET /api/auth/me/` (esperado 401 no backend) e `GET /` em cada destino. Confirma qual host:porta Docker atende cada vhost.
- **Demais arquivos:** o binário é chamado com os mesmos `-f/-d/-D` do processo mestre (no RHEL, o `apachectl` não aceita `-S`), além da árvore de includes, dos `CustomLog`, do logrotate, dos peers em :80/:443 (devem ser IPs do Cloudflare) e dos arquivos alterados depois do start do mestre.

Se o script disser que o Apache não foi encontrado, **pare**: o proxy é outro e este runbook precisa ser adaptado.

### P0.3 Host Docker: portas, imagens e rota em execução

```bash
scp "$RB/descobrir-docker.sh" "$DOCKER_PRD_SSH:/tmp/"
ssh -t "$DOCKER_PRD_SSH" "sudo OUT=/root/mc-docker-$TS BACKEND=marketchat_backend_prd FRONTEND=marketchat_frontend_prd bash /tmp/descobrir-docker.sh \
  && sudo tar -C /root -czf /tmp/mc-docker-$TS.tgz mc-docker-$TS && sudo chown \$USER /tmp/mc-docker-$TS.tgz"
scp "$DOCKER_PRD_SSH:/tmp/mc-docker-$TS.tgz" "$EVID/p0-docker-prd-$TS.tgz" && ssh "$DOCKER_PRD_SSH" "rm -f /tmp/mc-docker-$TS.tgz"
tar -xzf "$EVID/p0-docker-prd-$TS.tgz" -C "$EVID" && cat "$EVID/mc-docker-$TS/99-resumo.txt"
```

Esperado hoje: `ROTA /media PRESENTE`, `9001` e `3000` em `0.0.0.0`, e o bundle do front sem
`/attachment/`. Anote os agendamentos que chamam `manage.py`: eles embasam a revisão do seed.

### P0.4 Estação: confirmar por hostname qual Apache e qual vhost atendem

Um probe com id único vai pelo Cloudflare e depois é procurado no access log do host Apache.
Encontrar o id prova que o tráfego daquele hostname chega **a este Apache**, e o arquivo de log
indica o vhost. Os caminhos são inexistentes; nenhuma foto é tocada.

```bash
cd "$RB"
PID0=p0cf-$TS
HOSTS="$PRD_HOSTS" API_HOSTS="$PRD_API_HOSTS" SPA_HOSTS="$PRD_SPA_HOSTS" VIA=cf EXPECT_MEDIA=404 EXPECT_NEW=404 PROBE_ID=$PID0 \
  ./sondar.sh | tee "$EVID/p0-sonda-cf-$TS.txt"
ssh -t "$APACHE_PRD_SSH" "sudo grep -rsn 'qa-probe-$PID0' /var/log/httpd /var/log/apache2 | cut -c1-220"

PID1=p0ap-$TS     # direto no IP do Apache, preservando Host e SNI (use SCHEMES="https http" se SSL=flexible)
HOSTS="$PRD_HOSTS" API_HOSTS="$PRD_API_HOSTS" SPA_HOSTS="$PRD_SPA_HOSTS" VIA=apache APACHE_IP=$APACHE_PRD_IP \
  EXPECT_MEDIA=404 EXPECT_NEW=404 PROBE_ID=$PID1 ./sondar.sh | tee "$EVID/p0-sonda-apache-$TS.txt"
ssh -t "$APACHE_PRD_SSH" "sudo grep -rsn 'qa-probe-$PID1' /var/log/httpd /var/log/apache2 | cut -c1-220"
```

- **Leitura dos resultados:**
  - `404` com `server=gunicorn` ou `xfo=DENY` em `/media/<probe>`: chegou ao Django, é o vhost exposto;
  - `403`: já há bloqueio;
  - `200 text/html`: o SPA (`serve -s`) respondeu; ele não expõe arquivos, mas o vhost recebe o bloqueio mesmo assim;
  - `301/302`: vhost que só redireciona.
- Nesta fase, as linhas FAIL do `sondar.sh` são informativas: descrevem o estado atual.
- Se a estação não alcança `$APACHE_PRD_IP` (firewall só para o Cloudflare), rode o `sondar.sh` no próprio host Apache com `APACHE_IP=` do `Listen` do vhost.
- Se o id **não** aparecer no log de nenhum candidato, a origem é outra máquina: volte à P0.1.

### P0.5 Tabela de descoberta (preencher antes de seguir)

Critério de parada: **todo** hostname de `PRD_HOSTS` e `STG_HOSTS` tem uma linha completa.

| Hostname | Cloudflare: IP de origem ou túnel → service | proxied | Host Apache efetivo (nome, IP) | Vhost carregado (arquivo:linha, porta) | Destino ProxyPass (host Docker:porta) | Probe achado no log (arquivo) | `regra_media` hoje |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `app.marketchat.com.br` | | | | | | | |
| `api.marketchat.com.br` | | | | | | | |
| `marketchat.com.br` | | | | | | | |
| `www.marketchat.com.br` | | | | | | | |
| `staging-api.marketchat.com.br` | | | | | | | |
| `staging-app.marketchat.com.br` | | | | | | | |
| `staging.marketchat.com.br` | | | | | | | |

### P0.6 Estação: Cloudflare, somente leitura

```bash
cfapi "$CF/zones/$CF_ZONE_ID/url_normalization" | jq .result        # type=cloudflare junta // em /
cfapi "$CF/zones/$CF_ZONE_ID/settings/cache_level" | jq -r .result.value
cfapi "$CF/zones/$CF_ZONE_ID/settings/browser_cache_ttl" | jq -r .result.value
cfapi "$CF/zones/$CF_ZONE_ID/rulesets/phases/http_request_cache_settings/entrypoint" \
  | jq '.result.rules[]? | {description, expression, enabled, action_parameters}'
cfapi "$CF/zones/$CF_ZONE_ID/pagerules" | jq '.result[]? | {targets, actions, status}'
cfapi "$CF/zones/$CF_ZONE_ID/rulesets/phases/http_request_firewall_custom/entrypoint" \
  | jq '{id: .result.id, regras: [.result.rules[]? | {id, description, enabled}]}'
CF_API_TOKEN=$CF_API_TOKEN CF_ZONE_ID=$CF_ZONE_ID \
  python3 "$RB/cf_media_analytics.py" --since 2026-05-17 > "$EVID/cf-media-$TS.csv" 2> "$EVID/cf-media-resumo-$TS.txt"
chmod 600 "$EVID"/cf-media-*; cat "$EVID/cf-media-resumo-$TS.txt"
```

- **Cache:** sem regras, o Cloudflare guarda `.jpg` pelo Edge TTL padrão (o `serve` do Django não mandava `Cache-Control`). Navegadores podem ter cópias próprias, que não são purgáveis. Os endpoints novos respondem `private, no-store` e não entram no cache.
- **Analytics:** `cacheStatus` igual a `hit`, `stale`, `revalidated` ou `updating` indica caminho que teve cópia na borda. Se o resumo mostrar **LACUNA**, a retenção do plano não cobre desde 17/05.
- **Nunca** faça `curl` em caminhos reais para "ver se está em cache": um MISS faz o Cloudflare buscar a foto na origem e guardá-la.

## 3. P0 — Backups e evidências, separados por máquina (antes de qualquer mudança)

| Máquina | O que | Onde fica |
| --- | --- | --- |
| Estação | DNS, SSL, túneis, regras e analytics do Cloudflare; cópias das descobertas e das sondas | `$EVID` (`chmod 700`) |
| Host Apache | Config inteira e cada arquivo carregado, logs de acesso (inclusive `.gz`), descoberta | `/root/mc-apache-$TS/` no host Apache |
| Host Docker | `docker logs` dos containers, inspect, inventário do volume (só metadados), tags das imagens atuais para rollback, tarball do código implantado | `~/mc-incidente-$TS/`, `~/marketchat-code-$TS.tgz` e imagens `marketchat-rollback/*:$TS` no host Docker; a descoberta fica em `/root/mc-docker-$TS/` (cópia em `$EVID`) |

**Host Apache** (troque o `APACHE_PRD_SSH` pelo de staging no ensaio):

```bash
ssh -t "$APACHE_PRD_SSH" "sudo bash -c 'set -e; umask 077; D=/root/mc-apache-$TS; mkdir -p \$D; \
  for c in /etc/httpd /etc/apache2; do [ -d \$c ] && tar -C / -czpf \$D/etc-\$(basename \$c).tgz \${c#/}; done; \
  tar -czpf \$D/arquivos-carregados.tgz -T /root/mc-discovery-$TS/20-arquivos-carregados.txt 2>/dev/null; \
  for l in /var/log/httpd /var/log/apache2; do [ -d \$l ] && tar -C / -czpf \$D/logs-\$(basename \$l).tgz \${l#/}; done; \
  cp -a /root/mc-discovery-$TS \$D/; sha256sum \$D/*.tgz > \$D/SHA256SUMS; ls -la \$D'"
```

Se algum `CustomLog` (em `22-diretivas-relevantes.txt`) apontar para fora de `/var/log/httpd` ou `/var/log/apache2`, acrescente o diretório ao tar.

**Host Docker:**

```bash
ssh "$DOCKER_PRD_SSH" TS="$TS" bash -s <<'EOF'
set -euo pipefail
umask 077; D=~/mc-incidente-$TS; mkdir -p "$D"
for c in marketchat_backend_prd marketchat_frontend_prd; do
  docker inspect -f '{{.Name}} created={{.Created}} started={{.State.StartedAt}} image={{.Image}} log={{json .HostConfig.LogConfig}}' "$c" >> "$D/containers.txt"
  docker logs --timestamps "$c" > "$D/$c.log" 2>&1
done
docker exec marketchat_backend_prd find /app/media -type f -printf '%TY-%Tm-%Td %TH:%TM\t%s\t%P\n' | sort > "$D/media-inventario.tsv"
docker tag "$(docker inspect -f '{{.Image}}' marketchat_backend_prd)"  "marketchat-rollback/backend:$TS"
docker tag "$(docker inspect -f '{{.Image}}' marketchat_frontend_prd)" "marketchat-rollback/frontend:$TS"
tar -C ~ -czpf ~/marketchat-code-$TS.tgz --exclude=marketchat/front-end/node_modules --exclude=marketchat/media marketchat
sha256sum "$D"/* ~/marketchat-code-$TS.tgz > "$D/SHA256SUMS"
docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' | grep marketchat-rollback
wc -l "$D/media-inventario.tsv"
EOF
```

Critério:

- os arquivos existem, com tamanho maior que zero, e o `SHA256SUMS` foi gravado em cada máquina;
- `marketchat-rollback/backend:$TS` e `marketchat-rollback/frontend:$TS` aparecem em `docker images` **antes** do build da P1, que retagueia as imagens;
- o inventário tem uma linha por arquivo, e nenhum arquivo foi aberto.

## 4. Ensaio completo em staging

Execute as seções 2, 3 e 5 inteiras em staging antes de produção, com estas substituições:

| Item | Produção | Staging |
| --- | --- | --- |
| Host Apache | `$APACHE_PRD_SSH` / `$APACHE_PRD_IP` | `$APACHE_STG_SSH` / `$APACHE_STG_IP` |
| Host Docker | `$DOCKER_PRD_SSH` / `$DOCKER_PRD_API` | `$DOCKER_STG_SSH` / `$DOCKER_STG_API` |
| Hostnames | `$PRD_HOSTS`, `$PRD_API_HOSTS`, `$PRD_SPA_HOSTS` | `$STG_HOSTS`, `$STG_API_HOSTS`, `$STG_SPA_HOSTS` |
| Sync | `./scripts/deploy-prd.sh sync` | `./scripts/staging/deploy-remote.sh sync` |
| Helpers no host Docker | `scripts/producao/common.sh`: `production_require_env`, `production_compose`, `production_smoke_test`, `PRODUCTION_ON_SERVER=1` | `scripts/staging/common.sh`: `staging_require_env`, `staging_compose`, `staging_smoke_test`, `STAGING_ON_SERVER=1` |
| Containers | `marketchat_backend_prd`, `marketchat_frontend_prd` | `marketchat_backend_staging`, `marketchat_frontend_staging` (o Redis não é recriado) |
| Excludes do rsync | `scripts/producao/rsync-excludes.txt` | `scripts/staging/rsync-excludes.txt` |

**Só em staging**, entre a P5 e a P6, rode também a verificação HTTP completa e a de interface com dados commitados:

```bash
export QA_RUN_ID=$(date +%y%m%d%H%M)
ssh "$DOCKER_STG_SSH" "docker exec -i -e QA_RUN_ID=$QA_RUN_ID -e QA_CONFIRM_STAGING=1 marketchat_backend_staging python manage.py shell" \
  < "$RB/qa_media_seed.py" | sed -n 's/^QA_JSON=//p' > "$EVID/qa-stg-$QA_RUN_ID.json"
chmod 600 "$EVID/qa-stg-$QA_RUN_ID.json"; export QA_JSON_FILE=$EVID/qa-stg-$QA_RUN_ID.json
for h in staging-api.marketchat.com.br; do     # host que repassa /api
  BASE_URL=https://$h SKIP_SPA=1 "$RB/verificar-midia.sh" | tee "$EVID/stg-verif-cf-$h.txt"
  BASE_URL=https://$h SKIP_SPA=1 RESOLVE_IP=$APACHE_STG_IP INSECURE=1 "$RB/verificar-midia.sh" | tee "$EVID/stg-verif-apache-$h.txt"
done
```

Critério: 0 falhas nas duas execuções, inclusive `Authorization chegou ao Django`.

Na interface:

1. Numa janela anônima, faça login em staging com `user_a_email` e `user_a_password` do JSON QA.
2. No inbox, a conversa "Morador QA" mostra a imagem "MARKETCHAT QA CHAT".
3. No DevTools/Network, só aparece `GET /api/chatbot/messages/<id>/attachment/` → 200, sem nenhuma requisição a `/media`.

Depois, limpe:

```bash
ssh "$DOCKER_STG_SSH" "docker exec -i -e QA_RUN_ID=$QA_RUN_ID marketchat_backend_staging python manage.py shell" < "$RB/qa_media_cleanup.py"
rm -f "$QA_JSON_FILE"
```

Critério: `QA_CLEANUP … restantes=0`.

**Só siga para produção** se todos os critérios das fases P1 a P6 passarem em staging e a janela
P2→P5 couber no alvo de 15 a 20 minutos.

## 5. Produção

### P1 — Validar o ambiente e preparar as imagens (sem reiniciar nada; janela ainda fechada)

**P1.1 Estação: pré-voo e dry-run do rsync.**

```bash
cd ~/Documentos/marketchat
git status --short                                   # só docs/ não rastreados
git log --oneline origin/main..main                  # exatamente 4035136c, c680ae2a, d50fa6e9
git worktree add /tmp/mc-deploy-4035136c 4035136c
cp scripts/producao/env.deploy /tmp/mc-deploy-4035136c/scripts/producao/
grep -E '^(PRODUCTION_SSH|PUSH_LOCAL_ENV)=' /tmp/mc-deploy-4035136c/scripts/producao/env.deploy   # SSH = $DOCKER_PRD_SSH; PUSH_LOCAL_ENV=0
W=/tmp/mc-deploy-4035136c
rsync -anic --delete --exclude-from="$W/scripts/producao/rsync-excludes.txt" "$W/" "$DOCKER_PRD_SSH:marketchat/" \
  > "$EVID/prd-rsync-dryrun-$TS.txt"
git diff --name-only cdf496e 4035136c | sort > "$EVID/esperado.txt"
awk '$1 ~ /^(>f|\*deleting)/ {print $NF}' "$EVID/prd-rsync-dryrun-$TS.txt" | sort > "$EVID/rsync-mudancas.txt"
comm -13 "$EVID/esperado.txt" "$EVID/rsync-mudancas.txt"     # mudanças NÃO explicadas pelos 3 commits
```

Critério: o `comm` só mostra ruído conhecido, como a remoção de `test_media/`. Qualquer outro arquivo significa que o host Docker roda código diferente de `cdf496e`: **pare** e reconcilie antes.

**P1.2 Estação para o host Docker: enviar o código e construir as imagens.**

```bash
cd /tmp/mc-deploy-4035136c && ./scripts/deploy-prd.sh sync
ssh "$DOCKER_PRD_SSH" 'cd ~/marketchat && PRODUCTION_ON_SERVER=1 PRODUCTION_SKIP_ENV_PROMPT=1 \
  bash -c "source scripts/producao/common.sh && production_require_env && production_compose build"'
ssh "$DOCKER_PRD_SSH" "docker ps --format '{{.Names}} {{.Image}} {{.RunningFor}}' | grep marketchat_"
```

Critério: o build termina sem erro, e os containers seguem com o mesmo tempo de execução de antes.

**P1.3 Host Docker: verificação sintética na imagem nova, antes da troca.** O comando cria um container temporário a partir da imagem recém-construída, sem publicar portas, sem dependências e sem tocar nos containers em execução:

```bash
ssh "$DOCKER_PRD_SSH" "cd ~/marketchat && PRODUCTION_ON_SERVER=1 bash -c 'source scripts/producao/common.sh && \
  production_compose run --rm --no-deps -T --name mc-qa-inproc-$TS --entrypoint python backend manage.py shell'" \
  < "$RB/qa_media_inprocess.py" | tee "$EVID/p1-inprocess-$TS.txt"; echo "exit=${PIPESTATUS[0]}"
grep -E '^(FAIL|QA_INPROCESS)' "$EVID/p1-inprocess-$TS.txt" | cut -c1-300
```

Critério: `exit=0`, `"failed": []` e 25 PASS. Entre eles:

- anexo e foto nos cenários anônimo, token inválido, token na query, dono e outro tenant;
- `URLconf sem rota /media`;
- `rede: nenhuma tentativa fora de banco/cache/loopback`;
- `rollback: nenhum dado QA persistido`.

Se algo falhar: **pare**. Nada mudou em produção além do código em disco e das imagens novas; aplique o **R0**.

**P1.4 Host Docker: front novo na imagem nova.**

```bash
ssh "$DOCKER_PRD_SSH" "cd ~/marketchat && PRODUCTION_ON_SERVER=1 bash -c 'source scripts/producao/common.sh && \
  production_compose run --rm --no-deps -T --entrypoint sh frontend -c \"grep -l /attachment/ dist/assets/*.js | head -3\"'"
```

Critério: pelo menos um arquivo listado.

**P1.5 Host Docker: canário sintético no volume.** É gravado pelo container **atual**; o volume é o mesmo que o container novo vai usar:

```bash
ssh "$DOCKER_PRD_SSH" "docker exec marketchat_backend_prd sh -c 'mkdir -p /app/media/qa-canary && \
  printf \"marketchat canario sintetico %s\n\" $TS > /app/media/$CANARY && ls -l /app/media/$CANARY'"
```

Não peça o canário pelo Cloudflare nem pelo Apache antes da P2.

**Checklist para abrir a janela:**

- P1.1 a P1.5 OK;
- suporte avisado;
- sessões SSH abertas no host Apache e no host Docker;
- `mc-discovery-$TS` com o arquivo:linha de cada vhost à mão.

### P2 — Bloqueio `/media` no Apache real (INÍCIO DA JANELA de imagens)

**P2.1 Host Apache:** instalar o bloco e incluí-lo em cada vhost do MarketChat da tabela P0.5. Inclua o `:443` e também o `:80` se ele repassar tráfego (SSL `flexible` ou vhost sem redirect).

```bash
# Descoberta: 99-resumo.txt dá o comando (CTL) e o layout.
CONF=/etc/httpd; [ -d /etc/apache2 ] && CONF=/etc/apache2
CTL="httpd -f /etc/httpd/conf/httpd.conf"          # conforme "comando:" em 99-resumo.txt; Debian: apache2ctl
SNIPDIR=$CONF/marketchat; SNIP=$SNIPDIR/media-block.conf  # pasta própria: fora de conf.d/ e conf-enabled/
sudo install -d -m 755 "$SNIPDIR"
sudo install -o root -g root -m 644 /tmp/marketchat-media-block.conf "$SNIP"   # scp antes, a partir de $RB

# Para CADA linha de 30-vhosts.tsv. Vários vhosts no mesmo arquivo: do maior N para o menor.
F=$(readlink -f ARQUIVO_DO_VHOST); N=LINHA_DO_VIRTUALHOST
END=$(awk -v s="$N" 'NR>s && /<\/VirtualHost>/ {print NR; exit}' "$F")
sudo sed -n "${N},${END}p" "$F"                                  # confira: é o vhost certo?
sudo sed -i "${END}i\\    Include $SNIP" "$F"                     # vira a última diretiva do vhost
sudo sed -n "${N},$((END+1))p" "$F"
```

O `Include` precisa ser a **última** diretiva do vhost: um `<Location>` posterior com `Require all granted` sobrescreveria o bloqueio. O bloco nunca vai em `conf.d/` ou `conf-enabled/`, onde valeria para outros sites do servidor.

**P2.2 Host Apache:** validar e recarregar sem derrubar conexões.

```bash
sudo $CTL -t                                                     # precisa de "Syntax OK"
sudo $CTL -S 2>&1 | sed -E 's/:[0-9]+\)$/)/' > /tmp/S-depois.txt
sudo sed -E 's/:[0-9]+\)$/)/' /root/mc-discovery-$TS/11-apachectl-S.txt | diff - /tmp/S-depois.txt   # só "$ comando" e "[exit=0]" diferem
sudo systemctl reload httpd                                      # Debian: apache2. Graceful: requisições em curso terminam
systemctl is-active httpd; sudo tail -n 5 /var/log/httpd/error_log     # AH00493/graceful, sem AH00526
date -Is | tee /tmp/mc-janela-inicio-$TS                         # INÍCIO DA JANELA
sudo OUT=/root/mc-discovery-$TS-p2 HOSTNAMES_RE=marketchat bash /tmp/descobrir-apache.sh | sed -n '/== Vhosts que casam/,/^$/p'
```

- Se o Apache roda em container: `docker exec <c> httpd -t` e depois `docker exec <c> httpd -k graceful`.
- Se o `configtest` falhar: **não recarregue** e aplique o **R1a**. A config em execução não mudou e a janela não abriu.

Critério: `Syntax OK`, `-S` sem mudança de vhosts, reload sem erros, e `regra_media` com `bloqueio` em **todas** as linhas.

**P2.3 Estação:** sondas por hostname via Cloudflare e direto no IP do Apache. O backend ainda é o antigo, por isso `EXPECT_NEW=404`.

```bash
cd "$RB"
for via in cf apache; do
  HOSTS="$PRD_HOSTS" API_HOSTS="$PRD_API_HOSTS" SPA_HOSTS="$PRD_SPA_HOSTS" VIA=$via APACHE_IP=$APACHE_PRD_IP \
    EXPECT_NEW=404 CANARY_PATH=$CANARY PROBE_ID=p2$via-$TS ./sondar.sh | tee "$EVID/p2-sonda-$via-$TS.txt"
done
```

Critério, com 0 falhas nas duas execuções e para cada hostname:

- `/media/<probe>`, `/media/<canário>` e as variantes → **403**; nenhuma variante com 200;
- `/api/auth/me/` → 401;
- `/` → 200.

Via Cloudflare, o 403 do Apache chega com `server=cloudflare`; direto, com `server=Apache`.
Cópias de fotos reais ainda podem estar no cache do Cloudflare até a P4. As sondas não as
detectam de propósito, porque não usam caminhos reais.

### P3 — Acesso direto às portas internas do backend (host Docker)

Mede o que o bloqueio no Apache **não** cobre. Nada é alterado.

```bash
cd "$RB"
# Estação (outra máquina da LAN): porta do backend publicada em 0.0.0.0.
HOSTS="$DOCKER_PRD_IP app.marketchat.com.br" VIA=docker DOCKER_URL=$DOCKER_PRD_API EXPECT_NEW=404 \
  CANARY_PATH=$CANARY EXPECT_CANARY=200 PROBE_ID=p3lan-$TS ./sondar.sh | tee "$EVID/p3-lan-estacao-$TS.txt"
curl -s -o /dev/null -w "front LAN :3000 -> %{http_code}\n" "http://$DOCKER_PRD_IP:3000/"

# Host Apache: o destino do ProxyPass precisa responder (é o caminho legítimo).
scp "$RB/sondar.sh" "$APACHE_PRD_SSH:/tmp/"
ssh "$APACHE_PRD_SSH" "HOSTS=app.marketchat.com.br VIA=docker DOCKER_URL=$DOCKER_PRD_API EXPECT_NEW=404 \
  CANARY_PATH=$CANARY EXPECT_CANARY=200 PROBE_ID=p3ap-$TS bash /tmp/sondar.sh" | tee "$EVID/p3-lan-apache-$TS.txt"

# Host Docker: rota ainda presente no container em execução.
ssh "$DOCKER_PRD_SSH" "docker exec marketchat_backend_prd python manage.py shell -c \"from django.urls import get_resolver; print('ROTA /media PRESENTE' if any(str(p.pattern).startswith('media') for p in get_resolver().url_patterns) else 'ROTA /media AUSENTE')\"" 2>&1 | tail -1
```

Esperado: `/api/auth/me/` 401 nas duas origens, o canário **200** (a imagem antiga ainda serve
`/media` na LAN) e `ROTA /media PRESENTE`.

Registre de quais máquinas a porta responde. Essa exposição termina na P5. Se ela alcançar redes
além do host Apache, entra na pendência 4 (restrição por firewall, com aprovação própria).

Se o canário não der 200 na estação, a porta já está restrita: anote como mitigação existente.

### P4 — Invalidar respostas antigas de `/media` no Cloudflare

Depois da P2, a origem responde 403 a `/media`, então o Cloudflare não consegue repovoar o cache
após a purga.

```bash
PURGE=$(jq -nc --arg h "$PRD_HOSTS" '{prefixes: ($h | split(" ") | map(select(length > 0) + "/media"))}')
echo "$PURGE"
cfapi -X POST "$CF/zones/$CF_ZONE_ID/purge_cache" --data "$PURGE" | tee "$EVID/cf-purge-$TS.json" | jq '.success, .errors'
cd "$RB" && HOSTS="$PRD_HOSTS" API_HOSTS="$PRD_API_HOSTS" SPA_HOSTS="$PRD_SPA_HOSTS" VIA=cf EXPECT_NEW=404 \
  CANARY_PATH=$CANARY PROBE_ID=p4-$TS ./sondar.sh | tee "$EVID/p4-sonda-cf-$TS.txt"
```

Critério: `success: true` e as sondas com 0 falhas, sem `cf=HIT` em `/media` (403 não é
guardado por padrão). Hostnames com `proxied=false` não têm cache: ignore-os aqui. A purga é
irreversível e não tem efeito colateral.

**Regra WAF (recomendada; exige aprovação explícita porque altera a zona).** É defesa em
profundidade e registra tentativas em Security Events. Também cobre `//media` caso a
normalização da zona seja RFC 3986.

```bash
HOSTSET=$(printf '\\"%s\\" ' $PRD_HOSTS $STG_HOSTS)
RULE="{\"description\":\"MarketChat - bloquear /media (runbook contencao)\",\"action\":\"block\",\"enabled\":true,
\"expression\":\"(http.host in {${HOSTSET% }} and (starts_with(lower(http.request.uri.path), \\\"/media\\\") or starts_with(lower(http.request.uri.path), \\\"//media\\\")))\"}"
echo "$RULE" | jq .        # confira a expressão antes de enviar
RS=$(cfapi "$CF/zones/$CF_ZONE_ID/rulesets/phases/http_request_firewall_custom/entrypoint" | jq -r '.result.id // empty')
if [[ -n "$RS" ]]; then   # acrescenta sem tocar nas regras existentes
  cfapi -X POST "$CF/zones/$CF_ZONE_ID/rulesets/$RS/rules" --data "$RULE" > "$EVID/cf-waf-$TS.json"
else                      # só quando ainda não existe nenhuma regra custom na zona
  cfapi -X PUT "$CF/zones/$CF_ZONE_ID/rulesets/phases/http_request_firewall_custom/entrypoint" \
    --data "{\"rules\":[$RULE]}" > "$EVID/cf-waf-$TS.json"
fi
jq -r '.success, (.result.id), (.result.rules[] | select(.description|startswith("MarketChat - bloquear /media")) | .id)' "$EVID/cf-waf-$TS.json"
```

Guarde `RS` e o id da regra (`RULE_ID`) para o R3. Critério: `/media` responde com a página de
bloqueio do Cloudflare e a regra aparece em Security Events.

### P5 — Trocar backend e front juntos e validar os endpoints autenticados (FIM DA JANELA)

**P5.1 Host Docker:** trocar os dois containers no mesmo comando, sem build.

```bash
ssh "$DOCKER_PRD_SSH" 'cd ~/marketchat && PRODUCTION_ON_SERVER=1 bash -c "source scripts/producao/common.sh \
  && production_compose up -d --no-build backend frontend && sleep 6 && production_compose ps && production_smoke_test"'
```

Critério: API `401` em `/api/auth/me/`, front `200` e os dois containers `Up`. Se falhar, aplique o **R2**.

**P5.2 Host Docker:** verificação sintética no container em execução, mais o route check.

```bash
ssh "$DOCKER_PRD_SSH" "docker exec -i marketchat_backend_prd python manage.py shell" \
  < "$RB/qa_media_inprocess.py" | tee "$EVID/p5-inprocess-$TS.txt"; echo "exit=${PIPESTATUS[0]}"
grep -E '^(FAIL|QA_INPROCESS)' "$EVID/p5-inprocess-$TS.txt" | cut -c1-300
ssh "$DOCKER_PRD_SSH" "docker exec marketchat_backend_prd python manage.py shell -c \"from django.urls import get_resolver; print('ROTA /media PRESENTE' if any(str(p.pattern).startswith('media') for p in get_resolver().url_patterns) else 'ROTA /media AUSENTE')\"" 2>&1 | tail -1
```

Critério: `exit=0`, 25 PASS e `ROTA /media AUSENTE`.

**P5.3 Estação:** sondas via Cloudflare, via Apache e LAN direto.

```bash
cd "$RB"
for via in cf apache; do
  HOSTS="$PRD_HOSTS" API_HOSTS="$PRD_API_HOSTS" SPA_HOSTS="$PRD_SPA_HOSTS" VIA=$via APACHE_IP=$APACHE_PRD_IP \
    CANARY_PATH=$CANARY PROBE_ID=p5$via-$TS ./sondar.sh | tee "$EVID/p5-sonda-$via-$TS.txt"
done
HOSTS="$DOCKER_PRD_IP app.marketchat.com.br" VIA=docker DOCKER_URL=$DOCKER_PRD_API \
  CANARY_PATH=$CANARY EXPECT_CANARY=404 PROBE_ID=p5lan-$TS ./sondar.sh | tee "$EVID/p5-lan-$TS.txt"
```

Critério, com 0 falhas nas três execuções:

- **Via Cloudflare e via Apache:**
  - `/media` e o canário → 403;
  - anexo anônimo e com token inválido → **401**, com `Authorization chegou ao Django (token_not_valid)`;
  - `/api/auth/me/` → 401.
- **LAN direto:** o canário → **404**. A exposição LAN acabou.

**P5.4 Front publicado:**

```bash
ssh "$DOCKER_PRD_SSH" "docker exec marketchat_frontend_prd sh -c 'ls dist/assets/index-*.js; grep -l /attachment/ dist/assets/*.js | head -3'"
curl -s https://app.marketchat.com.br/ | grep -o 'assets/index-[^"]*\.js'
```

Critério: o mesmo `index-*.js` no container e na resposta pública, e um bundle com `/attachment/`.

**P5.5 Remover o canário e fechar a janela:**

```bash
ssh "$DOCKER_PRD_SSH" "docker exec marketchat_backend_prd sh -c 'rm -f /app/media/$CANARY && rmdir /app/media/qa-canary && echo canario removido'"
date -Is    # FIM DA JANELA; registre a duração desde a P2.2
```

Avise o suporte: "Manutenção concluída. Se alguma imagem do inbox não aparecer, atualize a página (F5)."

**P5.6 Opcional: interface.** Só com um tenant **interno** da equipe, nunca com conta de cliente. No inbox, uma conversa com imagem mostra a foto, e o DevTools só mostra `GET /api/chatbot/messages/<id>/attachment/` → 200. Sem tenant interno, vale o teste de interface feito em staging.

### P6 — Acompanhamento (30–60 min)

```bash
ssh "$DOCKER_PRD_SSH" "docker logs --since 30m marketchat_backend_prd 2>&1 | grep -E 'Traceback|Internal Server Error| 500 ' | tail -20"
ssh -t "$APACHE_PRD_SSH" "sudo tail -n 50000 ACCESS_LOG_DO_VHOST \
  | awk '\$7 ~ /\/attachment\/\$|\/security-photo\/\$/ {a[\$9]++} \$7 ~ /^\/+media/ {m[\$9]++} END {for (k in a) print \"endpoints\", k, a[k]; for (k in m) print \"media\", k, m[k]}'"
rm -f /tmp/mc-deploy-4035136c/scripts/producao/env.deploy
git -C ~/Documentos/marketchat worktree remove /tmp/mc-deploy-4035136c
```

Critério:

- sem 5xx novos;
- os 401 em `/attachment/` caem em minutos: vêm de abas com o front antigo e somem com F5;
- os 403 em `/media` são tentativas bloqueadas, mas continuam úteis como sinal.

## 6. P7 — Publicar os commits (requer aprovação explícita)

Não executado. Depois de staging e produção aprovados, na estação:

```bash
git -C ~/Documentos/marketchat log --oneline origin/main..main   # exatamente os 3 commits
git -C ~/Documentos/marketchat push origin main                  # sem --force
```

O push não piora a exposição: d50fa6e9 só remove os arquivos do índice, e os blobs já estão no
histórico remoto. A purga do histórico segue em `docs/media-protecao-e-purga-historico.md`, com
decisão própria.

## 7. P8 — Acessos a `/media` desde 17/05/2026

As evidências contêm caminhos que identificam carrinhos e clientes: mantenha `chmod 600` e não
abra nenhuma imagem.

**Host Apache** (fonte principal). Use os `CustomLog` de `22-diretivas-relevantes.txt`:

```bash
scp "$RB/analisar-logs-media.py" "$APACHE_PRD_SSH:/tmp/"
ssh -t "$APACHE_PRD_SSH" "sudo bash -c 'umask 077; D=/root/mc-apache-$TS; \
  python3 /tmp/analisar-logs-media.py --since 2026-05-17 /var/log/httpd/*access*log* /var/log/apache2/*access*.log* > \$D/media-hits.csv 2> \$D/media-resumo.txt; \
  cat \$D/media-resumo.txt; \
  awk -F, \"NR>1 && \\\$5 ~ /^(200|206|304)\\\$/ {print \\\$7}\" \$D/media-hits.csv | sort -u > \$D/media-paths.txt; \
  install -m 600 -o $(id -un) \$D/media-paths.txt /tmp/media-paths-$TS.txt'"
```

Leitura do resumo:

- **"Cobertura dos logs lidos":** se começar depois de 17/05, o logrotate já descartou o início (Debian: 14 dias; RHEL: 4 semanas por padrão). Registre a lacuna e procure backup ou SIEM.
- **IP do cliente:** se forem IPs do Cloudflare, o `%h` não traz o cliente real, a menos que haja `mod_remoteip` com `CF-Connecting-IP` ou um campo extra no `LogFormat` (coluna `extra` do CSV).
- **Muitas linhas não reconhecidas:** o `LogFormat` é diferente; ajuste a regex no topo do script.

**Estação (Cloudflare):** o `cf-media-*.csv` da P0.6 cobre a retenção do plano, com `clientIP` e `cacheStatus`.

**Host Docker (Django):** o `docker logs` salvo na seção 3 só cobre desde a última recriação do container, e só registra 404.

**Impacto por tenant, sem abrir arquivos.** O arquivo sai do host Apache, passa pela estação e vai ao host Docker:

```bash
scp "$APACHE_PRD_SSH:/tmp/media-paths-$TS.txt" "$EVID/media-paths.txt" && ssh "$APACHE_PRD_SSH" "rm -f /tmp/media-paths-$TS.txt"
scp "$EVID/media-paths.txt" "$DOCKER_PRD_SSH:/tmp/media-paths.txt"
ssh "$DOCKER_PRD_SSH" "docker cp /tmp/media-paths.txt marketchat_backend_prd:/tmp/media-paths.txt && rm -f /tmp/media-paths.txt"
ssh "$DOCKER_PRD_SSH" "docker exec -i marketchat_backend_prd python manage.py shell" < "$RB/mapear-caminhos.py" > "$EVID/impacto-$TS.csv"
ssh "$DOCKER_PRD_SSH" "docker exec marketchat_backend_prd rm -f /tmp/media-paths.txt"; chmod 600 "$EVID"/impacto-*.csv
```

O `impacto-*.csv` lista, para cada caminho entregue, o modelo, o objeto, o tenant e o morador:
é o insumo para a avaliação de LGPD. `SEM_REGISTRO` indica arquivo órfão ou já removido do banco.

## 8. Rollback

Princípio: **o bloqueio de `/media` no Apache, a purga e a regra WAF ficam.** Nenhum rollback
padrão reabre a rota.

| Etapa | Gatilho | Ação padrão | Critério de retorno |
| --- | --- | --- | --- |
| **R0** P1 (sync/build/verificação) | Qualquer falha antes da P2 | Nada nos containers. Opcional: restaurar o código no host Docker (abaixo) e remover o canário | `docker ps` inalterado |
| **R1a** P2, antes do reload | `configtest` falha ou `-S` mudou | **Não recarregue.** Restaure os arquivos editados a partir de `/root/mc-apache-$TS` e remova o snippet | `configtest` OK; config em execução nunca mudou |
| **R1b** P2, depois do reload | Site **não MarketChat** afetado (Include no vhost errado) | Remova o `Include` só desse vhost; `configtest`; reload | Aquele site volta; vhosts MarketChat seguem com `bloqueio` |
| **R1c** P2, depois do reload | Problema no MarketChat fora de `/media` | Corrigir para frente, mantendo o `Include`. O bloco só nega `/media`, então a causa é outra | Sondas da P2.3 com 0 falhas |
| **R2** P5 (containers) | Smoke falha, 5xx, login ou inbox quebrado mesmo após F5 | Voltar para as imagens `marketchat-rollback/*:$TS`, **mantendo** bloqueio, purga e WAF | image ids antigos no `docker inspect`; smoke OK; sondas `EXPECT_NEW=404` com `/media` 403 |
| **R3** P4 (WAF) | Falso positivo fora de `/media` | Desabilitar a regra. O Apache continua bloqueando `/media` | Rota afetada volta |
| **R4** P4 (purga) | — | Irreversível e sem efeito colateral | — |
| **R5** P1.3/P5.2 (verificação em processo) | Execução interrompida | Nada a desfazer: a transação não commitada é abortada pelo banco quando a conexão cai. Confira com a consulta abaixo | 0 tenants `qa-inproc-*` |

**R0 / R2: restaurar o código no host Docker.**

```bash
ssh "$DOCKER_PRD_SSH" TS="$TS" 'cd ~ && mv marketchat "marketchat.falhou-$TS" && tar -xzpf "marketchat-code-$TS.tgz" -C ~'
```

**R1a: restaurar os arquivos do Apache** editados na P2 (no host Apache):

```bash
sudo tar -xzpf /root/mc-apache-$TS/arquivos-carregados.tgz -C / CAMINHO/DO/ARQUIVO/EDITADO.conf   # sem a "/" inicial
sudo rm -f "$SNIP" && sudo $CTL -t     # não recarregue: a config em execução já é a antiga
```

**R2: voltar as imagens** (no host Docker), sem tocar no Apache nem no Cloudflare:

```bash
ssh "$DOCKER_PRD_SSH" TS="$TS" bash -s <<'EOF'
set -euo pipefail
cd ~/marketchat
docker tag "marketchat-rollback/backend:$TS"  "$(docker inspect -f '{{.Config.Image}}' marketchat_backend_prd)"
docker tag "marketchat-rollback/frontend:$TS" "$(docker inspect -f '{{.Config.Image}}' marketchat_frontend_prd)"
PRODUCTION_ON_SERVER=1 bash -c 'source scripts/producao/common.sh && production_compose up -d --no-build backend frontend && sleep 6 && production_smoke_test'
cd ~ && mv marketchat "marketchat.falhou-$TS" && tar -xzpf "marketchat-code-$TS.tgz" -C ~
EOF
```

Sem migrações entre as versões, o banco não precisa de rollback.

> **Consequência documentada do R2: perda temporária de imagens.** Com os containers antigos e
> o bloqueio mantido, o front antigo volta a pedir `/media/…` e recebe 403. **As fotos do inbox e
> dos carrinhos ficam sem exibição até um novo deploy da versão corrigida.** Os arquivos seguem
> intactos no volume. Além disso, o backend antigo volta a servir `/media` **na LAN**, em
> `$DOCKER_PRD_IP:9001`; o canário daria 200 de novo. Registre o horário, avise o suporte
> ("imagens do inbox indisponíveis até nova atualização") e trate a restrição por firewall da
> pendência 4 como prioridade.

**R5: conferir que a verificação em processo não deixou nada** (no host Docker):

```bash
ssh "$DOCKER_PRD_SSH" "docker exec marketchat_backend_prd python manage.py shell -c \"from apps.tenants.models import Tenant; print(Tenant.objects.filter(slug__startswith='qa-inproc-').count())\"" 2>&1 | tail -1
```

**R3: desabilitar a regra WAF** (na estação):

```bash
cfapi -X PATCH "$CF/zones/$CF_ZONE_ID/rulesets/$RS/rules/$RULE_ID" --data '{"enabled":false}' | jq .success
```

**Excepcional, fora do procedimento padrão:** remover o bloqueio de um vhost MarketChat
reabre `/media`. Isso só acontece com aprovação explícita do responsável pelo incidente e com a
regra WAF da P4 **ativa e verificada** antes (`sondar.sh VIA=cf` com `/media` 403 e
`server=cloudflare`). Mesmo assim, o acesso direto ao Apache e à LAN ficam abertos. Registre a
decisão e o horário.

## 9. Critérios de sucesso consolidados

- [ ] **P0:**
  - tabela P0.5 completa para todos os hostnames: Cloudflare (IP ou túnel e service), host Apache, vhost (arquivo:linha, porta), destino no host Docker e probe achado no log;
  - descobertas das duas máquinas salvas;
  - retenção do Cloudflare conhecida.
- [ ] **Backups por máquina** com `SHA256SUMS`; imagens `marketchat-rollback/*:$TS` criadas antes do build.
- [ ] **Staging:** P1 a P6 com 0 falhas; `verificar-midia.sh` com 0 falhas via Cloudflare e via Apache; imagem QA visível no inbox; cleanup `restantes=0`; janela P2→P5 dentro do alvo.
- [ ] **P1:** rsync sem mudanças inexplicadas; build OK; `qa_media_inprocess.py` na imagem nova com 25 PASS; bundle novo com `/attachment/`; canário criado; containers intactos.
- [ ] **P2:** `Syntax OK`, `-S` inalterado, graceful sem erros; `bloqueio` em todos os vhosts MarketChat; sondas cf e apache com 0 falhas (`/media` e canário 403).
- [ ] **P3:** exposição LAN registrada (canário 200 com a imagem antiga) e origens que alcançam `:9001` anotadas; destino do Apache respondendo 401.
- [ ] **P4:** purga `success`; sondas cf sem `HIT`; regra WAF ativa, se aprovada.
- [ ] **P5:**
  - smoke OK; verificação em processo com 25 PASS; `ROTA /media AUSENTE`;
  - sondas cf e apache com 0 falhas e `token_not_valid`; LAN com canário 404;
  - bundle público igual ao do container; canário removido; duração da janela registrada.
- [ ] **P6:** sem 5xx novos; 401 em `/attachment/` caindo.
- [ ] **P8:** relatório com período coberto, lacunas, contagem por status e `impacto-*.csv` por tenant.

## 10. Pendências para revisão

1. **Host Apache de produção e de staging:** nenhum dos dois está versionado. A P0 precisa identificá-los antes de qualquer mudança.
2. **Hostnames:** `api.marketchat.com.br`, o apex e `www`. Confirmar o papel de cada um (API, SPA ou redirect) e ajustar `*_API_HOSTS`/`*_SPA_HOSTS`. Qualquer outro registro que aponte para as mesmas origens entra no bloqueio, na purga e na regra WAF.
3. **SSL do Cloudflare:** se for `flexible`, o bloqueio entra também nos vhosts `:80` e as sondas usam `SCHEMES="https http"`.
4. **Portas 9001/3000 em `0.0.0.0` no host Docker:** com o Apache em outra máquina, publicar só em `127.0.0.1` quebraria o proxy. A proposta é restringir por firewall (cadeia `DOCKER-USER`, porque as regras de `firewalld`/INPUT não se aplicam a portas publicadas pelo Docker), liberando só o IP do host Apache. Mudança fora deste runbook, com aprovação própria. Com o backend novo, `/media` não existe mais; a restrição reduz a superfície da API.
5. **Origem acessível sem o Cloudflare:** verificar se o Apache aceita conexões de IPs que não são do Cloudflare (`06-conexoes.txt` e firewall do host Apache). Se aceitar, a regra WAF não protege esse caminho; o bloqueio no Apache protege.
6. **`qa_media_inprocess.py` com as settings reais:** foi validado com settings de teste e de staging. A primeira execução com `config.settings.production` acontece no ensaio de staging, se staging usar essas settings, ou na P1.3; ela aborta sem criar nada se o storage ou a rede não estiverem como esperado.
7. **Retenção dos logs:** logs do Apache e do Cloudflare anteriores à retenção podem não existir. Procurar backup ou SIEM antes que a lacuna aumente; a seção 3 congela o que existe hoje.
8. **Push dos 3 commits** e, separadamente, a decisão sobre a purga do histórico Git.
