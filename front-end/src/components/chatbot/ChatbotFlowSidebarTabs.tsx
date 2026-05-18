import { Folder, Puzzle } from "lucide-react";
import type { ReactNode } from "react";

export type SidebarTab = "flows" | "builder";

type Props = {
  activeTab: SidebarTab;
  builderDisabled: boolean;
  onTabChange: (tab: SidebarTab) => void;
  flowsPanel: ReactNode;
  builderPanel: ReactNode;
};

export default function ChatbotFlowSidebarTabs({
  activeTab,
  builderDisabled,
  onTabChange,
  flowsPanel,
  builderPanel,
}: Props) {
  return (
    <aside className="flex h-full w-80 shrink-0 flex-col overflow-hidden border-r border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      <div className="flex shrink-0 border-b border-gray-200 dark:border-gray-800">
        <button
          type="button"
          onClick={() => onTabChange("flows")}
          className={`flex flex-1 items-center justify-center gap-2 px-3 py-3 text-sm font-medium transition ${
            activeTab === "flows"
              ? "border-b-2 border-brand-500 text-brand-600 dark:text-brand-400"
              : "text-gray-500 hover:text-gray-700 dark:text-gray-400"
          }`}
        >
          <Folder className="h-4 w-4" />
          Meus Fluxos
        </button>
        <button
          type="button"
          onClick={() => !builderDisabled && onTabChange("builder")}
          disabled={builderDisabled}
          className={`flex flex-1 items-center justify-center gap-2 px-3 py-3 text-sm font-medium transition ${
            builderDisabled ? "cursor-not-allowed opacity-50" : ""
          } ${
            activeTab === "builder"
              ? "border-b-2 border-brand-500 text-brand-600 dark:text-brand-400"
              : "text-gray-500 hover:text-gray-700 dark:text-gray-400"
          }`}
        >
          <Puzzle className="h-4 w-4" />
          Construtor
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">{activeTab === "flows" ? flowsPanel : builderPanel}</div>
    </aside>
  );
}
