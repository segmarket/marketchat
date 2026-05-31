import { Navigate, Route, Routes } from "react-router";
import RedirectToAppHost from "../components/marketing/RedirectToAppHost";
import LandingPage from "../pages/marketing/LandingPage";
import LinksPage from "../pages/marketing/LinksPage";
import PrivacyPolicyPage from "../pages/marketing/PrivacyPolicyPage";

export default function MarketingRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/privacidade" element={<PrivacyPolicyPage />} />
      <Route path="/links" element={<LinksPage />} />
      <Route path="/reset-password" element={<RedirectToAppHost appPath="/reset-password" />} />
      <Route path="/signin" element={<RedirectToAppHost appPath="/signin" />} />
      <Route path="/login" element={<RedirectToAppHost appPath="/signin" />} />
      <Route path="/auth/signup" element={<RedirectToAppHost appPath="/auth/signup" />} />
      <Route path="/signup" element={<RedirectToAppHost appPath="/auth/signup" />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
