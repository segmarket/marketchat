import type { IntegrationsTabId } from "../../features/integrations/types";

type Props = {
  activeTab: IntegrationsTabId;
  onChange: (tab: IntegrationsTabId) => void;
};

const TABS: { id: IntegrationsTabId; label: string }[] = [
  { id: "whatsapp", label: "WhatsApp" },
  { id: "pix", label: "Recebimentos" },
];

export default function IntegrationsTabs({ activeTab, onChange }: Props) {
  const tabClass = (id: IntegrationsTabId) =>
    activeTab === id
      ? "shadow-theme-xs text-gray-900 dark:text-white bg-white dark:bg-gray-800"
      : "text-gray-500 dark:text-gray-400";

  return (
    <div className="mb-6 flex flex-wrap items-center gap-0.5 rounded-lg bg-gray-100 p-0.5 dark:bg-gray-900">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`rounded-md px-3 py-2 text-theme-sm font-medium hover:text-gray-900 dark:hover:text-white ${tabClass(tab.id)}`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
