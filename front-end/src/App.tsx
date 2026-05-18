import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router";
import LoginPage from "./pages/auth/LoginPage";
import SignupPage from "./pages/auth/SignupPage";
import ResetPasswordPage from "./pages/auth/ResetPasswordPage";
import NotFound from "./pages/OtherPage/NotFound";
import UserProfiles from "./pages/UserProfiles";
import Videos from "./pages/UiElements/Videos";
import Images from "./pages/UiElements/Images";
import Alerts from "./pages/UiElements/Alerts";
import Badges from "./pages/UiElements/Badges";
import Avatars from "./pages/UiElements/Avatars";
import Buttons from "./pages/UiElements/Buttons";
import LineChart from "./pages/Charts/LineChart";
import BarChart from "./pages/Charts/BarChart";
import Calendar from "./pages/Calendar";
import BasicTables from "./pages/Tables/BasicTables";
import FormElements from "./pages/Forms/FormElements";
import Blank from "./pages/Blank";
import AppLayout from "./layout/AppLayout";
import { ScrollToTop } from "./components/common/ScrollToTop";
import Home from "./pages/Dashboard/Home";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import BillingPage from "./pages/admin/BillingPage";
import SettingsPage from "./pages/admin/SettingsPage";
import IntegrationsPage from "./pages/admin/IntegrationsPage";
import ProductsPage from "./pages/admin/ProductsPage";
import MarketsPage from "./pages/admin/MarketsPage";
import ResidentsPage from "./pages/admin/ResidentsPage";
import ChatbotFlowsPage from "./pages/admin/ChatbotFlowsPage";

export default function App() {
  return (
    <Router>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<Navigate to="/admin" replace />} />

        <Route path="/login" element={<LoginPage />} />
        <Route path="/signin" element={<Navigate to="/login" replace />} />
        <Route path="/auth/signup" element={<SignupPage />} />
        <Route path="/signup" element={<Navigate to="/auth/signup" replace />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/admin" element={<AppLayout />}>
            <Route index element={<Home />} />
            <Route path="billing" element={<BillingPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="integrations" element={<IntegrationsPage />} />
            <Route path="products" element={<ProductsPage />} />
            <Route path="markets" element={<MarketsPage />} />
            <Route path="residents" element={<ResidentsPage />} />
            <Route path="chatbot-flows" element={<ChatbotFlowsPage />} />
            <Route path="profile" element={<UserProfiles />} />
            <Route path="calendar" element={<Calendar />} />
            <Route path="blank" element={<Blank />} />
            <Route path="form-elements" element={<FormElements />} />
            <Route path="basic-tables" element={<BasicTables />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="avatars" element={<Avatars />} />
            <Route path="badge" element={<Badges />} />
            <Route path="buttons" element={<Buttons />} />
            <Route path="images" element={<Images />} />
            <Route path="videos" element={<Videos />} />
            <Route path="line-chart" element={<LineChart />} />
            <Route path="bar-chart" element={<BarChart />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}
