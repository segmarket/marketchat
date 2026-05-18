import type { SettingsSectionId } from "../../features/settings/types";

type NavItem = {
  id: SettingsSectionId;
  label: string;
  adminOnly?: boolean;
  integrationsOnly?: boolean;
};

const NAV_ITEMS: NavItem[] = [
  { id: "markets", label: "Mercados" },
  { id: "integrations", label: "Integrações", integrationsOnly: true },
  { id: "account", label: "Minha conta" },
  { id: "plan", label: "Plano e pagamento", adminOnly: true },
  { id: "history", label: "Histórico de faturas", adminOnly: true },
];

type Props = {
  active: SettingsSectionId;
  showBilling: boolean;
  showIntegrations: boolean;
  onChange: (id: SettingsSectionId) => void;
};

export default function SettingsNav({
  active,
  showBilling,
  showIntegrations,
  onChange,
}: Props) {
  const visible = NAV_ITEMS.filter((item) => {
    if (item.adminOnly && !showBilling) return false;
    if (item.integrationsOnly && !showIntegrations) return false;
    return true;
  });

  return (
    <nav className="flex flex-col gap-1">
      {visible.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onChange(item.id)}
          className={`rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
            active === item.id
              ? "bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-400"
              : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/5"
          }`}
        >
          {item.label}
        </button>
      ))}
    </nav>
  );
}
