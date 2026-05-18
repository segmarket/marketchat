import type { HealthStatus } from "../../../features/integrations/types";

type Props = {
  evolutionApiStatus: HealthStatus;
  webhookStatus: HealthStatus;
};

function HealthLed({ status }: { status: HealthStatus }) {
  const color =
    status === "ok"
      ? "bg-success-500"
      : status === "error"
        ? "bg-error-500"
        : "bg-gray-400";
  return <span className={`h-3 w-3 shrink-0 rounded-full ${color}`} aria-hidden />;
}

function HealthCard({
  title,
  subtitle,
  status,
}: {
  title: string;
  subtitle: string;
  status: HealthStatus;
}) {
  const label = status === "ok" ? "Operacional" : status === "error" ? "Indisponível" : "Desconhecido";
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-gray-800 dark:text-white/90">{title}</p>
          <p className="mt-1 text-theme-xs text-gray-500 dark:text-gray-400">{subtitle}</p>
        </div>
        <HealthLed status={status} />
      </div>
      <p className="mt-3 text-theme-sm font-medium text-gray-700 dark:text-gray-300">{label}</p>
    </div>
  );
}

export default function WhatsappHealthGrid({ evolutionApiStatus, webhookStatus }: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <HealthCard
        title="Evolution API"
        subtitle="Serviço de conexão WhatsApp"
        status={evolutionApiStatus}
      />
      <HealthCard
        title="Webhook"
        subtitle="Eventos recebidos nos últimos 10 min"
        status={webhookStatus}
      />
    </div>
  );
}
