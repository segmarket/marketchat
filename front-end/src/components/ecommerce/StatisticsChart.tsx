import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";
import type { StabilitySeriesPoint } from "../../features/chatbotAnalytics/types";
import { formatChartDate } from "../../features/chatbotAnalytics/format";

type Props = {
  stabilitySeries?: StabilitySeriesPoint[];
  loading?: boolean;
};

export default function StatisticsChart({
  stabilitySeries = [],
  loading = false,
}: Props) {
  const categories = stabilitySeries.map((p) => formatChartDate(p.date));
  const totalData = stabilitySeries.map((p) => (loading ? 0 : p.line_total_sessions));
  const frictionData = stabilitySeries.map((p) => (loading ? 0 : p.line_friction_points));

  const options: ApexOptions = {
    legend: {
      show: true,
      position: "top",
      horizontalAlign: "left",
      fontFamily: "Outfit, sans-serif",
    },
    colors: ["#465FFF", "#9CB9FF"],
    chart: {
      fontFamily: "Outfit, sans-serif",
      height: 310,
      type: "line",
      toolbar: {
        show: false,
      },
    },
    stroke: {
      curve: "straight",
      width: [2, 2],
    },
    fill: {
      type: "gradient",
      gradient: {
        opacityFrom: 0.55,
        opacityTo: 0,
      },
    },
    markers: {
      size: 0,
      strokeColors: "#fff",
      strokeWidth: 2,
      hover: {
        size: 6,
      },
    },
    grid: {
      xaxis: {
        lines: {
          show: false,
        },
      },
      yaxis: {
        lines: {
          show: true,
        },
      },
    },
    dataLabels: {
      enabled: false,
    },
    tooltip: {
      enabled: true,
    },
    xaxis: {
      type: "category",
      categories,
      axisBorder: {
        show: false,
      },
      axisTicks: {
        show: false,
      },
      labels: {
        rotate: -45,
        style: {
          fontSize: "11px",
        },
      },
    },
    yaxis: {
      labels: {
        style: {
          fontSize: "12px",
          colors: ["#6B7280"],
        },
      },
      title: {
        text: "",
        style: {
          fontSize: "0px",
        },
      },
    },
  };

  const series = [
    {
      name: "Interações",
      data: totalData,
    },
    {
      name: "Pontos de atrito",
      data: frictionData,
    },
  ];

  return (
    <div className="rounded-2xl border border-gray-200 bg-white px-5 pb-5 pt-5 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6 sm:pt-6">
      <div className="mb-6 w-full">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
          Estabilidade (30 dias)
        </h3>
        <p className="mt-1 text-theme-sm text-gray-500 dark:text-gray-400">
          Volume diário de interações vs. incidentes de atrito
        </p>
      </div>

      <div className="custom-scrollbar max-w-full overflow-x-auto">
        <div className="min-w-[700px] xl:min-w-full">
          <Chart options={options} series={series} type="area" height={310} />
        </div>
      </div>
    </div>
  );
}
