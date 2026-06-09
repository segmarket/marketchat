import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import PageMeta from "../../components/common/PageMeta";
import ChatbotFlowDeleteConfirmModal from "../../components/chatbot/ChatbotFlowDeleteConfirmModal";
import ChatbotFlowRenameModal from "../../components/chatbot/ChatbotFlowRenameModal";
import ChatbotFlowWorkspace from "../../components/chatbot/ChatbotFlowWorkspace";
import type { ChatbotFlowBuilderHandle } from "../../components/chatbot/ChatbotFlowBuilder";
import type { SaveState } from "../../components/chatbot/ChatbotFlowCanvasTopBar";
import type { SidebarTab } from "../../components/chatbot/ChatbotFlowSidebarTabs";
import {
  deleteChatbotWorkflow,
  duplicateChatbotWorkflow,
  fetchChatbotWorkflow,
  fetchChatbotWorkflows,
  patchChatbotWorkflow,
  saveChatbotWorkflow,
} from "../../features/chatbot/api";
import { resolveAccountOwnerPhone } from "../../features/chatbot/flowDefaults";
import type { FlowTemplateId } from "../../features/chatbot/templates";
import type { ChatbotWorkflowSummary, FlowData, FlowNodeType } from "../../features/chatbot/types";
import { fetchAccountSettings } from "../../features/settings/api";
import { getAxiosErrorMessage } from "../../utils/apiError";

const EMPTY_FLOW: FlowData = { nodes: [], edges: [] };

export default function ChatbotFlowsPage() {
  const builderRef = useRef<ChatbotFlowBuilderHandle>(null);

  const [workflows, setWorkflows] = useState<ChatbotWorkflowSummary[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<number | null>(null);
  const [isDraft, setIsDraft] = useState(false);
  const [flowName, setFlowName] = useState("Novo fluxo");
  const [isActive, setIsActive] = useState(false);
  const [isSystemFlow, setIsSystemFlow] = useState(false);
  const [initialFlow, setInitialFlow] = useState<FlowData | null>(null);
  const [canvasKey, setCanvasKey] = useState("init");
  const [defaultOwnerPhone, setDefaultOwnerPhone] = useState("");
  const [loading, setLoading] = useState(true);
  const [canvasLoading, setCanvasLoading] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [sidebarTab, setSidebarTab] = useState<SidebarTab>("flows");
  const [togglingId, setTogglingId] = useState<number | null>(null);

  const [renameOpen, setRenameOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<ChatbotWorkflowSummary | null>(null);
  const [renameBusy, setRenameBusy] = useState(false);

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ChatbotWorkflowSummary | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const builderTabDisabled = selectedWorkflowId === null && !isDraft;

  const bumpCanvas = useCallback((key: string) => {
    setCanvasKey(key);
  }, []);

  const loadWorkflow = useCallback(
    async (id: number, list?: ChatbotWorkflowSummary[]) => {
      setCanvasLoading(true);
      setIsDraft(false);
      setSelectedWorkflowId(id);
      try {
        const detail = await fetchChatbotWorkflow(id);
        setFlowName(detail.name);
        setIsActive(detail.is_active);
        setIsSystemFlow(detail.is_system);
        setInitialFlow(detail.flow_data ?? EMPTY_FLOW);
        setIsDirty(false);
        bumpCanvas(`workflow-${id}`);
        setSidebarTab("builder");

        if (list) {
          setWorkflows(
            list.map((w) =>
              w.id === id ? { ...w, name: detail.name, is_active: detail.is_active } : w,
            ),
          );
        }
      } catch (err) {
        toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar o fluxo." }));
      } finally {
        setCanvasLoading(false);
      }
    },
    [bumpCanvas],
  );

  const refreshWorkflowList = useCallback(async () => {
    return fetchChatbotWorkflows();
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      setLoading(true);
      try {
        const [list, account] = await Promise.all([refreshWorkflowList(), fetchAccountSettings()]);
        if (cancelled) return;

        setWorkflows(list);
        setDefaultOwnerPhone(resolveAccountOwnerPhone(account));

        const active = list.find((w) => w.is_active) ?? list[0];
        if (active) {
          await loadWorkflow(active.id, list);
        } else {
          setInitialFlow(EMPTY_FLOW);
          bumpCanvas("empty");
        }
      } catch (err) {
        if (!cancelled) {
          toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar os fluxos." }));
          setInitialFlow(EMPTY_FLOW);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void init();
    return () => {
      cancelled = true;
    };
  }, [refreshWorkflowList, loadWorkflow, bumpCanvas]);

  useEffect(() => {
    if (saveState !== "saved") return;
    const t = window.setTimeout(() => setSaveState("idle"), 2000);
    return () => window.clearTimeout(t);
  }, [saveState]);

  function handleCreateBlank() {
    setSelectedWorkflowId(null);
    setIsDraft(true);
    setIsSystemFlow(false);
    setFlowName("Novo fluxo");
    setIsActive(false);
    setInitialFlow(EMPTY_FLOW);
    setIsDirty(true);
    bumpCanvas(`draft-${Date.now()}`);
    setSidebarTab("builder");
  }

  async function handleToggleActive(id: number, active: boolean) {
    setTogglingId(id);
    setWorkflows((prev) => prev.map((w) => (w.id === id ? { ...w, is_active: active } : w)));
    try {
      const updated = await patchChatbotWorkflow(id, { is_active: active });
      setWorkflows((prev) => prev.map((w) => (w.id === id ? { ...w, is_active: updated.is_active } : w)));
      if (selectedWorkflowId === id) {
        setIsActive(updated.is_active);
      }
      toast.success(updated.is_active ? "Fluxo ativado." : "Fluxo desativado.");
    } catch (err) {
      const list = await refreshWorkflowList();
      setWorkflows(list);
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível alterar o status." }));
    } finally {
      setTogglingId(null);
    }
  }

  async function handleDuplicate(id: number) {
    try {
      const copy = await duplicateChatbotWorkflow(id);
      const list = await refreshWorkflowList();
      setWorkflows(list);
      await loadWorkflow(copy.id, list);
      toast.success("Fluxo duplicado.");
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao duplicar o fluxo." }));
    }
  }

  function openRenameFromList(workflow: ChatbotWorkflowSummary) {
    if (workflow.is_system) {
      toast.error("Fluxos padrão do sistema não podem ser renomeados.");
      return;
    }
    setRenameTarget(workflow);
    setRenameOpen(true);
  }

  function openRenameFromTopBar() {
    if (isSystemFlow) return;
    if (isDraft || selectedWorkflowId === null) {
      setRenameTarget(null);
      setRenameOpen(true);
      return;
    }
    const wf = workflows.find((w) => w.id === selectedWorkflowId);
    if (wf) openRenameFromList(wf);
  }

  async function handleRenameConfirm(name: string) {
    if (isDraft || selectedWorkflowId === null) {
      setFlowName(name);
      setIsDirty(true);
      setRenameOpen(false);
      return;
    }
    if (!renameTarget) return;
    setRenameBusy(true);
    try {
      const updated = await patchChatbotWorkflow(renameTarget.id, { name });
      const list = await refreshWorkflowList();
      setWorkflows(list);
      if (selectedWorkflowId === renameTarget.id || flowName === renameTarget.name) {
        setFlowName(updated.name);
      }
      setRenameOpen(false);
      toast.success("Fluxo renomeado.");
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao renomear." }));
    } finally {
      setRenameBusy(false);
    }
  }

  function openDelete(workflow: ChatbotWorkflowSummary) {
    if (workflow.is_system) {
      toast.error("Fluxos padrão do sistema não podem ser excluídos.");
      return;
    }
    setDeleteTarget(workflow);
    setDeleteOpen(true);
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    setDeleteBusy(true);
    try {
      await deleteChatbotWorkflow(deleteTarget.id);
      const list = await refreshWorkflowList();
      setWorkflows(list);

      if (selectedWorkflowId === deleteTarget.id || isDraft) {
        const next = list.find((w) => w.is_active) ?? list[0];
        if (next) {
          await loadWorkflow(next.id, list);
        } else {
          handleCreateBlank();
        }
      }
      setDeleteOpen(false);
      toast.success("Fluxo excluído.");
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao excluir o fluxo." }));
    } finally {
      setDeleteBusy(false);
    }
  }

  async function handleSave() {
    const flow_data = builderRef.current?.getFlowData();
    if (!flow_data) return;

    setSaveState("saving");
    try {
      const saved = await saveChatbotWorkflow({
        id: selectedWorkflowId ?? undefined,
        name: flowName,
        is_active: isActive,
        flow_data,
      });
      const list = await refreshWorkflowList();
      setWorkflows(list);
      setSelectedWorkflowId(saved.id);
      setIsDraft(false);
      setFlowName(saved.name);
      setIsActive(saved.is_active);
      setIsSystemFlow(saved.is_system);
      setIsDirty(false);
      setSaveState("saved");
      toast.success("Estrutura de fluxo salva com sucesso.");
    } catch (err) {
      setSaveState("idle");
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao salvar o fluxo." }));
    }
  }

  function handleLoadTemplate(id: FlowTemplateId) {
    builderRef.current?.loadTemplate(id);
    setIsDirty(true);
  }

  function handleAddBlock(type: FlowNodeType) {
    builderRef.current?.addBlock(type);
    setIsDirty(true);
  }

  const saveDisabled = !isDirty && !isDraft && selectedWorkflowId !== null;

  return (
    <>
      <PageMeta
        title="Fluxos do Chatbot | MarketChat"
        description="Construtor visual de fluxos WhatsApp"
        noIndex
      />

      <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
        <ChatbotFlowWorkspace
          loading={loading || canvasLoading}
          builderRef={builderRef}
          canvasKey={canvasKey}
          initialFlow={initialFlow}
          defaultOwnerPhone={defaultOwnerPhone}
          workflows={workflows}
          selectedWorkflowId={selectedWorkflowId}
          isDraft={isDraft}
          flowName={flowName}
          isActive={isActive}
          isSystemFlow={isSystemFlow}
          sidebarTab={sidebarTab}
          builderTabDisabled={builderTabDisabled}
          saveState={saveState}
          saveDisabled={saveDisabled}
          togglingId={togglingId}
          onTabChange={setSidebarTab}
          onCreateBlank={handleCreateBlank}
          onSelectWorkflow={(id) => void loadWorkflow(id)}
          onToggleActive={(id, active) => void handleToggleActive(id, active)}
          onRenameList={openRenameFromList}
          onDuplicate={(id) => void handleDuplicate(id)}
          onDeleteList={openDelete}
          onOpenSettings={openRenameFromTopBar}
          onSave={() => void handleSave()}
          onFlowChange={() => setIsDirty(true)}
          onLoadTemplate={handleLoadTemplate}
          onAddBlock={handleAddBlock}
        />
      </div>

      <ChatbotFlowRenameModal
        isOpen={renameOpen}
        busy={renameBusy}
        initialName={renameTarget?.name ?? flowName}
        onClose={() => setRenameOpen(false)}
        onConfirm={(name) => void handleRenameConfirm(name)}
      />

      <ChatbotFlowDeleteConfirmModal
        isOpen={deleteOpen}
        busy={deleteBusy}
        flowName={deleteTarget?.name}
        onClose={() => setDeleteOpen(false)}
        onConfirm={() => void handleDeleteConfirm()}
      />
    </>
  );
}
