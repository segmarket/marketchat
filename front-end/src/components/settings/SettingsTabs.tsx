import type { SettingsTabId } from "../../features/settings/types";

type SettingsTabsProps = {
  activeTab: SettingsTabId;
  onChange: (tab: SettingsTabId) => void;
  showBillingTabs: boolean;
};

const TABS: { id: SettingsTabId; label: string; billingOnly?: boolean }[] = [
  { id: "account", label: "Minha Conta" },
  { id: "plan", label: "Plano e Pagamento", billingOnly: true },
  { id: "history", label: "Histórico de Faturas", billingOnly: true },
];

export default function SettingsTabs({ activeTab, onChange, showBillingTabs }: SettingsTabsProps) {
  const visible = TABS.filter((t) => !t.billingOnly || showBillingTabs);

  const tabClass = (id: SettingsTabId) =>
    activeTab === id
      ? "shadow-theme-xs text-gray-900 dark:text-white bg-white dark:bg-gray-800"
      : "text-gray-500 dark:text-gray-400";

  return (
    <div className="flex flex-wrap items-center gap-0.5 rounded-lg bg-gray-100 p-0.5 dark:bg-gray-900">
      {visible.map((tab) => (
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
