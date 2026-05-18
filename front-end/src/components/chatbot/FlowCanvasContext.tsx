import { createContext, useContext } from "react";

export const FlowCanvasReadOnlyContext = createContext(false);

export function useFlowCanvasReadOnly(): boolean {
  return useContext(FlowCanvasReadOnlyContext);
}
