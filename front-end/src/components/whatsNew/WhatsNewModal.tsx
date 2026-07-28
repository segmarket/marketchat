import { useEffect, useState } from "react";
import {
  Clock,
  ListChecks,
  MessagesSquare,
  Power,
  Receipt,
  type LucideIcon,
} from "lucide-react";
import {
  CHANGELOG_ITEMS,
  CURRENT_VERSION,
  LAST_SEEN_VERSION_KEY,
  type ChangelogIconName,
} from "../../features/whatsNew/changelogData";
import Button from "../ui/button/Button";
import { Modal } from "../ui/modal";

const ICON_MAP: Record<ChangelogIconName, LucideIcon> = {
  Clock,
  Power,
  MessagesSquare,
  Receipt,
  ListChecks,
};

function markVersionSeen() {
  try {
    localStorage.setItem(LAST_SEEN_VERSION_KEY, CURRENT_VERSION);
  } catch {
    // localStorage indisponível (modo privado restrito, etc.)
  }
}

function shouldShowWhatsNew(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const seen = localStorage.getItem(LAST_SEEN_VERSION_KEY);
    return seen !== CURRENT_VERSION;
  } catch {
    return false;
  }
}

export default function WhatsNewModal() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(shouldShowWhatsNew());
  }, []);

  function dismiss() {
    markVersionSeen();
    setOpen(false);
  }

  return (
    <Modal isOpen={open} onClose={dismiss} className="mx-4 max-w-lg p-6 sm:p-8">
      <div className="pr-8">
        <p className="text-sm font-medium text-brand-500 dark:text-brand-400">
          Atualização
        </p>
        <h2 className="mt-1 text-xl font-semibold text-gray-900 dark:text-white sm:text-2xl">
          Novidades da Versão {CURRENT_VERSION}
        </h2>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Confira o que melhoramos para deixar o atendimento ainda mais ágil.
        </p>
      </div>

      <ul className="mt-6 space-y-4">
        {CHANGELOG_ITEMS.map((item) => {
          const Icon = ICON_MAP[item.icon];
          return (
            <li key={item.id} className="flex gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400">
                <Icon className="size-5" aria-hidden />
              </span>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                  {item.title}
                </h3>
                <p className="mt-0.5 text-sm text-gray-600 dark:text-gray-400">
                  {item.description}
                </p>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="mt-8 flex justify-end">
        <Button type="button" variant="primary" onClick={dismiss} className="min-w-36">
          Entendi
        </Button>
      </div>
    </Modal>
  );
}
