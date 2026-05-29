export const PRODUCT_IMPORT_SPOTLIGHT_COPY = {
  download:
    "Passo 1 de 2: Baixe nosso modelo padrão primeiro. Ele já vem estruturado para você apenas preencher com os seus produtos.",
  import:
    "Passo 2 de 2: Excelente. Agora clique aqui para selecionar a planilha que você preencheu e concluir a missão.",
} as const;

export type ProductImportSpotlightStep = keyof typeof PRODUCT_IMPORT_SPOTLIGHT_COPY;
