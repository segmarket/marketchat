import type { NodeProps } from "@xyflow/react";
import { Play } from "lucide-react";
import type { TriggerNodeData } from "../../../features/chatbot/types";
import { NodeShell } from "./nodeShell";

export default function TriggerNode({ data }: NodeProps) {
  const d = data as TriggerNodeData;
  return (
    <NodeShell
      title="Gatilho"
      icon={Play}
      borderClass="border-emerald-500"
      headerClass="bg-emerald-600"
      showTarget={false}
    >
      <p>{d.label || "Quando o Morador enviar uma mensagem..."}</p>
    </NodeShell>
  );
}
