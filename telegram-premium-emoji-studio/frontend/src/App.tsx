import { Routes, Route, useLocation } from "react-router-dom";
import { useAuthBootstrap } from "@/hooks/useAuth";
import { useAppStore } from "@/store/appStore";
import { I18nProvider } from "@/i18n";
import { BottomNav } from "@/components/BottomNav";
import { Spinner } from "@/components/ui";
import { SubscriptionGate } from "@/components/SubscriptionGate";

import HomePage from "@/pages/HomePage";
import CreatePage from "@/pages/CreatePage";
import StudioPage from "@/pages/StudioPage";
import PacksPage from "@/pages/PacksPage";
import ReferralPage from "@/pages/ReferralPage";
import ProfilePage from "@/pages/ProfilePage";
import HelpPage from "@/pages/HelpPage";
import GiftPage from "@/pages/GiftPage";
import AdminPage from "@/pages/AdminPage";

function BootScreen({ message }: { message?: string }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-6 text-center">
      <div className="text-5xl animate-float">✨</div>
      <Spinner className="h-8 w-8 text-brand-500" />
      <p className="text-tg-hint text-sm">{message || "Premium Emoji Studio"}</p>
    </div>
  );
}

export default function App() {
  useAuthBootstrap();
  const { lang, authReady, authError, user } = useAppStore();
  const location = useLocation();

  return (
    <I18nProvider lang={lang}>
      {!authReady ? (
        <BootScreen />
      ) : authError && !user ? (
        <BootScreen message={authError} />
      ) : (
        <SubscriptionGate>
          <div className="mx-auto max-w-lg min-h-screen safe-bottom">
            <div key={location.pathname} className="animate-fade-in">
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/create" element={<CreatePage />} />
                <Route path="/studio/:kind" element={<StudioPage />} />
                <Route path="/packs" element={<PacksPage />} />
                <Route path="/referral" element={<ReferralPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/help" element={<HelpPage />} />
                <Route path="/gift" element={<GiftPage />} />
                <Route path="/admin" element={<AdminPage />} />
              </Routes>
            </div>
          </div>
          <BottomNav />
        </SubscriptionGate>
      )}
    </I18nProvider>
  );
}
