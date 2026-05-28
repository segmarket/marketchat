import { Navigate, Route, Routes } from "react-router";
import RedirectToAppHost from "../components/marketing/RedirectToAppHost";
import LandingPage from "../pages/marketing/LandingPage";

export default function MarketingRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/reset-password" element={<RedirectToAppHost appPath="/reset-password" />} />
      <Route path="/signin" element={<RedirectToAppHost appPath="/signin" />} />
      <Route path="/login" element={<RedirectToAppHost appPath="/signin" />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
