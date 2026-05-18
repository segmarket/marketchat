import type { Edge, Node, Viewport } from "@xyflow/react";

export type FlowNodeType = "trigger" | "ai_filter" | "response" | "owner_alert";

export type TriggerNodeData = {
  label: string;
};

export type AiFilterNodeData = {
  label: string;
  intents: string[];
  systemPrompt?: string;
};

export type ResponseNodeData = {
  label: string;
  message: string;
};

export type OwnerAlertNodeData = {
  label: string;
  ownerPhone: string;
  messageTemplate: string;
};

export type FlowNodeData = TriggerNodeData | AiFilterNodeData | ResponseNodeData | OwnerAlertNodeData;

export type FlowNode = Node<FlowNodeData, FlowNodeType>;
export type FlowEdge = Edge<{ intent?: string }>;

export type FlowData = {
  nodes: FlowNode[];
  edges: FlowEdge[];
  viewport?: Viewport;
};

export type ChatbotWorkflow = {
  id: number;
  name: string;
  is_active: boolean;
  is_system: boolean;
  system_key: string;
  flow_data: FlowData;
  created_at: string;
  updated_at: string;
};

export type ChatbotWorkflowSummary = {
  id: number;
  name: string;
  is_active: boolean;
  is_system: boolean;
  system_key: string;
  created_at: string;
  updated_at: string;
};

export type SaveWorkflowPayload = {
  id?: number;
  name?: string;
  is_active?: boolean;
  flow_data: FlowData;
};
