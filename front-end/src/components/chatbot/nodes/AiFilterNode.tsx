import { useReactFlow, type NodeProps } from "@xyflow/react";
import { Brain } from "lucide-react";
import { useFlowCanvasReadOnly } from "../FlowCanvasContext";
import type { AiFilterNodeData } from "../../../features/chatbot/types";
import { NodeShell, inputClass } from "./nodeShell";

export default function AiFilterNode({ id, data }: NodeProps) {
  const readOnly = useFlowCanvasReadOnly();
  const { updateNodeData } = useReactFlow();
  const d = data as AiFilterNodeData;
  const intentsText = (d.intents || []).join(", ");

  return (
    <NodeShell title="Inteligência Artificial" icon={Brain} borderClass="border-violet-500" headerClass="bg-violet-600">
      <p className="text-xs text-gray-500 dark:text-gray-400">
        A IA analisa a intenção do texto (ex.: reclamação, compra)
      </p>
      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400">Intenções (vírgula)</label>
      <input
        className={`h-9 ${inputClass}`}
        value={intentsText}
        disabled={readOnly}
        onChange={(e) => {
          const intents = e.target.value
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean);
          updateNodeData(id, { intents });
        }}
      />
    </NodeShell>
  );
}
