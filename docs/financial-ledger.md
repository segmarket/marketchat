# Carteira virtual (ledger interno)

## Visão geral

Recebimentos Pix de moradores caem na **conta master** do Asaas (token da plataforma). O MarketChat mantém um **ledger interno** por tenant (`Wallet`) para saldo, extrato e saques automáticos via Pix.

## Modelos

| Modelo | Descrição |
|--------|-----------|
| `Wallet` | Saldo disponível, chave Pix padrão (`default_pix_key`) |
| `LedgerTransaction` | Extrato (INFLOW vendas, OUTFLOW saques) |
| `WithdrawalRequest` | Saque Pix automático (`asaas_transfer_id`, status PAID/PROCESSING) |

## Fluxo de venda

1. Morador paga Pix gerado na conta master (`create_cart_pix_charge`, sem split).
2. Webhook `PAYMENT_RECEIVED` → `credit_sale_payment`.
3. Credita **líquido** = bruto − `FINANCIAL_PLATFORM_FEE_PERCENT` (default **2%**).
4. Idempotência: `LedgerTransaction.external_id` = ID do pagamento Asaas (unique).

## Fluxo de saque automático

1. Mercado configura chave Pix na primeira vez em **Financeiro** ou edita em **Configurações > Integrações** (`PATCH /api/financial/wallet/settings/`).
2. `POST /api/financial/withdraw/` com `{ "amount" }` apenas.
3. Backend valida saldo, chama `POST /v3/transfers` no Asaas (conta master).
4. Sucesso → debita `balance_available`, cria OUTFLOW e `WithdrawalRequest` PAID ou PROCESSING.
5. Falha Asaas → rollback; saldo do cliente não é alterado.
6. Webhook `TRANSFER_DONE` → confirma saque (`PROCESSING` → `PAID`); zera `balance_processing` no extrato.
7. Webhook `TRANSFER_FAILED` / `TRANSFER_CANCELLED` → estorna saldo e marca `REJECTED`.

**Webhook Asaas (saques):** habilite `TRANSFER_DONE` (e opcionalmente `TRANSFER_FAILED`, `TRANSFER_CANCELLED`) no mesmo webhook `PRD_Asaas` (`/api/billing/webhooks/asaas/`).

**Requisito operacional:** a conta master Asaas precisa ter saldo suficiente para transferências Pix e permissão de saque via API.

## API

| Método | Rota | Permissão |
|--------|------|-----------|
| GET | `/api/financial/statement/` | JWT + admin tenant |
| GET | `/api/financial/wallet/settings/` | JWT + admin tenant — tipo, chave mascarada e flag `has_pix_key_configured` |
| PATCH | `/api/financial/wallet/settings/` | JWT + admin tenant — valida CPF/CNPJ/e-mail/telefone/chave aleatória |
| POST | `/api/financial/withdraw/` | JWT + admin tenant |

## Mapeamento chave Pix → Asaas

| Interno | Asaas `pixAddressKeyType` |
|---------|---------------------------|
| PHONE | PHONE |
| RANDOM | EVP |
| CPF/CNPJ/EMAIL | iguais |

## Variáveis

```bash
FINANCIAL_PLATFORM_FEE_PERCENT=2
```

## Frontend

Rota `/admin/financial` — onboarding da chave Pix (se ainda não configurada), saldo, extrato e saque (somente valor). Edição da chave em **Configurações > Integrações**.

## Legado

Saques antigos em status PENDING (fila manual) ainda podem ser tratados no Django Admin.
