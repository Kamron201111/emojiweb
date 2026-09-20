import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { referralsApi } from "@/api/endpoints";
import { useI18n } from "@/i18n";
import { Skeleton } from "@/components/ui";
import { shareLink, haptic } from "@/lib/telegram";

export default function ReferralPage() {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const { data, isLoading } = useQuery({ queryKey: ["referrals"], queryFn: referralsApi.get });

  const copy = async () => {
    if (!data) return;
    try {
      await navigator.clipboard.writeText(data.link);
      setCopied(true);
      haptic("success");
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="px-4 pt-5">
      <div className="card p-6 text-center bg-gradient-to-br from-brand-600/20 to-fuchsia-600/10 mb-5 relative overflow-hidden">
        <div className="absolute -right-4 -top-4 text-6xl opacity-20 animate-float">🎁</div>
        <div className="text-5xl mb-2">🎉</div>
        <h1 className="text-xl font-extrabold">{t("ref_title")}</h1>
        <p className="text-tg-hint text-sm mt-1">{t("ref_desc")}</p>
      </div>

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (
        data && (
          <>
            <div className="grid grid-cols-3 gap-3 mb-5">
              <Stat label={t("invited")} value={data.invited_count} />
              <Stat label={t("successful")} value={data.successful_count} />
              <Stat label={t("earned_credits")} value={data.earned_credits} accent />
            </div>

            <div className="card p-4 mb-3">
              <p className="text-xs text-tg-hint mb-2">{t("ref_link")}</p>
              <div className="flex items-center gap-2">
                <input readOnly value={data.link} className="input flex-1 text-xs" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button className="btn-ghost" onClick={copy}>
                {copied ? `✓ ${t("copied")}` : t("copy_link")}
              </button>
              <button
                className="btn-primary"
                onClick={() => shareLink(data.link, t("ref_desc"))}
              >
                {t("share_telegram")}
              </button>
            </div>
          </>
        )
      )}
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className="card p-4 text-center">
      <p className={`text-2xl font-extrabold ${accent ? "text-gold" : "text-brand-400"}`}>{value}</p>
      <p className="text-[10px] text-tg-hint mt-1">{label}</p>
    </div>
  );
}
