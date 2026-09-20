import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { settingsApi } from "@/api/endpoints";
import { useI18n } from "@/i18n";
import { openTelegramLink } from "@/lib/telegram";

const FAQ = [
  { q: "Emoji qanday yaratiladi?", a: "Bo'lim tanlang, shablon va matn kiriting, ranglarni sozlang, keyin 'Yaratish' tugmasini bosing." },
  { q: "To'lov qanday amalga oshiriladi?", a: "Telegram Stars (⭐) orqali. Yoki bepul kreditingiz bo'lsa, uni ishlatishingiz mumkin." },
  { q: "Bepul kredit qanday olinadi?", a: "Do'stingizni taklif qiling — u birinchi emojisini yasaganda sizga 1 kredit beriladi." },
  { q: "To'plamni qayerdan topaman?", a: "'To'plamlar' bo'limida barcha yaratgan emoji/stikerlaringiz saqlanadi." },
];

export default function HelpPage() {
  const { t } = useI18n();
  const [open, setOpen] = useState<number | null>(0);
  const { data } = useQuery({ queryKey: ["settings"], queryFn: settingsApi.get });

  return (
    <div className="px-4 pt-5">
      <h1 className="text-2xl font-extrabold mb-4">{t("help_title")}</h1>

      <div className="card p-4 mb-5 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold">{t("support_contact")}</p>
          <p className="text-tg-hint text-sm">{data?.support_contact || "@support"}</p>
        </div>
        <button
          className="btn-primary !py-2"
          onClick={() => {
            const c = (data?.support_contact || "").replace("@", "");
            if (c) openTelegramLink(`https://t.me/${c}`);
          }}
        >
          {t("support_contact")}
        </button>
      </div>

      <h2 className="text-base font-bold mb-3">{t("help_faq")}</h2>
      <div className="space-y-2">
        {FAQ.map((f, i) => (
          <div key={i} className="card overflow-hidden">
            <button
              className="w-full flex items-center justify-between p-4 text-left"
              onClick={() => setOpen(open === i ? null : i)}
            >
              <span className="font-semibold text-sm">{f.q}</span>
              <span className={`transition-transform ${open === i ? "rotate-180" : ""}`}>⌄</span>
            </button>
            {open === i && <p className="px-4 pb-4 text-sm text-tg-hint animate-fade-in">{f.a}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
