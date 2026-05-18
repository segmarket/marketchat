import type { RefObject } from "react";
import type { ChatbotWorkflowSummary } from "../../features/chatbot/types";
import type { FlowTemplateId } from "../../features/chatbot/templates";
import type { FlowData, FlowNodeType } from "../../features/chatbot/types";
import ChatbotFlowBuilder, { type ChatbotFlowBuilderHandle } from "./ChatbotFlowBuilder";
import ChatbotFlowBuilderPanel from "./ChatbotFlowBuilderPanel";
import ChatbotFlowCanvasTopBar, { type SaveState } from "./ChatbotFlowCanvasTopBar";
import ChatbotFlowListPanel from "./ChatbotFlowListPanel";
import ChatbotFlowSidebarTabs, { type SidebarTab } from "./ChatbotFlowSidebarTabs";

type Props = {
  loading: boolean;
  builderRef: RefObject<ChatbotFlowBuilderHandle | null>;
  canvasKey: string;
  initialFlow: FlowData | null;
  defaultOwnerPhone: string;
  workflows: ChatbotWorkflowSummary[];
  selectedWorkflowId: number | null;
  isDraft: boolean;
  flowName: string;
  isActive: boolean;
  isSystemFlow: boolean;
  sidebarTab: SidebarTab;
  builderTabDisabled: boolean;
  saveState: SaveState;
  saveDisabled: boolean;
  togglingId: number | null;
  onTabChange: (tab: SidebarTab) => void;
  onCreateBlank: () => void;
  onSelectWorkflow: (id: number) => void;
  onToggleActive: (id: number, active: boolean) => void;
  onRenameList: (workflow: ChatbotWorkflowSummary) => void;
  onDuplicate: (id: number) => void;
  onDeleteList: (workflow: ChatbotWorkflowSummary) => void;
  onOpenSettings: () => void;
  onSave: () => void;
  onFlowChange: () => void;
  onLoadTemplate: (id: FlowTemplateId) => void;
  onAddBlock: (type: FlowNodeType) => void;
};

export default function ChatbotFlowWorkspace({
  loading,
  builderRef,
  canvasKey,
  initialFlow,
  defaultOwnerPhone,
  workflows,
  selectedWorkflowId,
  isDraft,
  flowName,
  isActive,
  isSystemFlow,
  sidebarTab,
  builderTabDisabled,
  saveState,
  saveDisabled,
  togglingId,
  onTabChange,
  onCreateBlank,
  onSelectWorkflow,
  onToggleActive,
  onRenameList,
  onDuplicate,
  onDeleteList,
  onOpenSettings,
  onSave,
  onFlowChange,
  onLoadTemplate,
  onAddBlock,
}: Props) {
  return (
    <div className="flex h-full w-full overflow-hidden bg-white dark:bg-gray-900">
      <ChatbotFlowSidebarTabs
        activeTab={sidebarTab}
        builderDisabled={builderTabDisabled}
        onTabChange={onTabChange}
        flowsPanel={
          <ChatbotFlowListPanel
            workflows={workflows}
            selectedWorkflowId={selectedWorkflowId}
            isDraft={isDraft}
            togglingId={togglingId}
            onCreateBlank={onCreateBlank}
            onSelectWorkflow={onSelectWorkflow}
            onToggleActive={onToggleActive}
            onRename={onRenameList}
            onDuplicate={onDuplicate}
            onDelete={onDeleteList}
          />
        }
        builderPanel={
          <ChatbotFlowBuilderPanel
            defaultOwnerPhone={defaultOwnerPhone}
            disabled={builderTabDisabled}
            onLoadTemplate={onLoadTemplate}
            onAddBlock={onAddBlock}
          />
        }
      />

      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col">
        <ChatbotFlowCanvasTopBar
          flowName={flowName}
          isActive={isActive}
          isSystem={isSystemFlow}
          saveState={saveState}
          saveDisabled={saveDisabled}
          onOpenSettings={onOpenSettings}
          onSave={onSave}
        />

        <div className="relative h-full min-h-0 w-full flex-1">
          {loading ? (
            <div className="flex h-full items-center justify-center bg-slate-50 dark:bg-gray-950/50">
              <p className="text-sm text-gray-500 animate-pulse dark:text-gray-400">Carregando canvas…</p>
            </div>
          ) : (
            <ChatbotFlowBuilder
              key={canvasKey}
              ref={builderRef}
              initialFlow={initialFlow}
              defaultOwnerPhone={defaultOwnerPhone}
              readOnly={false}
              onFlowChange={onFlowChange}
            />
          )}
        </div>
      </div>
    </div>
  );
}
