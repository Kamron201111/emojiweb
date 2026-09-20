import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { paymentsApi, settingsApi } from "@/api/endpoints";
import { useI18n } from "@/i18n";
import { CustomEmoji } from "@/components/CustomEmoji";
import { Spinner } from "@/components/ui";
import { openInvoice, haptic } from "@/lib/telegram";
import { ApiError } from "@/api/client";

const PRESETS = [15, 25, 50, 100, 250, 500];

export default function GiftPage() {
  const { t } = useI18n();
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: settingsApi.get });
  const [amount, setAmount] = useState(50);
  const [phase, setPhase] = useState<"idle" | "loading" | "thanks" | "error">("idle");
  const [error, setError] = useState("");

  const min = settings?.gift_min_amount ?? 1;
  const max = settings?.gift_max_amount ?? 100000;

  const gift = async () => {
    if (amount < min || amount > max) return;
    haptic("medium");
    setPhase("loading");
    try {
      const res = await paymentsApi.gift(amount);
      if (!res.invoice_link) throw new Error("Invoice link yo'q");
      const status = await openInvoice(res.invoice_link);
      setPhase(status === "paid" ? "thanks" : "idle");
      if (status === "paid") haptic("success");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("error"));
      setPhase("error");
    }
  };

  return (
    <div className="px-4 pt-5">
      <div className="card p-6 text-center bg-gradient-to-br from-gold/20 to-amber-600/10 mb-5">
        <div className="text-5xl mb-2 animate-float">⭐</div>
        <h1 className="text-xl font-extrabold">{t("gift_title")}</h1>
      </div>

      {phase === "thanks" ? (
        <div className="card p-8 text-center animate-scale-in">
          <div className="text-6xl mb-3">🙏</div>
          <p className="font-bold">{t("gift_thanks")}</p>
        </div>
      ) : (
        <>
          <p className="text-sm font-semibold mb-3">{t("gift_amount")}</p>
          <div className="grid grid-cols-3 gap-3 mb-4">
            {PRESETS.map((p) => (
              <button
                key={p}
                onClick={() => {
                  haptic("select");
                  setAmount(p);
                }}
                className={`card p-4 font-bold ${amount === p ? "ring-2 ring-brand-500 text-brand-400" : ""}`}
              >
                {p} <CustomEmoji name="stars" />
              </button>
            ))}
          </div>
          <input
            type="number"
            className="input mb-4"
            value={amount}
            min={min}
            max={max}
            onChange={(e) => setAmount(Number(e.target.value))}
          />
          <button className="btn-gold w-full" onClick={gift} disabled={phase === "loading"}>
            {phase === "loading" ? <Spinner className="h-5 w-5" /> : `${amount} ⭐ ${t("gift_title")}`}
          </button>
          {phase === "error" && <p className="text-red-400 text-sm mt-3 text-center">{error}</p>}
        </>
      )}
    </div>
  );
}
