import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";
import type { HourlyDistributionBucket } from "../../features/chatbotAnalytics/types";

const DEFAULT_BUCKETS: HourlyDistributionBucket[] = [
  { label: "00h-06h", count: 0 },
  { label: "06h-12h", count: 0 },
  { label: "12h-18h", count: 0 },
  { label: "18h-00h", count: 0 },
];

type Props = {
  hourlyDistribution?: HourlyDistributionBucket[];
  loading?: boolean;
};

export default function MonthlySalesChart({
  hourlyDistribution = DEFAULT_BUCKETS,
  loading = false,
}: Props) {
  const categories = hourlyDistribution.map((b) => b.label);
  const data = hourlyDistribution.map((b) => (loading ? 0 : b.count));

  const options: ApexOptions = {
    colors: ["#465fff"],
    chart: {
      fontFamily: "Outfit, sans-serif",
      type: "bar",
      height: 180,
      toolbar: {
        show: false,
      },
    },
    plotOptions: {
      bar: {
        horizontal: false,
        columnWidth: "39%",
        borderRadius: 5,
        borderRadiusApplication: "end",
      },
    },
    dataLabels: {
      enabled: false,
    },
    stroke: {
      show: true,
      width: 4,
      colors: ["transparent"],
    },
    xaxis: {
      categories,
      axisBorder: {
        show: false,
      },
      axisTicks: {
        show: false,
      },
    },
    legend: {
      show: true,
      position: "top",
      horizontalAlign: "left",
      fontFamily: "Outfit",
    },
    yaxis: {
      title: {
        text: undefined,
      },
    },
    grid: {
      yaxis: {
        lines: {
          show: true,
        },
      },
    },
    fill: {
      opacity: 1,
    },
    tooltip: {
      x: {
        show: false,
      },
      y: {
        formatter: (val: number) => `${val}`,
      },
    },
  };

  const series = [
    {
      name: "Atendimentos",
      data,
    },
  ];

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white px-5 pt-5 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6 sm:pt-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
            Volume por horário
          </h3>
          <p className="mt-1 text-theme-sm text-gray-500 dark:text-gray-400">
            Início dos atendimentos no mês atual
          </p>
        </div>
      </div>

      <div className="custom-scrollbar max-w-full overflow-x-auto">
        <div className="-ml-5 min-w-[400px] pl-2 xl:min-w-full">
          <Chart options={options} series={series} type="bar" height={180} />
        </div>
      </div>
    </div>
  );
}
