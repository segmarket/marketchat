import { Check, Circle } from "lucide-react";
import { Link } from "react-router";
import Button from "../ui/button/Button";
import type { OnboardingStatus } from "../../features/onboarding/types";

type Mission = {
  key: keyof Pick<
    OnboardingStatus,
    | "step_market_created"
    | "step_product_created"
    | "step_whatsapp_connected"
    | "step_test_order_completed"
  >;
  title: string;
  description: string;
  href: string;
};

const MISSIONS: Mission[] = [
  {
    key: "step_market_created",
    title: "Mercado",
    description: "Cadastrar o 1º Condomínio",
    href: "/admin/settings?section=markets",
  },
  {
    key: "step_product_created",
    title: "Estoque",
    description: "Cadastrar o 1º Produto",
    href: "/admin/products",
  },
  {
    key: "step_whatsapp_connected",
    title: "Conexão",
    description: "Conectar o Robô do WhatsApp",
    href: "/admin/settings?section=integrations",
  },
  {
    key: "step_test_order_completed",
    title: "Auditoria",
    description: "Simular 1º Pedido de Teste",
    href: "/admin/sales",
  },
];

type Props = {
  status: OnboardingStatus;
  dismissBusy?: boolean;
  onDismiss: () => void;
};

export default function OnboardingJourneyCard({ status, dismissBusy = false, onDismiss }: Props) {
  const allDone = status.completion_percent >= 100;

  return (
    <section className="mb-6 rounded-2xl border border-gray-200 bg-white p-5 shadow-theme-sm dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
      <header className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white/90">
          Construindo seu Mercado Inteligente ({status.completed_count}/4 Missões Concluídas)
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Complete o setup para liberar o monitoramento em tempo real.
        </p>
      </header>

      <div className="mb-6 h-2.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-800">
        <div
          className="h-full rounded-full bg-green-500 transition-all duration-500 ease-out"
          style={{ width: `${status.completion_percent}%` }}
          role="progressbar"
          aria-valuenow={status.completion_percent}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>

      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {MISSIONS.map((mission) => {
          const done = status[mission.key];
          return (
            <li key={mission.key}>
              <Link
                to={mission.href}
                className={`flex h-full flex-col rounded-xl border p-4 transition-colors hover:bg-gray-50 dark:hover:bg-white/[0.03] ${
                  done
                    ? "border-green-200 bg-green-50/50 dark:border-green-900/40 dark:bg-green-950/20"
                    : "border-gray-200 dark:border-gray-800"
                }`}
              >
                <div className="mb-3 flex items-center gap-2">
                  {done ? (
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-500 text-white">
                      <Check className="size-3.5" aria-hidden />
                    </span>
                  ) : (
                    <span className="flex h-6 w-6 items-center justify-center rounded-full border border-gray-300 text-gray-400 dark:border-gray-600">
                      <Circle className="size-3" aria-hidden />
                    </span>
                  )}
                  <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    {mission.title}
                  </span>
                </div>
                <span
                  className={`text-sm font-medium ${
                    done ? "text-green-700 dark:text-green-400" : "text-gray-800 dark:text-white/90"
                  }`}
                >
                  {mission.description}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>

      {allDone ? (
        <div className="mt-6 flex justify-end">
          <Button onClick={onDismiss} disabled={dismissBusy}>
            {dismissBusy ? "Finalizando…" : "Tudo Pronto! Começar a Faturar"}
          </Button>
        </div>
      ) : null}
    </section>
  );
}
