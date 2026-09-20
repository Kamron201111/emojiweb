import { useNavigate } from "react-router-dom";
import { useAppStore } from "@/store/appStore";
import { useI18n } from "@/i18n";
import { CustomEmoji } from "@/components/CustomEmoji";
import { haptic } from "@/lib/telegram";
import type { CustomEmojiKey } from "@/lib/customEmoji";

interface Cat {
  kind: string;
  route: string;
  titleKey: Parameters<ReturnType<typeof useI18n>["t"]>[0];
  descKey: Parameters<ReturnType<typeof useI18n>["t"]>[0];
  emoji: CustomEmojiKey;
  gradient: string;
}

const CATEGORIES: Cat[] = [
  { kind: "name", route: "/studio/name", titleKey: "cat_name", descKey: "cat_name_desc", emoji: "lightning", gradient: "from-indigo-500 to-purple-600" },
  { kind: "logo", route: "/studio/logo", titleKey: "cat_logo", descKey: "cat_logo_desc", emoji: "black_star", gradient: "from-fuchsia-500 to-pink-600" },
  { kind: "logo2", route: "/studio/logo2", titleKey: "cat_extra1", descKey: "cat_extra1_desc", emoji: "gold_star", gradient: "from-amber-400 to-orange-600" },
  { kind: "logo3", route: "/studio/logo3", titleKey: "cat_extra2", descKey: "cat_extra2_desc", emoji: "green_check", gradient: "from-emerald-400 to-teal-600" },
  { kind: "pf", route: "/studio/pf", titleKey: "cat_pf", descKey: "cat_pf_desc", emoji: "fire", gradient: "from-rose-500 to-red-600" },
];

const QUICK = [
  { route: "/packs", titleKey: "cat_packs", emoji: "🗂️" },
  { route: "/gift", titleKey: "gift_title", emoji: "⭐" },
  { route: "/referral", titleKey: "cat_referral", emoji: "🎁" },
  { route: "/help", titleKey: "cat_help", emoji: "🆘" },
] as const;

export default function HomePage() {
  const nav = useNavigate();
  const { t } = useI18n();
  const user = useAppStore((s) => s.user);

  const go = (route: string) => {
    haptic("medium");
    nav(route);
  };

  return (
    <div className="px-4 pt-4">
      {/* Header */}
      <header className="flex items-center gap-3 mb-6">
        <div className="h-12 w-12 rounded-2xl overflow-hidden bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white font-bold text-lg shadow-glow">
          {user?.photo_url ? (
            <img src={user.photo_url} alt="" className="h-full w-full object-cover" />
          ) : (
            (user?.first_name?.[0] || "U").toUpperCase()
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-tg-hint">{t("greeting")}</p>
          <p className="font-bold truncate">{user?.full_name || user?.username || "User"}</p>
        </div>
        <button
          onClick={() => go("/profile")}
          className="chip border border-tg-border"
          title={t("free_credits")}
        >
          <CustomEmoji name="stars" /> {user?.credits ?? 0}
        </button>
      </header>

      {/* Hero */}
      <div className="card p-5 mb-6 bg-gradient-to-br from-brand-600/20 to-fuchsia-600/10 relative overflow-hidden">
        <div className="absolute -right-6 -top-6 text-7xl opacity-20 animate-float">✨</div>
        <h1 className="text-xl font-extrabold leading-tight">Premium Emoji Studio</h1>
        <p className="text-tg-hint text-sm mt-1 max-w-[85%]">
          {t("cat_name_desc")} • {t("cat_logo_desc")}
        </p>
        <button className="btn-primary mt-4" onClick={() => go("/create")}>
          {t("nav_create")} →
        </button>
      </div>

      {/* Category cards */}
      <h2 className="text-base font-bold mb-3">{t("nav_create")}</h2>
      <div className="grid grid-cols-2 gap-3 mb-6">
        {CATEGORIES.map((c) => (
          <button
            key={c.kind}
            onClick={() => go(c.route)}
            className="card p-4 text-left relative overflow-hidden active:scale-[0.97] transition-transform"
          >
            <div className={`h-11 w-11 rounded-2xl bg-gradient-to-br ${c.gradient} flex items-center justify-center text-xl mb-3 shadow-soft`}>
              <CustomEmoji name={c.emoji} className="text-white" />
            </div>
            <p className="font-bold text-sm">{t(c.titleKey)}</p>
            <p className="text-[11px] text-tg-hint mt-0.5">{t(c.descKey)}</p>
          </button>
        ))}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-4 gap-2.5">
        {QUICK.map((q) => (
          <button key={q.route} onClick={() => go(q.route)} className="card p-3 flex flex-col items-center gap-1.5 active:scale-95 transition-transform">
            <span className="text-2xl">{q.emoji}</span>
            <span className="text-[10px] text-tg-hint text-center leading-tight">{t(q.titleKey)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
