# Rotas da API (base: `/api`)

Todas as URLs abaixo são relativas ao host do backend (ex.: `http://127.0.0.1:8001` em dev local; a porta 8000 costuma estar ocupada pelo Portainer).

## Autenticação (`/api/auth/`)

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| POST | `/api/auth/register/` | Nenhuma | Cadastro de novo tenant + usuário administrador + cartão (trial Asaas). |
| GET | `/api/auth/me/` | JWT | Dados do usuário logado, tenant e `billing_blocked` (sempre acessível, mesmo com cobrança em atraso). |
| POST | `/api/auth/token/` | Nenhuma | Login (JWT access + refresh). Inclui `tenant_id` no payload do access token. |
| POST | `/api/auth/token/refresh/` | Refresh token | Renova o access token. |
| POST | `/api/auth/password/change/` | JWT | Troca de senha (senha atual + nova). |
| POST | `/api/auth/password/reset/` | Nenhuma | Solicita e-mail de recuperação (corpo com link para o front). |
| POST | `/api/auth/password/reset/confirm/` | Nenhuma | Confirma nova senha com `uid`, `token` e `new_password`. |

## Configurações — conta (`/api/settings/account/`)

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| GET | `/api/settings/account/` | JWT | Dados do usuário logado e da empresa (tenant). |
| PATCH | `/api/settings/account/` | JWT | Atualiza perfil (`first_name`, `last_name`, `phone`). Admin do tenant pode alterar `tenant_name`, `tenant_phone` e definir `cpf_cnpj` **uma vez**; após cadastro, CPF/CNPJ é somente leitura. |

Corpo PATCH (campos opcionais): `first_name`, `last_name`, `phone`, `tenant_name`, `tenant_phone`, `cpf_cnpj`.

Acessível mesmo com cobrança em atraso (bypass do middleware 402).

## Configurações — cobrança (`/api/settings/billing/`)

Requer JWT e `is_tenant_admin=True`.

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| GET | `/api/settings/billing/history/` | JWT + admin tenant | Histórico de cobranças no Asaas (cache 5 min). |
| GET | `/api/settings/billing/payment-method/` | JWT + admin tenant | Forma de pagamento atual da assinatura. |
| POST | `/api/settings/billing/payment-method/` | JWT + admin tenant | Atualiza cartão da assinatura (`credit_card`, `credit_card_holder`). |

Resposta do histórico (`results[]`): `due_date`, `value`, `status` (`PAID`, `PENDING`, `OVERDUE`), `billing_type`, `invoice_url`.

Acessível mesmo com cobrança em atraso (bypass do middleware 402).

## Cobrança (`/api/billing/`)

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| POST | `/api/webhooks/asaas/` | Igual à rota em billing. | Webhook Asaas (Pix de carrinho + assinatura SaaS). Em dev local o Asaas **não alcança** `localhost` — use túnel (ngrok) na URL do webhook ou `python manage.py sync_pending_cart_payments` após confirmar no sandbox. |
| POST | `/api/billing/webhooks/asaas/` | Se `ASAAS_WEBHOOK_VERIFY=True`: header `X-Webhook-Token` = `ASAAS_WEBHOOK_TOKEN`. Em dev (`ASAAS_WEBHOOK_VERIFY=False`) o corpo é aceito sem esse header. | Mesmo handler: `PAYMENT_RECEIVED`/`PAYMENT_CONFIRMED` (carrinho), `PAYMENT_OVERDUE`/`PAYMENT_DELETED` (Pix expirado), assinatura (`PAYMENT_CONFIRMED`, `PAYMENT_OVERDUE`, `SUBSCRIPTION_DELETED`). |

## Produtos (`/api/products/`)

Requer JWT (`IsAuthenticated`). Dados isolados por `tenant_id` do usuário logado.

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| GET | `/api/products/` | JWT | Lista produtos do tenant. Query opcional: `name`, `sku`, `status` (`active` \| `inactive`). |
| PATCH | `/api/products/<id>/` | JWT | Atualização rápida: apenas `name`, `price`, `status`. |
| GET | `/api/products/download-template/` | JWT | Download do modelo `.xlsx` (colunas: `sku`, `name`, `search_aliases`, `price`, `status`). |
| POST | `/api/products/upload-preview/` | JWT | Upload multipart (`file`: `.xlsx` ou `.csv`). Compara por SKU e retorna resumo sem gravar. |
| POST | `/api/products/upload-confirm/` | JWT | Confirma importação com o token do preview. |

### Fluxo de importação

1. `GET /api/products/download-template/` — baixar modelo.
2. `POST /api/products/upload-preview/` — enviar planilha preenchida.

Corpo multipart: campo `file`.

Resposta 200:

```json
{
  "new_count": 2,
  "updated_count": 1,
  "import_token": "uuid-da-sessao"
}
```

- **Novo:** SKU inexistente no tenant.
- **Alterado:** SKU existente com diferença em `name`, `search_aliases`, `price` ou `status`.
- Linhas idênticas ao banco são ignoradas.
- SKUs duplicados na planilha: mantém a primeira ocorrência.

3. `POST /api/products/upload-confirm/` — efetivar em transação atômica.

```json
{ "import_token": "uuid-da-sessao" }
```

Resposta 200:

```json
{
  "created": 2,
  "updated": 1,
  "import_token": "uuid-da-sessao"
}
```

Erros: `400` (planilha inválida), `404` (token inválido/expirado), `409` (token já confirmado). Token expira em 2 horas.

### Status na planilha

Valores aceitos para `status`: `Ativo` / `Inativo` (também `active`, `inactive`, `1`, `0`, `sim`, `não`, etc.).

## Mercados (`/api/markets/`)

Requer JWT (`IsAuthenticated`). Dados isolados por `tenant_id` do usuário logado.

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| GET | `/api/markets/` | JWT | Lista mercados do tenant. Query opcional: `name`, `address`, `status` (`active` \| `inactive`). |
| POST | `/api/markets/` | JWT | Cadastra mercado no tenant atual. |
| GET | `/api/markets/<id>/` | JWT | Detalhe de um mercado do tenant. |
| PATCH | `/api/markets/<id>/` | JWT | Atualização parcial: `name`, `address`, `status`. |
| PUT | `/api/markets/<id>/` | JWT | Atualização completa: `name`, `address`, `status`. |
| DELETE | `/api/markets/<id>/` | JWT | Remove mercado (hard delete). |

Corpo POST/PUT: `name` (obrigatório), `address` (obrigatório), `status` opcional (`active` ou `inactive`, padrão `active`).

Mercados de outro tenant retornam **404** em GET/PATCH/PUT/DELETE.

## Integrações — Pix / subconta Asaas (`/api/integrations/pix/`)

Requer JWT. Escrita (`PUT`) exige administrador do tenant (`IsTenantAdmin`).

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| GET | `/api/integrations/pix/` | JWT | Configuração Pix/subconta do tenant + `prefill` (dados do tenant/usuário) + `has_market_address`. |
| PUT | `/api/integrations/pix/` | JWT + admin tenant | Salva dados Pix; se ainda não houver `asaas_wallet_id`, cria subconta no Asaas (`POST /v3/accounts`) usando endereço do primeiro mercado cadastrado. |

Corpo PUT: `name`, `email`, `cpf_cnpj`, `pix_key_type` (`CPF`, `CNPJ`, `EMAIL`, `PHONE`, `RANDOM`), `pix_key`.

Resposta inclui: `asaas_wallet_id`, `account_status` (`PENDING`, `APPROVED`, `REJECTED`), `has_wallet`, `has_market_address`, `can_manage`.

Erros: `400` (sem mercado com endereço válido, falha Asaas com `detail` em português).

Variável de ambiente: `ASAAS_SUBACCOUNT_INCOME_VALUE` (faturamento mensal enviado ao Asaas na criação da subconta; padrão `5000`).

## Chatbot — fluxos visuais (`/api/chatbot/`)

Requer JWT. O `flow_data` segue o formato React Flow (`nodes`, `edges`, `viewport` opcional).

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| GET | `/api/chatbot/workflows/` | JWT | Lista fluxos do tenant (`id`, `name`, `is_active`, `is_system`, `system_key`, timestamps). Inclui 5 fluxos padrão (`is_system=true`) criados no cadastro do tenant. |
| GET | `/api/chatbot/workflows/active/` | JWT | Retorna o fluxo ativo com `flow_data` completo (404 se não houver). |
| GET | `/api/chatbot/workflows/<id>/` | JWT | Detalhe do fluxo com `flow_data` completo. |
| PATCH | `/api/chatbot/workflows/<id>/` | JWT | Atualiza `name` e/ou `is_active` do fluxo informado (vários fluxos podem estar ativos ao mesmo tempo). `name` bloqueado se `is_system=true` (403). |
| DELETE | `/api/chatbot/workflows/<id>/` | JWT | Remove fluxo customizado. Bloqueado se `is_system=true` (403). |
| POST | `/api/chatbot/workflows/<id>/duplicate/` | JWT | Duplica fluxo como `Cópia de {nome}` (inativo). |
| POST | `/api/chatbot/workflows/save/` | JWT | Salva ou atualiza fluxo (`id?`, `name?`, `is_active?`, `flow_data`). Upsert atômico. |

Tipos de nó permitidos: `trigger`, `ai_filter`, `response`, `owner_alert`. Arestas de `ai_filter` podem incluir `data.intent` para roteamento.

Classificação de intenção no webhook usa serviço de IA no servidor (variáveis `OPENAI_API_KEY`, `OPENAI_MODEL` — não expostas ao usuário final).

## Moradores (`/api/residents/`)

Requer JWT (`IsAuthenticated`). Dados isolados por `tenant_id` do usuário logado.

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| GET | `/api/residents/` | JWT | Lista moradores cadastrados (com mercado vinculado). Query opcional: `market_id`, `name` (parcial, case-insensitive), `phone` (dígitos, parcial no número). |
| GET | `/api/residents/markets/` | JWT | Lista mercados ativos (id, name) para filtro e edição. |
| PATCH | `/api/residents/<id>/` | JWT | Altera manualmente o `market_id` vinculado ao morador. |

Corpo PATCH: `{ "market_id": 1 }`.

O cadastro inicial de moradores ocorre via fluxo WhatsApp (webhook Evolution); ver máquina de estados em `apps/residents/services/onboarding_flow.py`.

### Compra via WhatsApp (carrinho + Pix)

Processado no webhook Evolution (`POST /api/integrations/webhooks/evolution/`) para moradores com cadastro concluído, **antes** do motor visual do chatbot.

No estado `ACTIVE_BOT`, a **triagem de intenção** (`intent_gatekeeper`) classifica a mensagem (`MAINTENANCE_ISSUE`, `PAYMENT_ERROR`, `PURCHASE`, `STOCK_ISSUE`, `GENERAL`) antes de qualquer busca no catálogo. Apenas `PURCHASE` dispara o fluxo de carrinho. Respostas com IA (`GENERAL`, `STOCK_ISSUE`) incluem `Resident.name` e `Market.name` no system prompt. `PAYMENT_ERROR` alerta o dono, oferece compra via Pix no WhatsApp e move a sessão para `AWAITING_PRODUCT_SELECTION`. `MAINTENANCE_ISSUE` mantém apenas o chamado de suporte.

Estados `ChatSession`: `ACTIVE_BOT`, `AWAITING_PRODUCT_SELECTION`, `AWAITING_QUANTITY`, `AWAITING_LOOP_DECISION`, `AWAITING_PHOTO`.

Modelos em `apps/sales`: `Cart` (`OPEN`, `AWAITING_PHOTO`, `AWAITING_PAYMENT`, `COMPLETED`), `CartItem`.

Dependências: `OPENAI_API_KEY` / `OPENAI_MODEL` (extração do termo de produto), subconta Asaas do tenant com `asaas_wallet_id`, `MEDIA_ROOT` (foto do carrinho), Evolution GO (`/send/text` para o fluxo de venda; catálogo e carrinho em mensagens de texto numeradas — sem carrossel/lista/botões nativos, por compatibilidade com todas as versões do WhatsApp).

## Notificações do painel (`/api/notifications/`)

Alertas em tempo real gerados quando o gatekeeper trata incidentes críticos (`PAYMENT_ERROR`, `MAINTENANCE_ISSUE`).

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| GET | `/api/notifications/latest/` | JWT | Últimas 5 notificações não lidas do tenant + `unread_count` total. |
| POST | `/api/notifications/<id>/read/` | JWT | Marca uma notificação como lida (somente do tenant do usuário). |
| POST | `/api/notifications/read-all/` | JWT | Marca todas as notificações não lidas do tenant como lidas. |

Resposta `GET latest`: `{ "unread_count": number, "results": [{ "id", "title", "message", "severity", "is_read", "created_at", "market_id", "market_name", "intent_type" }] }`.

Resposta `POST read-all`: `{ "marked_read": number }`.

## Onboarding gamificado (`/api/onboarding/`)

Jornada de setup (4 missões). O `GET status` sincroniza automaticamente o progresso com mercados, pelo menos um produto cadastrado, WhatsApp conectado e primeiro pedido concluído com foto de auditoria.

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| GET | `/api/onboarding/status/` | JWT | Status das missões, `completed_count`, `completion_percent`, `show_mission_panel`. |
| POST | `/api/onboarding/dismiss/` | JWT | Marca `onboarding_finished=true` (exige 100% das missões). |

Resposta `GET status`: `{ "step_market_created", "step_product_created", "step_whatsapp_connected", "step_test_order_completed", "onboarding_finished", "completed_count", "completion_percent", "show_mission_panel" }`.

## Exemplo multi-tenant (`/api/`)

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| GET | `/api/demo-notes/` | JWT | Lista notas de demonstração do tenant do usuário. |
| POST | `/api/demo-notes/` | JWT | Cria nota de demonstração no tenant atual. |

## Bloqueio por billing (middleware)

Quando o tenant está com acesso suspenso por cobrança, a maioria das rotas autenticadas em `/api/` responde **402 Payment Required** com corpo JSON `{"detail": "..."}` (exceto bypass: registro, token, `me`, reset de senha, `/api/settings/account`, `/api/settings/billing`, webhook Asaas). O front-end pode redirecionar o usuário para a página de cobrança ao receber 402.

## Admin Django

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| * | `/admin/` | Sessão staff | Painel administrativo padrão. |
