import { BrowserRouter as Router } from "react-router";
import { ScrollToTop } from "./components/common/ScrollToTop";
import AppRoutes from "./routes/AppRoutes";
import MarketingRoutes from "./routes/MarketingRoutes";
import { isAppHost } from "./utils/host";

export default function App() {
  const onAppHost = isAppHost();

  return (
    <Router>
      <ScrollToTop />
      {onAppHost ? <AppRoutes /> : <MarketingRoutes />}
    </Router>
  );
}
