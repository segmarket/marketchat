import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { initConsentDefaults } from "./utils/analytics";
import "./index.css";

initConsentDefaults();
import "swiper/swiper-bundle.css";
import "flatpickr/dist/flatpickr.css";
import { Toaster } from "sonner";
import App from "./App.tsx";
import { AppWrapper } from "./components/common/PageMeta.tsx";
import { ThemeProvider } from "./context/ThemeContext.tsx";
import { AuthProvider } from "./context/AuthContext.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <AppWrapper>
          <Toaster richColors position="top-right" closeButton />
          <App />
        </AppWrapper>
      </AuthProvider>
    </ThemeProvider>
  </StrictMode>,
);
