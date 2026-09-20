import { useQuery } from "@tanstack/react-query";
import { settingsApi } from "@/api/endpoints";
import { useI18n } from "@/i18n";
import { openTelegramLink } from "@/lib/telegram";
import { Spinner } from "./ui";

// Blocks the app until the user is subscribed to all required channels.
// Membership is always verified server-side (never a frontend checkbox).
export function SubscriptionGate({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["subscription"],
    queryFn: settingsApi.subscription,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner className="h-8 w-8 text-brand-500" />
      </div>
    );
  }

  if (data && !data.subscribed && data.channels.length > 0) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-6 text-center gap-5 animate-fade-in">
        <div className="text-6xl animate-float">📢</div>
        <div>
          <h1 className="text-xl font-bold">{t("sub_title")}</h1>
          <p className="text-tg-hint text-sm mt-1">{t("sub_desc")}</p>
        </div>
        <div className="w-full max-w-sm space-y-2">
          {data.channels.map((c) => (
            <button
              key={c.id}
              className="btn-ghost w-full justify-between"
              onClick={() => openTelegramLink(c.url)}
            >
              <span>{c.title || c.username}</span>
              <span>↗</span>
            </button>
          ))}
        </div>
        <button className="btn-primary w-full max-w-sm" onClick={() => refetch()} disabled={isRefetching}>
          {isRefetching ? <Spinner className="h-5 w-5" /> : t("sub_check")}
        </button>
      </div>
    );
  }

  return <>{children}</>;
}
