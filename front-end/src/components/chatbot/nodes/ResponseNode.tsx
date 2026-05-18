import { useReactFlow, type NodeProps } from "@xyflow/react";
import { MessageCircle } from "lucide-react";
import { useFlowCanvasReadOnly } from "../FlowCanvasContext";
import type { ResponseNodeData } from "../../../features/chatbot/types";
import { NodeShell, inputClass } from "./nodeShell";

export default function ResponseNode({ id, data }: NodeProps) {
  const readOnly = useFlowCanvasReadOnly();
  const { updateNodeData } = useReactFlow();
  const d = data as ResponseNodeData;

  return (
    <NodeShell
      title="Resposta ao Morador"
      icon={MessageCircle}
      borderClass="border-brand-500"
      headerClass="bg-brand-500"
    >
      <p className="text-xs text-gray-500 dark:text-gray-400">Enviar mensagem automática de volta para o morador.</p>
      <textarea
        className={`min-h-[72px] ${inputClass}`}
        value={d.message || ""}
        placeholder="Texto da resposta..."
        disabled={readOnly}
        onChange={(e) => updateNodeData(id, { message: e.target.value })}
      />
    </NodeShell>
  );
}
