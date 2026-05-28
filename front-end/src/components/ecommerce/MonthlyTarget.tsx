import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";
import MetricHelpTooltip from "../ui/help-tooltip/MetricHelpTooltip";
import type { ChatbotAnalyticsRetention } from "../../features/chatbotAnalytics/types";
import { formatCount } from "../../features/chatbotAnalytics/format";
import { METRIC_HELP_TEXTS } from "../../features/chatbotAnalytics/metricHelpTexts";

type Props = {
  retention: ChatbotAnalyticsRetention | null;
  loading?: boolean;
};

export default function MonthlyTarget({ retention, loading = false }: Props) {
  const rate = retention?.retention_rate ?? 0;
  const series = [loading ? 0 : rate];

  const options: ApexOptions = {
    colors: ["#465FFF"],
    chart: {
      fontFamily: "Outfit, sans-serif",
      type: "radialBar",
      height: 330,
      sparkline: {
        enabled: true,
      },
    },
    plotOptions: {
      radialBar: {
        startAngle: -85,
        endAngle: 85,
        hollow: {
          size: "80%",
        },
        track: {
          background: "#E4E7EC",
          strokeWidth: "100%",
          margin: 5,
        },
        dataLabels: {
          name: {
            show: false,
          },
          value: {
            fontSize: "36px",
            fontWeight: "600",
            offsetY: -40,
            color: "#1D2939",
            formatter(val) {
              return `${Number(val).toFixed(1)}%`;
            },
          },
        },
      },
    },
    fill: {
      type: "solid",
      colors: ["#465FFF"],
    },
    stroke: {
      lineCap: "round",
    },
    labels: ["Retenção"],
  };

  return (
    <div className="rounded-2xl border border-gray-200 bg-gray-100 dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="rounded-2xl bg-white px-5 pb-11 pt-5 shadow-default dark:bg-gray-900 sm:px-6 sm:pt-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
            Taxa de retenção (IA)
          </h3>
          <p className="mt-1 text-theme-sm text-gray-500 dark:text-gray-400">
            Conversas resolvidas pelo bot sem incidentes críticos no mês
          </p>
        </div>
        <div className="relative max-h-[330px]">
          <Chart options={options} series={series} type="radialBar" height={330} />
        </div>
        <p className="mx-auto mt-6 w-full max-w-[380px] text-center text-sm text-gray-500 sm:text-base">
          {loading
            ? "Carregando métricas…"
            : "Percentual de atendimentos resolvidos automaticamente (compra, estoque ou dúvida geral) sem escalonamento crítico."}
        </p>
      </div>

      <div className="flex items-center justify-center gap-5 px-6 py-3.5 sm:gap-8 sm:py-5">
        <div>
          <div className="mb-1 flex justify-center">
            <MetricHelpTooltip
              label="Sessões automatizadas"
              helpText={METRIC_HELP_TEXTS.automatedSessions}
              className="justify-center"
            />
          </div>
          <p className="text-center text-base font-semibold text-gray-800 dark:text-white/90 sm:text-lg">
            {loading ? "—" : formatCount(retention?.automated_sessions_count ?? 0)}
          </p>
        </div>

        <div className="h-7 w-px bg-gray-200 dark:bg-gray-800" />

        <div>
          <div className="mb-1 flex justify-center">
            <MetricHelpTooltip
              label="Chamados de suporte"
              helpText={METRIC_HELP_TEXTS.supportTickets}
              className="justify-center"
            />
          </div>
          <p className="text-center text-base font-semibold text-gray-800 dark:text-white/90 sm:text-lg">
            {loading ? "—" : formatCount(retention?.support_tickets_count ?? 0)}
          </p>
        </div>

        <div className="h-7 w-px bg-gray-200 dark:bg-gray-800" />

        <div>
          <div className="mb-1 flex justify-center">
            <MetricHelpTooltip
              label="Sessões canceladas"
              helpText={METRIC_HELP_TEXTS.cancelledSessions}
              className="justify-center"
            />
          </div>
          <p className="text-center text-base font-semibold text-gray-800 dark:text-white/90 sm:text-lg">
            {loading ? "—" : formatCount(retention?.cancelled_sessions_count ?? 0)}
          </p>
        </div>
      </div>
    </div>
  );
}
