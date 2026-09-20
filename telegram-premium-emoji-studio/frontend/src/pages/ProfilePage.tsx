import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/store/appStore";
import { useI18n } from "@/i18n";
import { meApi } from "@/api/endpoints";
import { CustomEmoji } from "@/components/CustomEmoji";
import { haptic } from "@/lib/telegram";
import type { Lang } from "@/types";

const LANGS: { code: Lang; label: string; flag: string }[] = [
  { code: "uz", label: "O'zbekcha", flag: "🇺🇿" },
  { code: "ru", label: "Русский", flag: "🇷🇺" },
  { code: "en", label: "English", flag: "🇬🇧" },
];

export default function ProfilePage() {
  const nav = useNavigate();
  const { t } = useI18n();
  const { user, lang, setLang, theme, setTheme, setUser } = useAppStore();

  const credits = useQuery({ queryKey: ["credits"], queryFn: meApi.credits });

  const changeLang = async (code: Lang) => {
    haptic("select");
    setLang(code);
    try {
      const updated = await meApi.setLanguage(code);
      setUser(updated);
    } catch {
      /* keep local */
    }
  };

  return (
    <div className="px-4 pt-5">
      <div className="card p-5 flex items-center gap-4 mb-5">
        <div className="h-16 w-16 rounded-2xl overflow-hidden bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white text-2xl font-bold">
          {user?.photo_url ? <img src={user.photo_url} alt="" className="h-full w-full object-cover" /> : (user?.first_name?.[0] || "U").toUpperCase()}
        </div>
        <div className="min-w-0">
          <p className="font-bold text-lg truncate">{user?.full_name || user?.username}</p>
          {user?.username && <p className="text-tg-hint text-sm">@{user.username}</p>}
          {user?.is_admin && <span className="chip border border-brand-500/40 text-brand-400 mt-1">🛡️ Admin</span>}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-5">
        <Stat icon={<CustomEmoji name="stars" />} label={t("free_credits")} value={credits.data?.credits ?? user?.credits ?? 0} />
        <Stat icon="🗂️" label={t("packs_created")} value={user?.packs_created ?? 0} />
        <Stat icon="⭐" label={t("stars_spent")} value={user?.stars_spent ?? 0} />
      </div>

      <div className="card p-4 mb-4">
        <p className="text-sm font-semibold mb-3">{t("language")}</p>
        <div className="grid grid-cols-3 gap-2">
          {LANGS.map((l) => (
            <button
              key={l.code}
              onClick={() => changeLang(l.code)}
              className={`btn ${lang === l.code ? "btn-primary" : "btn-ghost"}`}
            >
              {l.flag} {l.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card p-4 mb-4 flex items-center justify-between">
        <p className="text-sm font-semibold">{t("theme")}</p>
        <button
          className="btn-ghost !py-2"
          onClick={() => {
            haptic("light");
            setTheme(theme === "dark" ? "light" : "dark");
          }}
        >
          {theme === "dark" ? "🌙 Dark" : "☀️ Light"}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <button className="btn-ghost" onClick={() => nav("/gift")}>⭐ {t("gift_title")}</button>
        <button className="btn-ghost" onClick={() => nav("/help")}>🆘 {t("help_title")}</button>
      </div>
    </div>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="card p-4 text-center">
      <div className="text-xl mb-1">{icon}</div>
      <p className="text-xl font-extrabold text-brand-400">{value}</p>
      <p className="text-[10px] text-tg-hint mt-0.5">{label}</p>
    </div>
  );
}
