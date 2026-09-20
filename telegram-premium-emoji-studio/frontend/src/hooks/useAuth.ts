import { useEffect } from "react";
import { authApi } from "@/api/endpoints";
import { loadStoredToken, setSessionToken } from "@/api/client";
import { getInitData, initTelegram, detectColorScheme } from "@/lib/telegram";
import { useAppStore } from "@/store/appStore";

// Boots the Telegram runtime, validates initData against the backend, and
// hydrates the app store with the authenticated user.
export function useAuthBootstrap() {
  const { setUser, setLang, setTheme, setAuthReady, setAuthError } = useAppStore();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      initTelegram();
      setTheme(detectColorScheme());
      loadStoredToken();

      const initData = getInitData();
      if (!initData) {
        // Outside Telegram (dev). Surface a friendly message but keep the UI.
        setAuthError("Telegram ichida oching (initData topilmadi)");
        setAuthReady(true);
        return;
      }
      try {
        const res = await authApi.login(initData);
        if (cancelled) return;
        setSessionToken(res.token);
        setUser(res.user);
        setLang(res.user.language);
        setAuthError(null);
      } catch (e) {
        if (!cancelled) setAuthError(e instanceof Error ? e.message : "Auth error");
      } finally {
        if (!cancelled) setAuthReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
