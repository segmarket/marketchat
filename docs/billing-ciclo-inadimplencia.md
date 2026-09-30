# Ciclo de inadimplência da assinatura SaaS

Escopo: assinatura do MarketChat cobrada no Asaas (cartão de crédito recorrente). O fluxo Pix
dos carrinhos (`apps/sales/services/asaas_payment_webhook.py`) não foi alterado e continua
sendo avaliado antes do ramo de assinatura em `process_asaas_webhook_payload`.

## 1. Regras

| Situação | Regra |
|----------|-------|
| Cobrança vencida ou cartão recusado | A cobrança `pay_…` vira **exigida** (`SubscriptionCharge.overdue_at`). Tenant ACTIVE/TRIAL → OVERDUE; SUSPENDED continua SUSPENDED; CANCELED não muda. |
| Pagamento confirmado | Só quita a cobrança `pay_…` informada. O acesso volta apenas se ela era exigida **e** não resta outra exigida. |
| Evento antigo, repetido ou fora de ordem | Sem efeito: pagamento é estado terminal da cobrança; `PAYMENT_OVERDUE` depois do pagamento é ignorado; `PAYMENT_RECEIVED` que chega ~32 dias após o `PAYMENT_CONFIRMED` (cartão) não reativa o ciclo seguinte. |
| Evento sem `payment.id` | Pode marcar atraso (conservador); nunca libera acesso. |
| Tenant CANCELED | Evento de pagamento nunca reativa. Só o fluxo "Reativar" (que recusa quem cancelou com fatura em atraso). |
| Troca de cartão | `PUT /subscriptions/{id}/creditCard` não cobra nada (documentação Asaas). Não libera acesso. |
| Regularização | `POST /api/settings/billing/regularize/`: troca o cartão, **consulta** cada cobrança exigida e paga com `POST /payments/{id}/payWithCreditCard`. Acesso volta só com status CONFIRMED/RECEIVED dessa cobrança. |
| Carência | Única regra em `apps/tenants/billing_rules.py`: em carência enquanto `agora < overdue_since + BILLING_GRACE_DAYS`; suspende a partir desse instante. Painel, bot, `check_subscriptions`, `/api/auth/me` (`grace_ends_at`) e UI usam a mesma função. |
| CANCELED após o trial | Sem painel e sem bot (`Tenant.has_messaging_access`); `check_subscriptions` grava `billing_blocked_at` e agenda o logout. Status continua CANCELED (reativável). |
| Suspensão | Bloqueio local imediato (status, `billing_blocked_at`, carrinhos/sessões). O logout Evolution é etapa separada, pendente até confirmar. |

## 2. Contrato Asaas usado

Fontes: [estrutura dos eventos](https://docs.asaas.com/docs/eventos-de-webhooks),
[webhook de cobranças](https://docs.asaas.com/docs/webhook-para-cobrancas),
[pagar cobrança com cartão](https://docs.asaas.com/reference/pagar-uma-cobranca-com-cartao-de-credito).

Envelope (entrega **at-least-once**, pode repetir e chegar fora de ordem):

```json
{
  "id": "evt_05b708f961d739ea7eba7e4db318f621&368604920",
  "event": "PAYMENT_RECEIVED",
  "dateCreated": "2024-06-12 16:45:03",
  "payment": {
    "id": "pay_080225913252",
    "subscription": "sub_VXJBYgP2u0eO",
    "dueDate": "2021-01-01",
    "originalDueDate": "2021-01-01",
    "value": 100,
    "status": "RECEIVED",
    "confirmedDate": "2021-01-01",
    "paymentDate": "2021-01-01",
    "billingType": "CREDIT_CARD",
    "deleted": false
  }
}
```

Campos consumidos: `id` do evento (idempotência), `event`, `dateCreated` (fuso da conta,
America/Sao_Paulo), `payment.id`, `payment.subscription`, `dueDate`, `originalDueDate`
(competência), `value`, `status`. Eventos tratados na assinatura:

- quitação: `PAYMENT_CONFIRMED`, `PAYMENT_RECEIVED` (com `status` em CONFIRMED/RECEIVED/RECEIVED_IN_CASH);
- cobrança exigida: `PAYMENT_OVERDUE`, `PAYMENT_CREDIT_CARD_CAPTURE_REFUSED`. Os nomes
  `PAYMENT_REJECTED`/`REFUSED`/`FAILED` não existem na documentação, mas continuam aceitos
  por compatibilidade;
- `PAYMENT_DELETED` (cobrança removida, deixa de ser exigida; **não** libera acesso);
- `SUBSCRIPTION_DELETED`/`SUBSCRIPTION_CANCELED` (comportamento anterior mantido).

`payWithCreditCard`: corpo `{"creditCardToken": "..."}`. A documentação orienta consultar a
cobrança antes de pagar e após timeout, sem retentativa automática. O serviço faz
`GET /payments/{id}` antes e, em timeout, consulta de novo e responde "resultado incerto"
sem repetir.

## 3. Identificação persistente e idempotência

- `billing.SubscriptionCharge`: uma linha por `asaas_payment_id` (único), com
  `asaas_subscription_id`, `due_date`, `original_due_date` (competência), `value`,
  `asaas_status`, `overdue_at` (exigida desde), `paid_at`, `removed_at`, `last_event`.
- `billing.AsaasWebhookEvent`: `event_key` único, que é o `id` do evento (`evt_…`) ou
  `sha256` do corpo quando o `id` não vier, mais `outcome` e `processed_at`. Evento já
  processado é descartado. Em caso de exceção a transação é revertida e o Asaas reenvia.
- O processamento de cada evento roda numa transação com `select_for_update` no tenant e na
  assinatura.
- Tenants que já estavam OVERDUE/SUSPENDED antes do ledger não têm cobrança exigida registrada.
  Um pagamento desses tenants só libera o acesso se `GET /payments?subscription=…&status=OVERDUE`
  vier vazio. Se vier com itens, eles passam a ser exigidos; se o Asaas falhar, nada é liberado.

## 4. Logout Evolution com retry observável

Campos em `Tenant`: `whatsapp_logout_pending_since`, `whatsapp_logout_attempts`,
`whatsapp_logout_last_attempt_at`, `whatsapp_logout_last_error` (visíveis no admin).

- A suspensão grava a pendência junto com o bloqueio local; falha no logout não desfaz nada.
- O middleware do painel não chama mais a Evolution: quem passa da carência é suspenso
  localmente na request e o logout fica para o `check_subscriptions`.
- `check_subscriptions` executa três etapas: suspensões, bloqueio de CANCELED após o trial e
  retry dos logouts pendentes. Cada falha sai no stderr como
  `Logout Evolution pendente: tenant_id=… tentativas=… ultimo_erro=…`, e há um log
  `WARNING` equivalente.
- Se o tenant se regularizar antes do logout, a pendência é descartada. Se o logout já tiver
  ocorrido, basta reconectar pelo QR Code; a instância não é removida.

## 5. Agendamento do `check_subscriptions` em produção — **NÃO VERIFICADO**

O que o repositório mostra:

- `docker-compose.production.yml` tem apenas os serviços `backend` (Gunicorn) e `frontend`,
  sem serviço de agendamento;
- `docker/entrypoint.sh` roda migrate, collectstatic e Gunicorn, sem cron no container;
- a única referência é o comentário "cron diário às 02:00" no próprio comando.

Logo, se o comando roda hoje, é por crontab ou timer systemd no **host Docker**, fora do Git.
Sem acesso ao servidor, isso não foi verificado. Os comandos abaixo, todos somente leitura,
devem ser executados no host do backend (container `marketchat_backend_prd`):

```bash
# 1) Agendamentos no host
crontab -l 2>/dev/null; sudo crontab -l 2>/dev/null
sudo grep -RIn "check_subscriptions\|manage.py" /etc/crontab /etc/cron.d /etc/cron.hourly \
  /etc/cron.daily /var/spool/cron 2>/dev/null
systemctl list-timers --all 2>/dev/null | grep -Ei "marketchat|subscri|manage" || true
sudo grep -RIl "check_subscriptions" /etc/systemd/system /usr/lib/systemd/system 2>/dev/null

# 2) Agendamento dentro do container (não esperado)
docker exec marketchat_backend_prd sh -c 'ls /etc/cron* 2>/dev/null; ps aux | grep -i [c]ron'

# 3) Evidência de execução
sudo journalctl --since "7 days ago" 2>/dev/null | grep -i check_subscriptions | tail -20
sudo grep -RIn "check_subscriptions\|Nenhum tenant elegível\|suspenso(s)" /var/log/syslog* \
  /var/log/cron* /var/log/marketchat* 2>/dev/null | tail -20

# 4) Evidência indireta no banco: com cron diário, estes números deveriam ser ~0
docker exec marketchat_backend_prd python manage.py shell -c "
from datetime import timedelta as td
from django.utils import timezone as tz
from apps.tenants.models import Tenant as T
n = tz.now()
print('TRIAL vencido ha >1d:', T.objects.filter(subscription_status='TRIAL', trial_ends_at__lt=n - td(days=1)).count())
print('OVERDUE ha >4d:', T.objects.filter(subscription_status='OVERDUE', overdue_since__lt=n - td(days=4)).count())
"

# 5) O que o comando faria agora (código atualmente em produção; não altera nada)
docker exec marketchat_backend_prd python manage.py check_subscriptions --dry-run
```

Como interpretar: sem entrada em (1)/(2) e com contagens > 0 em (4), o comando não está
agendado.

**Staging (implementado):** serviço `scheduler` no `docker-compose.yml`
(`marketchat_scheduler_staging`), com a mesma imagem e o mesmo `.env.staging` do backend. O
`docker/scheduler.sh` espera o banco estar migrado (`migrate --check`), roda o
`check_subscriptions` na subida e depois a cada `CHECK_SUBSCRIPTIONS_INTERVAL_SECONDS` (padrão
3600). Sobe com `deploy-full.sh` e `deploy-backend.sh`. Acompanhar:

```bash
docker logs -f marketchat_scheduler_staging
```

**Produção (proposto, após validar em staging):** o mesmo serviço no
`docker-compose.production.yml`, ou um cron no host com trava contra execução simultânea:

```cron
# /etc/cron.d/marketchat-billing (host Docker)
17 * * * * root flock -n /run/marketchat-check-subscriptions.lock docker exec marketchat_backend_prd python manage.py check_subscriptions >> /var/log/marketchat/check_subscriptions.log 2>&1
```

Monitorar "Logout Evolution pendente" e "E-mail de suspensão pendente" na saída.

### E-mail de suspensão

A suspensão pela request (primeira chamada ao painel após a carência) não envia e-mail nem faz
rede. `Tenant.billing_suspension_notified_at` registra o envio; o aviso fica pendente enquanto for
nulo ou anterior ao `billing_blocked_at` atual, então uma nova suspensão após regularizar gera novo
e-mail. O `check_subscriptions` envia os pendentes (e reenvia no ciclo seguinte se o SMTP falhar) e
os lista no `--dry-run`. A migração `tenants.0011` marca como avisados os tenants já suspensos no
deploy: ninguém recebe e-mail retroativo.

## 6. Deploy (não executado)

1. As migrações `billing.0004_subscription_charge_ledger` e
   `tenants.0010_tenant_whatsapp_logout_retry` são aditivas e rodam no boot (`entrypoint.sh`).
2. Antes de ligar o agendamento, rodar `check_subscriptions --dry-run` com o código novo. A
   etapa nova bloqueia **todos os CANCELED com trial encerrado e sem `billing_blocked_at`**
   (quem cancelou durante o trial). Revise essa lista.
3. Publicar backend e front juntos: a tela de bloqueio passa a usar `/regularize/`, e o front
   antigo continuaria chamando só a troca de cartão.

## 7. Simulação reproduzível em QA (`qa_billing_delinquency`)

Somente staging + Asaas sandbox. O comando recusa `ASAAS_API_URL` fora de
`https://api-sandbox.asaas.com`, chave sem prefixo de sandbox ou com prefixo de produção, e
qualquer host de produção nas configurações. Ações que alteram estado exigem `--confirm-slug`
igual ao slug do tenant e aceitam `--dry-run`; `diagnose`, `validate` e `replay-webhook` não
gravam nada (as chamadas HTTP e o teste do bot rodam dentro de transação revertida).

### Pré-requisitos

- Staging com este código (migrações `billing.0004`, `billing.0005_qa_billing_snapshot`,
  `tenants.0010`) e o front correspondente.
- Um tenant **fictício** com assinatura no sandbox atual, admin ativo e, para o teste real do bot,
  instância WhatsApp de teste conectada; e um segundo tenant ativo como controle.
- Webhook do sandbox apontando para a URL **pública** do staging
  (`https://staging-api.marketchat.com.br/api/webhooks/asaas/`), com `PAYMENT_OVERDUE` e
  `PAYMENT_CONFIRMED`. O `diagnose` lista os webhooks e acusa fila interrompida.
- O e-mail de suspensão vai para o admin do tenant fictício; use um endereço de teste.
- Se o staging tiver `check_subscriptions` agendado, ele pode suspender o tenant e repetir o
  logout Evolution pendente por conta própria; isso é esperado e não altera o roteiro.

### Comandos (no host de QA)

```bash
qa() { docker exec marketchat_backend_staging python manage.py qa_billing_delinquency "$@"; }

# 0. Escolher os tenants (id, slug, status, assinatura)
docker exec marketchat_backend_staging python manage.py shell -c "
from apps.billing.models import Subscription
for s in Subscription.objects.select_related('tenant').order_by('tenant_id'):
    print(s.tenant_id, s.tenant.slug, s.tenant.subscription_status, s.asaas_subscription_id)"
T=<id do tenant fictício>; S=<slug do tenant fictício>; C=<id do tenant de controle>

# 1. Diagnóstico: estado, fim da carência, cobranças exigidas, cliente/assinatura/webhooks no sandbox
qa diagnose --tenant-id $T

# 2. Preparar duas cobranças PENDING da assinatura (se o diagnose listar menos de duas elegíveis)
qa generate-charges --tenant-id $T --confirm-slug $S --until AAAA-MM --dry-run
qa generate-charges --tenant-id $T --confirm-slug $S --until AAAA-MM
qa diagnose --tenant-id $T                     # anote PAY_A e PAY_B em "Elegíveis"

# 3. Vencimento integrado: sandbox marca OVERDUE e o webhook real coloca o tenant em carência
qa force-overdue --tenant-id $T --confirm-slug $S --payment-id $PAY_A --dry-run
qa force-overdue --tenant-id $T --confirm-slug $S --payment-id $PAY_A --wait 180
qa force-overdue --tenant-id $T --confirm-slug $S --payment-id $PAY_B --wait 180
qa validate --tenant-id $T --expect grace --control-tenant-id $C

# 4. Antecipar a carência só deste tenant (salva snapshot; status continua OVERDUE).
#    Feche as abas do painel desse tenant antes: qualquer request dele após a carência suspende
#    na hora (has_panel_access → ensure_billing_state, sem logout e com e-mail pendente), e o
#    run-check passa a fazer só o e-mail e a 1ª tentativa de logout. Com o scheduler ativo, ele
#    também pode rodar o check_subscriptions (logout Evolution real) entre os passos.
qa advance-grace --tenant-id $T --confirm-slug $S --ends-in-minutes 0 --dry-run
qa advance-grace --tenant-id $T --confirm-slug $S --ends-in-minutes 0

# 5. Suspensão pelo check_subscriptions, com falha simulada do logout Evolution
qa run-check --tenant-id $T --confirm-slug $S --dry-run
qa run-check --tenant-id $T --confirm-slug $S --simulate-logout-failure
qa validate --tenant-id $T --expect blocked --control-tenant-id $C

# 6. UI: trocar só o cartão (roteiro abaixo, passo U3) e confirmar que segue bloqueado
qa validate --tenant-id $T --expect blocked

# 7. Pagar 1 de 2 faturas: confirmação no sandbox + webhook real; segue bloqueado
qa confirm-payment --tenant-id $T --confirm-slug $S --payment-id $PAY_A --wait 180
qa validate --tenant-id $T --expect blocked

# 8. Webhook duplicado e fora de ordem não alteram estado
qa replay-webhook --tenant-id $T --mode duplicate --payment-id $PAY_A
qa replay-webhook --tenant-id $T --mode stale --payment-id $PAY_A

# 9. Quitar a última fatura: pela UI (passo U4) ou pelo sandbox
qa confirm-payment --tenant-id $T --confirm-slug $S --payment-id $PAY_B --wait 180
qa validate --tenant-id $T --expect active --control-tenant-id $C
```

Para abandonar o cenário antes de quitar as faturas:
`qa restore --tenant-id $T --confirm-slug $S --dry-run` e depois sem `--dry-run`. O restore é
recusado se alguma cobrança do snapshot já foi paga ou removida e não reverte o Asaas nem um
logout Evolution já executado. Cada ação termina com erro (código ≠ 0) se alguma verificação
falhar.

### Roteiro pela UI (login com o admin do tenant fictício)

- **U1 — carência (após o passo 3):** faixa amarela "Aviso de cobrança… Pague a fatura em aberto
  até <data/hora>"; o painel funciona; o link "Pagar fatura em Configurações" abre
  `/admin/settings?tab=plan` com o status "Em carência".
- **U2 — bloqueio (após o passo 5):** recarregar qualquer tela do painel redireciona para
  `/admin/billing-blocked` ("Acesso suspenso por pendência financeira") com as faturas exigidas.
  Sair e entrar de novo funciona e cai na mesma tela. Com o controle logado em outra janela, o
  painel dele segue normal.
- **U3 — troca de cartão (passo 6):** `/admin/settings?tab=plan` → "Alterar cartão de crédito" →
  cartão de teste do sandbox (documentação Asaas; não anote o número). O cartão é salvo, mas o
  painel continua redirecionando para `/admin/billing-blocked`.
- **U4 — regularização (passo 9, alternativa ao `confirm-payment`):** em `/admin/billing-blocked`,
  "Pagar fatura e reativar" com cartão de teste do sandbox. O painel volta após a confirmação.
- **Bot (opcional, confirmação real):** com o tenant suspenso e a instância ainda conectada (logout
  simulado como falho), enviar uma mensagem de outro número para o WhatsApp de teste: nenhuma
  resposta. Após o passo 9, a mesma mensagem é respondida (se um `check_subscriptions` agendado
  repetir o logout pendente antes disso, a instância precisa ser reconectada pelo QR Code).

### O que é simulado e o que é confirmado pelo sandbox

| Etapa | Origem |
| --- | --- |
| Cliente, assinatura, cobranças e webhooks existem | Sandbox (`[SANDBOX]` no diagnose) |
| Cobrança vencida e tenant em carência | Sandbox: `/sandbox/payment/{id}/overdue` + webhook real processado |
| Fim da carência | Simulado: `overdue_since` e `overdue_at` do tenant deslocados (snapshot) |
| Suspensão | Código real: `check_subscriptions --tenant-id` ou a 1ª request do tenant após a carência |
| Falha do logout Evolution | Simulada (`--simulate-logout-failure`); pendência gravada pelo código real |
| 402, rotas liberadas e bloqueio do bot | Código real, chamado em processo e revertido (`validate`) |
| Troca de cartão | Sandbox, pela UI |
| Pagamento parcial e quitação | Sandbox: `/sandbox/payment/{id}/confirm` ou pagamento pela UI + webhook real |
| Webhook duplicado / fora de ordem | Simulado: evento reenviado ao processador real em transação revertida (`[SIMULADO]`) |
