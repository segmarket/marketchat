import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import confetti from "canvas-confetti";
import { toast } from "sonner";
import AdminPageLayout from "../../components/layout/AdminPageShell";
import Label from "../../components/form/Label";
import ChartsBlurGuard from "../../components/onboarding/ChartsBlurGuard";
import OnboardingJourneyCard from "../../components/onboarding/OnboardingJourneyCard";
import EcommerceMetrics from "../../components/ecommerce/EcommerceMetrics";
import MonthlySalesChart from "../../components/ecommerce/MonthlySalesChart";
import StatisticsChart from "../../components/ecommerce/StatisticsChart";
import MonthlyTarget from "../../components/ecommerce/MonthlyTarget";
import { fetchChatbotAnalytics } from "../../features/chatbotAnalytics/api";
import type { ChatbotAnalyticsResponse } from "../../features/chatbotAnalytics/types";
import { dismissOnboarding, fetchOnboardingStatus } from "../../features/onboarding/api";
import type { OnboardingStatus } from "../../features/onboarding/types";
import { fetchResidentMarkets } from "../../features/residents/api";
import type { ResidentMarketOption } from "../../features/residents/types";
import { getAxiosErrorMessage } from "../../utils/apiError";

function fireOnboardingConfetti() {
  const duration = 2500;
  const end = Date.now() + duration;

  const frame = () => {
    confetti({
      particleCount: 3,
      angle: 60,
      spread: 55,
      origin: { x: 0, y: 0.65 },
    });
    confetti({
      particleCount: 3,
      angle: 120,
      spread: 55,
      origin: { x: 1, y: 0.65 },
    });
    if (Date.now() < end) {
      requestAnimationFrame(frame);
    }
  };

  confetti({
    particleCount: 120,
    spread: 70,
    origin: { y: 0.6 },
  });
  frame();
}

export default function Home() {
  const { pathname } = useLocation();
  const [analytics, setAnalytics] = useState<ChatbotAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [markets, setMarkets] = useState<ResidentMarketOption[]>([]);
  const [marketId, setMarketId] = useState<number | "">("");
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const [onboardingLoading, setOnboardingLoading] = useState(true);
  const [dismissBusy, setDismissBusy] = useState(false);
  const confettiFiredRef = useRef(false);

  const loadMarkets = useCallback(async () => {
    try {
      const data = await fetchResidentMarkets();
      setMarkets(data);
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar condomínios." }),
      );
    }
  }, []);

  const loadAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchChatbotAnalytics(marketId === "" ? null : Number(marketId));
      setAnalytics(data);
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, {
          notAxiosMessage: "Não foi possível carregar o monitoramento.",
        }),
      );
    } finally {
      setLoading(false);
    }
  }, [marketId]);

  const loadOnboarding = useCallback(async () => {
    setOnboardingLoading(true);
    try {
      const data = await fetchOnboardingStatus();
      setOnboarding(data);

      if (
        data.completion_percent >= 100
        && !data.onboarding_finished
        && !confettiFiredRef.current
      ) {
        confettiFiredRef.current = true;
        fireOnboardingConfetti();
      }
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, {
          notAxiosMessage: "Não foi possível carregar o progresso do onboarding.",
        }),
      );
    } finally {
      setOnboardingLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMarkets();
  }, [loadMarkets]);

  useEffect(() => {
    void loadAnalytics();
  }, [loadAnalytics]);

  useEffect(() => {
    if (pathname !== "/admin" && pathname !== "/admin/") return;
    confettiFiredRef.current = false;
    void loadOnboarding();
  }, [pathname, loadOnboarding]);

  useEffect(() => {
    function onFocus() {
      if (pathname === "/admin" || pathname === "/admin/") {
        void loadOnboarding();
      }
    }
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [pathname, loadOnboarding]);

  async function handleDismissOnboarding() {
    setDismissBusy(true);
    try {
      const data = await dismissOnboarding();
      setOnboarding(data);
      toast.success("Setup concluído. Boas vendas!");
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível finalizar." }));
    } finally {
      setDismissBusy(false);
    }
  }

  const chartsLocked =
    onboarding !== null
    && !onboarding.onboarding_finished
    && onboarding.completion_percent < 75;

  const showMissionPanel = Boolean(onboarding?.show_mission_panel);

  return (
    <AdminPageLayout
      pageTitle="Dashboard"
      metaTitle="Dashboard | MarketChat"
      metaDescription="Saúde operacional do chatbot WhatsApp e volume de atendimentos"
      description="Interações, retenção da IA e incidentes do mês atual."
    >
      {showMissionPanel && onboarding && !onboardingLoading ? (
        <OnboardingJourneyCard
          status={onboarding}
          dismissBusy={dismissBusy}
          onDismiss={() => void handleDismissOnboarding()}
        />
      ) : null}

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-end">
        <div className="w-full sm:max-w-xs">
          <Label htmlFor="dashboard-market">Condomínio</Label>
          <select
            id="dashboard-market"
            value={marketId}
            onChange={(e) => {
              const value = e.target.value;
              setMarketId(value === "" ? "" : Number(value));
            }}
            className="mt-1 h-11 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-800 outline-none focus:border-brand-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
          >
            <option value="">Todos os condomínios</option>
            {markets.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4 md:gap-6">
        <div className="col-span-12 space-y-6 xl:col-span-7">
          <EcommerceMetrics cards={analytics?.cards ?? null} loading={loading} />
          <ChartsBlurGuard locked={chartsLocked}>
            <MonthlySalesChart
              hourlyDistribution={analytics?.hourly_distribution}
              loading={loading}
            />
          </ChartsBlurGuard>
        </div>

        <div className="col-span-12 xl:col-span-5">
          <ChartsBlurGuard locked={chartsLocked}>
            <MonthlyTarget retention={analytics?.retention ?? null} loading={loading} />
          </ChartsBlurGuard>
        </div>

        <div className="col-span-12">
          <ChartsBlurGuard locked={chartsLocked}>
            <StatisticsChart
              stabilitySeries={analytics?.stability_series}
              stabilityMarketNames={analytics?.stability_market_names}
              loading={loading}
            />
          </ChartsBlurGuard>
        </div>
      </div>
    </AdminPageLayout>
  );
}
