export type InboxTab = "waiting" | "bot" | "all";

type Props = {
  value: InboxTab;
  onChange: (tab: InboxTab) => void;
};

const TABS: { id: InboxTab; label: string }[] = [
  { id: "all", label: "Todos" },
  { id: "waiting", label: "Aguardando" },
  { id: "bot", label: "Bot" },
];

export default function InboxTabs({ value, onChange }: Props) {
  return (
    <div className="flex gap-1 border-b border-gray-200 px-2 pt-2 dark:border-gray-800">
      {TABS.map((tab) => {
        const active = value === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`flex-1 rounded-t-lg px-2 py-2.5 text-sm font-medium transition-colors ${
              active
                ? "bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300"
                : "text-gray-500 hover:bg-gray-50 hover:text-gray-800 dark:hover:bg-white/5 dark:hover:text-white/80"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
