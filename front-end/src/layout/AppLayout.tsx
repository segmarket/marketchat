import { NotificationsProvider } from "../context/NotificationsContext";
import { SidebarProvider, useSidebar } from "../context/SidebarContext";
import { Outlet, useLocation } from "react-router";
import GracePeriodBanner from "../components/billing/GracePeriodBanner";
import { useAuth } from "../context/AuthContext";
import BillingBlocked from "../pages/admin/BillingBlocked";
import TrialExpired from "../pages/admin/TrialExpired";
import AppHeader from "./AppHeader";
import Backdrop from "./Backdrop";
import AppSidebar from "./AppSidebar";

const FULLSCREEN_ROUTES = ["/admin/chatbot-flows"];

const LayoutContent: React.FC = () => {
  const { isExpanded, isHovered, isMobileOpen } = useSidebar();
  const { pathname } = useLocation();
  const { user } = useAuth();
  const isFullscreen = FULLSCREEN_ROUTES.some((route) => pathname.startsWith(route));
  const onBillingSettings = pathname.startsWith("/admin/settings");
  const onBillingBlocked = pathname.startsWith("/admin/billing-blocked");

  if (user?.subscription_status === "SUSPENDED" && !onBillingSettings && !onBillingBlocked) {
    return <BillingBlocked />;
  }

  if (user?.trial_expired && !onBillingSettings) {
    return <TrialExpired />;
  }

  return (
    <NotificationsProvider pollingEnabled={!isFullscreen}>
      <div className="min-h-screen xl:flex">
        <div>
          <AppSidebar />
          <Backdrop />
        </div>
        <div
          className={`flex min-h-0 min-w-0 w-full flex-1 flex-col transition-all duration-300 ease-in-out ${
            isExpanded || isHovered ? "lg:ml-[290px]" : "lg:ml-[90px]"
          } ${isMobileOpen ? "ml-0" : ""}`}
        >
          <GracePeriodBanner />
          <AppHeader />
          <div
            className={
              isFullscreen
                ? "flex min-h-0 flex-1 flex-col overflow-hidden"
                : "w-full min-w-0 max-w-(--breakpoint-2xl) flex-1 p-4 md:p-6"
            }
          >
            <Outlet />
          </div>
        </div>
      </div>
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
