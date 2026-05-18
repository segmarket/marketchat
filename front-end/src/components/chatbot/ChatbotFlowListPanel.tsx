import { Plus } from "lucide-react";
import type { ChatbotWorkflowSummary } from "../../features/chatbot/types";
import Button from "../ui/button/Button";
import FlowListItem from "./FlowListItem";

type Props = {
  workflows: ChatbotWorkflowSummary[];
  selectedWorkflowId: number | null;
  isDraft: boolean;
  togglingId: number | null;
  onCreateBlank: () => void;
  onSelectWorkflow: (id: number) => void;
  onToggleActive: (id: number, active: boolean) => void;
  onRename: (workflow: ChatbotWorkflowSummary) => void;
  onDuplicate: (id: number) => void;
  onDelete: (workflow: ChatbotWorkflowSummary) => void;
};

export default function ChatbotFlowListPanel({
  workflows,
  selectedWorkflowId,
  isDraft,
  togglingId,
  onCreateBlank,
  onSelectWorkflow,
  onToggleActive,
  onRename,
  onDuplicate,
  onDelete,
}: Props) {
  const systemFlows = workflows.filter((w) => w.is_system);
  const customFlows = workflows.filter((w) => !w.is_system);

  return (
    <div className="flex flex-col gap-5 p-4 lg:p-5">
      <section>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          Fluxos Padrão (Sistema)
        </h3>
        {systemFlows.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Nenhum fluxo padrão encontrado. Execute o seed no servidor.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {systemFlows.map((wf) => (
              <FlowListItem
                key={wf.id}
                workflow={wf}
                selected={selectedWorkflowId === wf.id && !isDraft}
                togglingActive={togglingId === wf.id}
                onSelect={() => onSelectWorkflow(wf.id)}
                onToggleActive={(active) => onToggleActive(wf.id, active)}
                onRename={() => onRename(wf)}
                onDuplicate={() => onDuplicate(wf.id)}
                onDelete={() => onDelete(wf)}
              />
            ))}
          </div>
        )}
      </section>

      <section>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          Meus Fluxos Customizados
        </h3>
        <Button
          startIcon={<Plus className="h-4 w-4" />}
          onClick={onCreateBlank}
          className="mb-3 w-full"
        >
          Criar Novo Fluxo em Branco
        </Button>
        {customFlows.length === 0 && !isDraft ? (
          <div className="rounded-lg border border-dashed border-gray-300 px-3 py-6 text-center dark:border-gray-700">
            <p className="text-sm text-gray-500 dark:text-gray-400">Nenhum fluxo customizado ainda.</p>
            <Button size="sm" className="mt-3" onClick={onCreateBlank}>
              Criar primeiro fluxo
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {isDraft && (
              <div className="rounded-lg border border-brand-500 bg-brand-50 px-3 py-2.5 dark:border-brand-600 dark:bg-brand-500/10">
                <p className="truncate text-sm font-medium text-gray-800 dark:text-white/90">Novo fluxo</p>
                <span className="text-xs text-gray-400">Rascunho — salve para persistir</span>
              </div>
            )}
            {customFlows.map((wf) => (
              <FlowListItem
                key={wf.id}
                workflow={wf}
                selected={selectedWorkflowId === wf.id && !isDraft}
                togglingActive={togglingId === wf.id}
                onSelect={() => onSelectWorkflow(wf.id)}
                onToggleActive={(active) => onToggleActive(wf.id, active)}
                onRename={() => onRename(wf)}
                onDuplicate={() => onDuplicate(wf.id)}
                onDelete={() => onDelete(wf)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
