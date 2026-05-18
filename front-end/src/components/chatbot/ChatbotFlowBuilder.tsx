import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef } from "react";
import { FlowCanvasReadOnlyContext } from "./FlowCanvasContext";
import { toast } from "sonner";
import { applyDefaultOwnerPhone } from "../../features/chatbot/flowDefaults";
import { chatbotNodeTypes } from "../../features/chatbot/nodeTypes";
import { getFlowTemplates, type FlowTemplateId } from "../../features/chatbot/templates";
import type { FlowData, FlowNode, FlowNodeType } from "../../features/chatbot/types";

export type ChatbotFlowBuilderHandle = {
  getFlowData: () => FlowData;
  loadTemplate: (id: FlowTemplateId) => void;
  addBlock: (type: FlowNodeType) => void;
};

type BuilderInnerProps = {
  initialFlow: FlowData | null;
  defaultOwnerPhone: string;
  readOnly?: boolean;
  onFlowChange?: () => void;
};

function defaultNodeData(type: FlowNodeType, defaultOwnerPhone: string): FlowNode["data"] {
  const ownerDigits = defaultOwnerPhone.replace(/\D/g, "");
  switch (type) {
    case "trigger":
      return { label: "Quando o Morador enviar uma mensagem..." };
    case "ai_filter":
      return {
        label: "IA analisa a intenção",
        intents: ["reclamação"],
        systemPrompt: "",
      };
    case "response":
      return {
        label: "Resposta automática",
        message: "",
      };
    case "owner_alert":
      return {
        label: "Alerta ao dono",
        ownerPhone: ownerDigits,
        messageTemplate: "Alerta: {name} ({phone}) — {text}",
      };
    default:
      return { label: "" };
  }
}

function BuilderInner(
  { initialFlow, defaultOwnerPhone, readOnly = false, onFlowChange }: BuilderInnerProps,
  ref: React.Ref<ChatbotFlowBuilderHandle>,
) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { fitView, getViewport, setViewport } = useReactFlow();
  const normalizedInitial = initialFlow
    ? applyDefaultOwnerPhone(initialFlow, defaultOwnerPhone)
    : null;
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>(normalizedInitial?.nodes ?? []);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(normalizedInitial?.edges ?? []);
  const blockCounter = useRef(0);

  useEffect(() => {
    if (!initialFlow) return;
    const flow = applyDefaultOwnerPhone(initialFlow, defaultOwnerPhone);
    setNodes(flow.nodes ?? []);
    setEdges(flow.edges ?? []);
    if (flow.viewport) {
      setViewport(flow.viewport);
    } else {
      void fitView({ padding: 0.2 });
    }
  }, [initialFlow, defaultOwnerPhone, setNodes, setEdges, setViewport, fitView]);

  const notifyChange = useCallback(() => {
    onFlowChange?.();
  }, [onFlowChange]);

  const wrappedOnNodesChange = useCallback(
    (...args: Parameters<typeof onNodesChange>) => {
      onNodesChange(...args);
      notifyChange();
    },
    [onNodesChange, notifyChange],
  );

  const wrappedOnEdgesChange = useCallback(
    (...args: Parameters<typeof onEdgesChange>) => {
      onEdgesChange(...args);
      notifyChange();
    },
    [onEdgesChange, notifyChange],
  );

  useImperativeHandle(ref, () => ({
    getFlowData: () => ({
      nodes,
      edges,
      viewport: getViewport(),
    }),
    loadTemplate: (id: FlowTemplateId) => {
      if (readOnly) return;
      const tpl = getFlowTemplates(defaultOwnerPhone).find((t) => t.id === id);
      if (!tpl) return;
      const flow = applyDefaultOwnerPhone(tpl.build(), defaultOwnerPhone, true);
      setNodes(flow.nodes);
      setEdges(flow.edges);
      if (flow.viewport) {
        setViewport(flow.viewport);
      } else {
        void fitView({ padding: 0.2 });
      }
      notifyChange();
      toast.message("Template carregado. Clique em Salvar para persistir.");
    },
    addBlock: (type: FlowNodeType) => {
      if (readOnly) return;
      blockCounter.current += 1;
      const id = `${type}-${Date.now()}-${blockCounter.current}`;
      const newNode: FlowNode = {
        id,
        type,
        position: { x: 120 + blockCounter.current * 24, y: 120 + blockCounter.current * 24 },
        data: defaultNodeData(type, defaultOwnerPhone),
      };
      setNodes((nds) => [...nds, newNode]);
      notifyChange();
    },
  }));

  const onConnect = useCallback(
    (connection: Connection) => {
      if (readOnly) return;
      setEdges((eds) => addEdge(connection, eds));
      notifyChange();
    },
    [readOnly, setEdges, notifyChange],
  );

  return (
    <div
      ref={reactFlowWrapper}
      className="h-full w-full bg-slate-50 dark:bg-gray-950/50"
    >
      <FlowCanvasReadOnlyContext.Provider value={readOnly}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={readOnly ? undefined : wrappedOnNodesChange}
        onEdgesChange={readOnly ? undefined : wrappedOnEdgesChange}
        onConnect={onConnect}
        nodeTypes={chatbotNodeTypes}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        elementsSelectable={!readOnly}
        fitView
        deleteKeyCode={readOnly ? null : ["Backspace", "Delete"]}
        className="!h-full !w-full bg-slate-50 dark:bg-gray-950/50"
      >
        <Background gap={16} size={1} color="#d1d5db" />
        <Controls className="!rounded-lg !border-gray-200 !shadow-theme-sm dark:!border-gray-700 dark:!bg-gray-900" />
        <MiniMap
          className="!rounded-lg !border-gray-200 dark:!border-gray-700"
          maskColor="rgba(0,0,0,0.08)"
        />
      </ReactFlow>
      </FlowCanvasReadOnlyContext.Provider>
    </div>
  );
}

const BuilderInnerWithRef = forwardRef(BuilderInner);

type Props = {
  initialFlow: FlowData | null;
  defaultOwnerPhone: string;
  readOnly?: boolean;
  onFlowChange?: () => void;
};

const ChatbotFlowBuilder = forwardRef<ChatbotFlowBuilderHandle, Props>(function ChatbotFlowBuilder(
  { initialFlow, defaultOwnerPhone, readOnly, onFlowChange },
  ref,
) {
  return (
    <div className="h-full w-full">
      <ReactFlowProvider>
        <BuilderInnerWithRef
          ref={ref}
          initialFlow={initialFlow}
          defaultOwnerPhone={defaultOwnerPhone}
          readOnly={readOnly}
          onFlowChange={onFlowChange}
        />
      </ReactFlowProvider>
    </div>
  );
});

export default ChatbotFlowBuilder;
