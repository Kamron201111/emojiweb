import { NavLink } from "react-router-dom";
import { useI18n } from "@/i18n";
import { useAppStore } from "@/store/appStore";
import { haptic } from "@/lib/telegram";

const items = [
  { to: "/", key: "nav_home", icon: "🏠", exact: true },
  { to: "/create", key: "nav_create", icon: "✨" },
  { to: "/packs", key: "nav_packs", icon: "🗂️" },
  { to: "/referral", key: "nav_referral", icon: "🎁" },
  { to: "/profile", key: "nav_profile", icon: "👤" },
] as const;

export function BottomNav() {
  const { t } = useI18n();
  const isAdmin = useAppStore((s) => s.user?.is_admin);

  const nav = isAdmin
    ? [...items, { to: "/admin", key: "nav_admin" as const, icon: "🛡️" }]
    : items;

  return (
    <nav className="fixed bottom-0 inset-x-0 z-40">
      <div className="mx-auto max-w-lg px-3 pb-[env(safe-area-inset-bottom)]">
        <div className="mb-2 rounded-3xl bg-tg-card/90 backdrop-blur-xl border border-tg-border shadow-soft flex justify-around py-1.5">
          {nav.map((it) => (
            <NavLink
              key={it.to}
              to={it.to}
              end={"exact" in it ? it.exact : false}
              onClick={() => haptic("select")}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center gap-0.5 px-3 py-1.5 rounded-2xl transition-all ${
                  isActive ? "text-brand-400" : "text-tg-hint"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span className={`text-xl transition-transform ${isActive ? "scale-110" : ""}`}>{it.icon}</span>
                  <span className="text-[10px] font-medium">{t(it.key)}</span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}
