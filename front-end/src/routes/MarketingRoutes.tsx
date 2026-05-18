import { Navigate, Route, Routes } from "react-router";
import LandingPage from "../pages/marketing/LandingPage";

export default function MarketingRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
