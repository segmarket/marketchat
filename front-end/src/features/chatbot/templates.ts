import type { FlowData } from "./types";
import { digitsOnlyPhone } from "./flowDefaults";

function baseViewport() {
  return { x: 0, y: 0, zoom: 0.85 };
}

function ownerPhone(defaultOwnerPhone?: string): string {
  return digitsOnlyPhone(defaultOwnerPhone ?? "");
}

export function templateGeladeiraManutencao(defaultOwnerPhone = ""): FlowData {
  return {
    nodes: [
      {
        id: "trigger-1",
        type: "trigger",
        position: { x: 80, y: 40 },
        data: { label: "Quando o Morador enviar uma mensagem..." },
      },
      {
        id: "ai-1",
        type: "ai_filter",
        position: { x: 80, y: 180 },
        data: {
          label: "IA analisa a intenção do texto",
          intents: ["manutenção", "geladeira", "reclamação"],
          systemPrompt: "Classifique se a mensagem é sobre manutenção ou problema na geladeira.",
        },
      },
      {
        id: "response-1",
        type: "response",
        position: { x: 80, y: 360 },
        data: {
          label: "Enviar mensagem automática ao morador",
          message: "O responsável pelo mercado foi avisado. Em breve entraremos em contato.",
        },
      },
      {
        id: "alert-1",
        type: "owner_alert",
        position: { x: 80, y: 540 },
        data: {
          label: "Alerta no WhatsApp do Dono",
          ownerPhone: ownerPhone(defaultOwnerPhone),
          messageTemplate: "Manutenção reportada por {name} ({phone}): {text}",
        },
      },
    ],
    edges: [
      { id: "e-t-ai", source: "trigger-1", target: "ai-1" },
      {
        id: "e-ai-res",
        source: "ai-1",
        target: "response-1",
        data: { intent: "manutenção" },
      },
      { id: "e-res-alert", source: "response-1", target: "alert-1" },
    ],
    viewport: baseViewport(),
  };
}

export function templateMaquininhaPagamento(defaultOwnerPhone = ""): FlowData {
  return {
    nodes: [
      {
        id: "trigger-1",
        type: "trigger",
        position: { x: 80, y: 40 },
        data: { label: "Quando o Morador enviar uma mensagem..." },
      },
      {
        id: "ai-1",
        type: "ai_filter",
        position: { x: 80, y: 180 },
        data: {
          label: "IA analisa a intenção do texto",
          intents: ["pagamento", "maquininha", "pix"],
          systemPrompt: "Classifique problemas de pagamento ou maquininha.",
        },
      },
      {
        id: "response-1",
        type: "response",
        position: { x: 80, y: 360 },
        data: {
          label: "Resposta ao morador",
          message:
            "Recebemos seu relato sobre pagamento. Nossa equipe está verificando a maquininha.",
        },
      },
      {
        id: "alert-1",
        type: "owner_alert",
        position: { x: 80, y: 540 },
        data: {
          label: "Alerta no WhatsApp do Dono",
          ownerPhone: ownerPhone(defaultOwnerPhone),
          messageTemplate: "Falha de pagamento — {name} ({phone}): {text}",
        },
      },
    ],
    edges: [
      { id: "e-t-ai", source: "trigger-1", target: "ai-1" },
      {
        id: "e-ai-res",
        source: "ai-1",
        target: "response-1",
        data: { intent: "pagamento" },
      },
      { id: "e-res-alert", source: "response-1", target: "alert-1" },
    ],
    viewport: baseViewport(),
  };
}

export function templateProdutoEstoque(defaultOwnerPhone = ""): FlowData {
  return {
    nodes: [
      {
        id: "trigger-1",
        type: "trigger",
        position: { x: 80, y: 40 },
        data: { label: "Quando o Morador enviar uma mensagem..." },
      },
      {
        id: "ai-1",
        type: "ai_filter",
        position: { x: 80, y: 180 },
        data: {
          label: "IA analisa a intenção do texto",
          intents: ["estoque", "produto", "falta"],
          systemPrompt: "Classifique mensagens sobre produto em falta ou estoque.",
        },
      },
      {
        id: "response-1",
        type: "response",
        position: { x: 80, y: 360 },
        data: {
          label: "Resposta ao morador",
          message: "Obrigado! Anotamos a falta de produto e vamos repor o estoque.",
        },
      },
      {
        id: "alert-1",
        type: "owner_alert",
        position: { x: 80, y: 540 },
        data: {
          label: "Alerta no WhatsApp do Dono",
          ownerPhone: ownerPhone(defaultOwnerPhone),
          messageTemplate: "Produto em falta — {name} ({phone}): {text}",
        },
      },
    ],
    edges: [
      { id: "e-t-ai", source: "trigger-1", target: "ai-1" },
      {
        id: "e-ai-res",
        source: "ai-1",
        target: "response-1",
        data: { intent: "estoque" },
      },
      { id: "e-res-alert", source: "response-1", target: "alert-1" },
    ],
    viewport: baseViewport(),
  };
}

export type FlowTemplateId = "geladeira" | "maquininha" | "estoque";

export function getFlowTemplates(defaultOwnerPhone = "") {
  return [
    {
      id: "geladeira" as const,
      title: "Geladeira com Problema",
      description: "Manutenção e geladeira",
      build: () => templateGeladeiraManutencao(defaultOwnerPhone),
    },
    {
      id: "maquininha" as const,
      title: "Falha na Maquininha/Pagamento",
      description: "Pagamento e PIX",
      build: () => templateMaquininhaPagamento(defaultOwnerPhone),
    },
    {
      id: "estoque" as const,
      title: "Produto em Falta/Estoque",
      description: "Reposição de estoque",
      build: () => templateProdutoEstoque(defaultOwnerPhone),
    },
  ];
}

/** @deprecated Use getFlowTemplates */
export const FLOW_TEMPLATES = getFlowTemplates();
