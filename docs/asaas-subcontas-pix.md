# Subcontas Asaas (Pix + split)

## Fluxo no MarketChat

1. Admin cadastra **mercado com endereço completo** (CEP, rua, número, bairro, cidade, UF).
2. Em **Configurações → Integrações → Pix**, informa CNPJ (obrigatório em produção), e-mail e chave Pix.
3. O backend chama `POST /v3/accounts` com os mesmos dados comerciais (endereço do primeiro mercado, `incomeValue`, telefone da conta).
4. Grava `walletId` (split), `asaas_account_id` e `asaas_subaccount_api_key` (retorno único).
5. Status inicia em **PENDING** até o Asaas aprovar (`accountStatus.general = APPROVED`).
6. Cobranças Pix do WhatsApp usam `split` 100% para `walletId` só com subconta **APPROVED**.

## Webhooks Asaas (conta raiz PRD)

Além dos eventos de **pagamento** e **assinatura**, marque na conta **produção**:

- `ACCOUNT_STATUS_GENERAL_APPROVAL_*`
- `ACCOUNT_STATUS_COMMERCIAL_INFO_*`
- `ACCOUNT_STATUS_DOCUMENT_*`
- `ACCOUNT_STATUS_BANK_ACCOUNT_INFO_*`

URL: `https://app.marketchat.com.br/api/billing/webhooks/asaas/`

Na criação da subconta, o sistema também tenta registrar um webhook na subconta (mesma URL/token), se `PUBLIC_WEBHOOK_BASE_URL` e `ASAAS_WEBHOOK_TOKEN` (≥ 32 caracteres) estiverem definidos.

## Variáveis `.env`

```bash
ASAAS_SUBACCOUNT_INCOME_VALUE=5000
ASAAS_SUBACCOUNT_COMPANY_TYPE=MEI
ASAAS_WEBHOOK_NOTIFY_EMAIL=suporte@marketchat.com.br
PUBLIC_WEBHOOK_BASE_URL=https://app.marketchat.com.br
```

## API

| Método | Caminho | Descrição |
|--------|---------|-----------|
| GET/PUT | `/api/integrations/pix/` | Configuração e status KYC |
| POST | `/api/integrations/pix/sync-status/` | Consulta `GET /v3/myAccount/status` com apiKey da subconta |

Resposta inclui: `split_ready`, `asaas_status_*`, `status_message`, `can_sync_status`.

## Produção

- Subcontas exigem **CNPJ** (14 dígitos) na API Asaas produção.
- Sandbox ainda aceita CPF para testes.
