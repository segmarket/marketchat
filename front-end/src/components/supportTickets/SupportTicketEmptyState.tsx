import { MessageSquare } from "lucide-react";

export default function SupportTicketEmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-8 py-12 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-gray-100 dark:bg-gray-800">
        <MessageSquare className="size-7 text-gray-400 dark:text-gray-500" strokeWidth={1.5} />
      </div>
      <div className="max-w-sm space-y-2">
        <p className="text-sm font-medium text-gray-800 dark:text-white/90">
          Nenhum chamado selecionado
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Selecione um chamado da lista para ver o histórico ou clique em ajuda para abrir um novo.
        </p>
      </div>
    </div>
  );
}
