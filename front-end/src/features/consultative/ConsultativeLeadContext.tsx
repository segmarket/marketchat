import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import ConsultativeLeadFormModal from "../../components/marketing/ConsultativeLeadFormModal";

type ConsultativeLeadContextValue = {
  openLeadForm: () => void;
  closeLeadForm: () => void;
  isLeadFormOpen: boolean;
};

const ConsultativeLeadContext = createContext<ConsultativeLeadContextValue | null>(null);

export function ConsultativeLeadProvider({ children }: { children: ReactNode }) {
  const [isLeadFormOpen, setIsLeadFormOpen] = useState(false);

  const openLeadForm = useCallback(() => setIsLeadFormOpen(true), []);
  const closeLeadForm = useCallback(() => setIsLeadFormOpen(false), []);

  const value = useMemo(
    () => ({ openLeadForm, closeLeadForm, isLeadFormOpen }),
    [openLeadForm, closeLeadForm, isLeadFormOpen],
  );

  return (
    <ConsultativeLeadContext.Provider value={value}>
      {children}
      <ConsultativeLeadFormModal isOpen={isLeadFormOpen} onClose={closeLeadForm} />
    </ConsultativeLeadContext.Provider>
  );
}

export function useConsultativeLead() {
  const context = useContext(ConsultativeLeadContext);
  if (!context) {
    throw new Error("useConsultativeLead must be used within ConsultativeLeadProvider");
  }
  return context;
}
