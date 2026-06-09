import { BrowserRouter as Router } from "react-router";
import { ScrollToTop } from "./components/common/ScrollToTop";
import AppRoutes from "./routes/AppRoutes";
import MarketingRoutes from "./routes/MarketingRoutes";
import { useAnalytics } from "./hooks/useAnalytics";
import { isAppHost } from "./utils/host";

function AnalyticsBootstrap() {
  useAnalytics();
  return null;
}

export default function App() {
  const onAppHost = isAppHost();

  return (
    <Router>
      <AnalyticsBootstrap />
      <ScrollToTop />
      {onAppHost ? <AppRoutes /> : <MarketingRoutes />}
    </Router>
  );
}
