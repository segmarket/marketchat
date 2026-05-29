import { Navigate, Route, Routes } from "react-router";
import ProtectedRoute from "../components/auth/ProtectedRoute";
import AppLayout from "../layout/AppLayout";
import LoginPage from "../pages/auth/LoginPage";
import SignupPage from "../pages/auth/SignupPage";
import ResetPasswordPage from "../pages/auth/ResetPasswordPage";
import Home from "../pages/Dashboard/Home";
import SettingsPage from "../pages/admin/SettingsPage";
import ChatbotFlowsPage from "../pages/admin/ChatbotFlowsPage";
import ChatLogsPage from "../pages/admin/ChatLogsPage";
import SalesDashboard from "../pages/admin/SalesDashboard";
import ResidentsPage from "../pages/admin/ResidentsPage";
import ProductsPage from "../pages/admin/ProductsPage";
import SupportHistoryPage from "../pages/admin/SupportHistoryPage";
import NotFound from "../pages/OtherPage/NotFound";
import BillingBlocked from "../pages/admin/BillingBlocked";
import TrialExpired from "../pages/admin/TrialExpired";
import AppRootRedirect from "./AppRootRedirect";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<AppRootRedirect />} />

      <Route path="/signin" element={<LoginPage />} />
      <Route path="/login" element={<Navigate to="/signin" replace />} />
      <Route path="/auth/signup" element={<SignupPage />} />
      <Route path="/signup" element={<Navigate to="/auth/signup" replace />} />
      <Route path="/register" element={<SignupPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/admin/trial-expired" element={<TrialExpired />} />
        <Route path="/admin/billing-blocked" element={<BillingBlocked />} />
        <Route path="/admin" element={<AppLayout />}>
          <Route index element={<Home />} />
          <Route path="chat-logs" element={<ChatLogsPage />} />
          <Route path="sales" element={<SalesDashboard />} />
          <Route path="residents" element={<ResidentsPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="support" element={<SupportHistoryPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="chatbot-flows" element={<ChatbotFlowsPage />} />

          <Route
            path="markets"
            element={<Navigate to="/admin/settings?section=markets" replace />}
          />
          <Route
            path="billing"
            element={<Navigate to="/admin/settings?tab=plan" replace />}
          />
          <Route
            path="integrations"
            element={<Navigate to="/admin/settings?section=integrations" replace />}
          />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
