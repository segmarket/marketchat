export const WHATSAPP_CONNECT_SPOTLIGHT_COPY = {
  trigger:
    "Passo 1 de 2: Clique aqui para iniciar o nosso robô e gerar o seu QR Code exclusivo de conexão.",
  scan:
    'Passo 2 de 2: Quase pronto. Abra o WhatsApp no seu celular, vá em "Aparelhos Conectados" > "Conectar um aparelho" e aponte a câmera para este QR Code.',
} as const;

export type WhatsappConnectSpotlightStep = keyof typeof WHATSAPP_CONNECT_SPOTLIGHT_COPY;
