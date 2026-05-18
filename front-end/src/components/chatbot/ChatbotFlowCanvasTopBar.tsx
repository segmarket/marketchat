import { Check, ChevronRight, Folder, Loader2, Settings } from "lucide-react";
import Button from "../ui/button/Button";

export type SaveState = "idle" | "saving" | "saved";

type Props = {
  flowName: string;
  isActive: boolean;
  isSystem: boolean;
  saveState: SaveState;
  saveDisabled: boolean;
  onOpenSettings: () => void;
  onSave: () => void;
};

export default function ChatbotFlowCanvasTopBar({
  flowName,
  isActive,
  isSystem,
  saveState,
  saveDisabled,
  onOpenSettings,
  onSave,
}: Props) {
  return (
    <div className="absolute top-0 right-0 left-0 z-20 flex items-center justify-between gap-3 border-b border-gray-200 bg-white/90 p-4 backdrop-blur-sm dark:border-gray-800 dark:bg-gray-900/90">
      <div className="flex min-w-0 flex-wrap items-center gap-2 text-sm">
        <span className="text-gray-500 dark:text-gray-400">Fluxos do Chatbot</span>
        <ChevronRight className="h-4 w-4 shrink-0 text-gray-400" />
        <span className="flex min-w-0 items-center gap-1.5 font-medium text-gray-800 dark:text-white/90">
          <Folder className="h-4 w-4 shrink-0 text-brand-500" />
          <span className="truncate">{flowName}</span>
        </span>
        {isSystem ? (
          <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400">
            Sistema
          </span>
        ) : isActive ? (
          <span className="text-xs text-success-500">● Ativo</span>
        ) : (
          <span className="text-xs text-gray-400">○ Inativo</span>
        )}
        {!isSystem && (
          <button
            type="button"
            onClick={onOpenSettings}
            className="ml-1 flex h-8 w-8 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
            aria-label="Configurações do fluxo"
          >
            <Settings className="h-4 w-4" />
          </button>
        )}
      </div>

      <Button
        onClick={onSave}
        disabled={saveDisabled || saveState === "saving"}
        className="shrink-0"
        startIcon={
          saveState === "saving" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : saveState === "saved" ? (
            <Check className="h-4 w-4" />
          ) : undefined
        }
      >
        {saveState === "saving"
          ? "Salvando…"
          : saveState === "saved"
            ? "Salvo"
            : "Salvar Estrutura de Fluxo"}
      </Button>
    </div>
  );
}
