import type { NodeTypes } from "@xyflow/react";
import AiFilterNode from "../../components/chatbot/nodes/AiFilterNode";
import OwnerAlertNode from "../../components/chatbot/nodes/OwnerAlertNode";
import ResponseNode from "../../components/chatbot/nodes/ResponseNode";
import TriggerNode from "../../components/chatbot/nodes/TriggerNode";

export const chatbotNodeTypes: NodeTypes = {
  trigger: TriggerNode,
  ai_filter: AiFilterNode,
  response: ResponseNode,
  owner_alert: OwnerAlertNode,
};
