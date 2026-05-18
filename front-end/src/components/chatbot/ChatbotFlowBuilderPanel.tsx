import Button from "../ui/button/Button";
import { getFlowTemplates, type FlowTemplateId } from "../../features/chatbot/templates";
import type { FlowNodeType } from "../../features/chatbot/types";

const BLOCKS: { type: FlowNodeType; label: string; description: string }[] = [
  { type: "trigger", label: "Gatilho de Entrada", description: "Início do fluxo" },
  { type: "ai_filter", label: "Filtro de IA", description: "Classificar intenção" },
  { type: "response", label: "Resposta ao Morador", description: "Mensagem automática" },
  { type: "owner_alert", label: "Alerta ao Dono", description: "WhatsApp do proprietário" },
];

type Props = {
  defaultOwnerPhone: string;
  disabled?: boolean;
  onLoadTemplate: (id: FlowTemplateId) => void;
  onAddBlock: (type: FlowNodeType) => void;
};

export default function ChatbotFlowBuilderPanel({
  defaultOwnerPhone,
  disabled = false,
  onLoadTemplate,
  onAddBlock,
}: Props) {
  const templates = getFlowTemplates(defaultOwnerPhone);

  return (
    <div
      className={`flex flex-col gap-6 p-4 lg:p-5 ${disabled ? "pointer-events-none opacity-50" : ""}`}
    >
      <section>
        <h3 className="mb-2 text-sm font-semibold text-gray-800 dark:text-white/90">
          Fluxos Prontos (Templates)
        </h3>
        <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">
          Carregue um organograma pré-definido no canvas.
        </p>
        <div className="flex flex-col gap-2">
          {templates.map((tpl) => (
            <Button
              key={tpl.id}
              type="button"
              variant="outline"
              className="!justify-start !text-left !whitespace-normal"
              onClick={() => onLoadTemplate(tpl.id)}
              disabled={disabled}
            >
              <span className="block font-medium">{tpl.title}</span>
              <span className="block text-xs font-normal text-gray-500">{tpl.description}</span>
            </Button>
          ))}
        </div>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-gray-800 dark:text-white/90">Adicionar Blocos</h3>
        <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">
          Clique para inserir um novo nó no mapa.
        </p>
        <div className="flex flex-col gap-2">
          {BLOCKS.map((block) => (
            <button
              key={block.type}
              type="button"
              disabled={disabled}
              onClick={() => onAddBlock(block.type)}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-left transition hover:border-brand-300 hover:bg-brand-50 disabled:cursor-not-allowed dark:border-gray-700 dark:bg-gray-900 dark:hover:border-brand-700 dark:hover:bg-brand-500/10"
            >
              <span className="block text-sm font-medium text-gray-800 dark:text-white/90">{block.label}</span>
              <span className="block text-xs text-gray-500 dark:text-gray-400">{block.description}</span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
