import { useEffect, useRef } from "react";
import { NotificationsProvider } from "../context/NotificationsContext";
import { SidebarProvider, useSidebar } from "../context/SidebarContext";
import { Outlet, useLocation } from "react-router";
import GracePeriodBanner from "../components/billing/GracePeriodBanner";
import { useAuth } from "../context/AuthContext";
import BillingBlocked from "../pages/admin/BillingBlocked";
import TrialExpired from "../pages/admin/TrialExpired";
import SupportCopilot from "../components/support/SupportCopilot";
import WhatsNewModal from "../components/whatsNew/WhatsNewModal";
import AppHeader from "./AppHeader";
import Backdrop from "./Backdrop";
import AppSidebar from "./AppSidebar";

const FULLSCREEN_ROUTES = ["/admin/chatbot-flows", "/admin/chat-logs"];
/** Rotas que pausam o poll global de notificações (canvas pesado). */
const PAUSE_NOTIFICATION_POLL_ROUTES = ["/admin/chatbot-flows"];
/** Rotas em que o botão flutuante do Support Copilot atrapalha a UI. */
const HIDE_SUPPORT_COPILOT_ROUTES = ["/admin/chat-logs"];

const LayoutContent: React.FC = () => {
  const { isExpanded, isHovered, isMobileOpen, closeMobileSidebar } = useSidebar();
  const { pathname, search } = useLocation();
  const prevRoute = useRef(`${pathname}${search}`);
  const { user } = useAuth();

  useEffect(() => {
    const route = `${pathname}${search}`;
    if (prevRoute.current !== route) {
      closeMobileSidebar();
      prevRoute.current = route;
    }
  }, [pathname, search, closeMobileSidebar]);
  const isFullscreen = FULLSCREEN_ROUTES.some((route) => pathname.startsWith(route));
  const pauseNotificationPoll = PAUSE_NOTIFICATION_POLL_ROUTES.some((route) =>
    pathname.startsWith(route),
  );
  const hideSupportCopilot = HIDE_SUPPORT_COPILOT_ROUTES.some((route) =>
    pathname.startsWith(route),
  );
  const onBillingSettings = pathname.startsWith("/admin/settings");
  const onBillingBlocked = pathname.startsWith("/admin/billing-blocked");

  if (user?.subscription_status === "SUSPENDED" && !onBillingSettings && !onBillingBlocked) {
    return <BillingBlocked />;
  }

  if (user?.trial_expired && !onBillingSettings) {
    return <TrialExpired />;
  }

  return (
    <NotificationsProvider pollingEnabled={!pauseNotificationPoll}>
      <div className={`${isFullscreen ? "h-dvh overflow-hidden" : "min-h-screen"} xl:flex`}>
        <div>
          <AppSidebar />
          <Backdrop />
        </div>
        <div
          className={`flex min-h-0 min-w-0 w-full flex-1 flex-col transition-all duration-300 ease-in-out ${
            isFullscreen ? "h-full overflow-hidden" : ""
          } ${
            isExpanded || isHovered ? "lg:ml-[290px]" : "lg:ml-[90px]"
          } ${isMobileOpen ? "ml-0" : ""}`}
        >
          <GracePeriodBanner />
          <AppHeader />
          <div
            className={
              isFullscreen
                ? "flex min-h-0 flex-1 flex-col overflow-hidden"
                : "flex min-w-0 w-full flex-1 px-4 py-4 md:px-8 md:py-6"
            }
          >
            <Outlet />
          </div>
        </div>
      </div>
      {!hideSupportCopilot ? <SupportCopilot /> : null}
      <WhatsNewModal />
    </NotificationsProvider>
  );
};

const AppLayout: React.FC = () => {
  return (
    <SidebarProvider>
      <LayoutContent />
    </SidebarProvider>
  );
};

export default AppLayout;
