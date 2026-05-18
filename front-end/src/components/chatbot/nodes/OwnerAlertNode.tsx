import { useReactFlow, type NodeProps } from "@xyflow/react";
import { Bell } from "lucide-react";
import { useFlowCanvasReadOnly } from "../FlowCanvasContext";
import type { OwnerAlertNodeData } from "../../../features/chatbot/types";
import { maskPhoneInput } from "../../../features/residents/format";
import { NodeShell, inputClass } from "./nodeShell";

export default function OwnerAlertNode({ id, data }: NodeProps) {
  const readOnly = useFlowCanvasReadOnly();
  const { updateNodeData } = useReactFlow();
  const d = data as OwnerAlertNodeData;

  return (
    <NodeShell
      title="Alerta WhatsApp"
      icon={Bell}
      borderClass="border-error-500"
      headerClass="bg-error-500"
      showSource={false}
    >
      <p className="text-xs text-gray-500 dark:text-gray-400">
        Encaminhar dados do morador e o problema para o WhatsApp do Dono.
      </p>
      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400">
        Telefone do dono
      </label>
      <p className="mb-1 text-xs text-gray-400 dark:text-gray-500">
        Preenchido com o celular da conta; você pode alterar se necessário.
      </p>
      <input
        className={`h-9 ${inputClass}`}
        value={d.ownerPhone ? maskPhoneInput(d.ownerPhone) : ""}
        placeholder="(11) 99999-9999"
        disabled={readOnly}
        onChange={(e) => {
          const digits = e.target.value.replace(/\D/g, "");
          updateNodeData(id, { ownerPhone: digits });
        }}
      />
      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400">Mensagem</label>
      <textarea
        className={`min-h-[64px] ${inputClass}`}
        value={d.messageTemplate || ""}
        placeholder="Use {name}, {phone}, {text}"
        disabled={readOnly}
        onChange={(e) => updateNodeData(id, { messageTemplate: e.target.value })}
      />
    </NodeShell>
  );
}
