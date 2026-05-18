import { Copy, Lock, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import type { ChatbotWorkflowSummary } from "../../features/chatbot/types";
import { Dropdown } from "../ui/dropdown/Dropdown";
import { DropdownItem } from "../ui/dropdown/DropdownItem";

type Props = {
  workflow: ChatbotWorkflowSummary;
  selected: boolean;
  togglingActive: boolean;
  onSelect: () => void;
  onToggleActive: (active: boolean) => void;
  onRename: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
};

function FlowActiveToggle({
  active,
  disabled,
  onChange,
}: {
  active: boolean;
  disabled: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={active}
      disabled={disabled}
      onClick={(e) => {
        e.stopPropagation();
        if (!disabled) onChange(!active);
      }}
      className={`relative h-6 w-11 shrink-0 rounded-full transition ${
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"
      } ${active ? "bg-brand-500" : "bg-gray-200 dark:bg-white/10"}`}
    >
      <span
        className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow-theme-sm transition-transform ${
          active ? "translate-x-5" : "translate-x-0"
        }`}
      />
    </button>
  );
}

export default function FlowListItem({
  workflow,
  selected,
  togglingActive,
  onSelect,
  onToggleActive,
  onRename,
  onDuplicate,
  onDelete,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const isSystem = workflow.is_system;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2.5 transition ${
        selected
          ? "border-brand-500 bg-brand-50 dark:border-brand-600 dark:bg-brand-500/10"
          : "border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-900 dark:hover:border-gray-600"
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          {isSystem && <Lock className="h-3.5 w-3.5 shrink-0 text-brand-500" aria-hidden />}
          <p className="truncate text-sm font-medium text-gray-800 dark:text-white/90">{workflow.name}</p>
          {isSystem && (
            <span className="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400">
              Sistema
            </span>
          )}
        </div>
        {workflow.is_active ? (
          <span className="text-xs text-success-500">● Ativo</span>
        ) : (
          <span className="text-xs text-gray-400">○ Inativo</span>
        )}
      </div>
      <FlowActiveToggle
        active={workflow.is_active}
        disabled={togglingActive}
        onChange={onToggleActive}
      />
      <div className="relative">
        <button
          type="button"
          className="dropdown-toggle flex h-8 w-8 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
          onClick={(e) => {
            e.stopPropagation();
            setMenuOpen((v) => !v);
          }}
          aria-label="Ações do fluxo"
        >
          <MoreHorizontal className="h-4 w-4" />
        </button>
        <Dropdown isOpen={menuOpen} onClose={() => setMenuOpen(false)} className="w-44 py-1">
          {!isSystem && (
            <DropdownItem
              onClick={() => {
                setMenuOpen(false);
                onRename();
              }}
              className="flex items-center gap-2 px-4 py-2 text-sm"
            >
              <Pencil className="h-4 w-4" />
              Renomear
            </DropdownItem>
          )}
          <DropdownItem
            onClick={() => {
              setMenuOpen(false);
              onDuplicate();
            }}
            className="flex items-center gap-2 px-4 py-2 text-sm"
          >
            <Copy className="h-4 w-4" />
            Duplicar
          </DropdownItem>
          {!isSystem && (
            <DropdownItem
              onClick={() => {
                setMenuOpen(false);
                onDelete();
              }}
              className="flex items-center gap-2 px-4 py-2 text-sm text-error-600 dark:text-error-500"
            >
              <Trash2 className="h-4 w-4" />
              Excluir
            </DropdownItem>
          )}
        </Dropdown>
      </div>
    </div>
  );
}
