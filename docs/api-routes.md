# Rotas da API (base: `/api`)

Todas as URLs abaixo são relativas ao host do backend (ex.: `http://127.0.0.1:8000`).

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

## Cobrança (`/api/billing/`)

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| POST | `/api/billing/webhooks/asaas/` | Se `ASAAS_WEBHOOK_VERIFY=True`: header `X-Webhook-Token` = `ASAAS_WEBHOOK_TOKEN`. Em dev (`ASAAS_WEBHOOK_VERIFY=False`) o corpo é aceito sem esse header. | Webhook Asaas (`PAYMENT_CONFIRMED`, `PAYMENT_OVERDUE`, `SUBSCRIPTION_DELETED`). |

## Exemplo multi-tenant (`/api/`)

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| GET | `/api/demo-notes/` | JWT | Lista notas de demonstração do tenant do usuário. |
| POST | `/api/demo-notes/` | JWT | Cria nota de demonstração no tenant atual. |

## Bloqueio por billing (middleware)

Quando o tenant está com acesso suspenso por cobrança, a maioria das rotas autenticadas em `/api/` responde **402 Payment Required** com corpo JSON `{"detail": "..."}` (exceto bypass: registro, token, `me`, reset de senha, webhook Asaas). O front-end pode redirecionar o usuário para a página de cobrança ao receber 402.

## Admin Django

| Método | Caminho | Autenticação | Descrição |
|--------|---------|--------------|-----------|
| * | `/admin/` | Sessão staff | Painel administrativo padrão. |
