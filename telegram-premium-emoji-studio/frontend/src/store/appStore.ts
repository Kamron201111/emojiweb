import { create } from "zustand";
import type { Lang, UserPublic } from "@/types";

type Theme = "light" | "dark";

interface AppState {
  user: UserPublic | null;
  lang: Lang;
  theme: Theme;
  authReady: boolean;
  authError: string | null;
  setUser: (u: UserPublic | null) => void;
  setLang: (l: Lang) => void;
  setTheme: (t: Theme) => void;
  setAuthReady: (v: boolean) => void;
  setAuthError: (e: string | null) => void;
  patchCredits: (delta: number) => void;
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  lang: (localStorage.getItem("lang") as Lang) || "uz",
  theme: (localStorage.getItem("theme") as Theme) || "dark",
  authReady: false,
  authError: null,
  setUser: (user) => set({ user }),
  setLang: (lang) => {
    localStorage.setItem("lang", lang);
    set({ lang });
  },
  setTheme: (theme) => {
    localStorage.setItem("theme", theme);
    document.documentElement.classList.toggle("dark", theme === "dark");
    set({ theme });
  },
  setAuthReady: (authReady) => set({ authReady }),
  setAuthError: (authError) => set({ authError }),
  patchCredits: (delta) =>
    set((s) => (s.user ? { user: { ...s.user, credits: s.user.credits + delta } } : {})),
}));
