import { useQuery } from "@tanstack/react-query";
import { ordersApi } from "@/api/endpoints";
import { useI18n } from "@/i18n";
import { EmptyState, ErrorState, Skeleton, Badge } from "@/components/ui";

const STATUS_TONE: Record<string, "brand" | "gold" | "green"> = {
  completed: "green",
  paid: "gold",
  generating: "brand",
};

export default function PacksPage() {
  const { t } = useI18n();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["orders"],
    queryFn: ordersApi.list,
  });

  return (
    <div className="px-4 pt-5">
      <h1 className="text-2xl font-extrabold mb-4">{t("cat_packs")}</h1>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      )}

      {isError && <ErrorState message={t("error")} onRetry={() => refetch()} retryLabel={t("retry")} />}

      {data && data.length === 0 && <EmptyState title={t("empty")} hint={t("cat_name_desc")} />}

      <div className="space-y-3">
        {data?.map((o) => (
          <div key={o.id} className="card p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-bold truncate">{o.pack_title || `#${o.id}`}</p>
                <p className="text-xs text-tg-hint mt-0.5">
                  {o.kind} • {o.item_count} • {o.pack_kind}
                </p>
                <p className="text-[11px] text-tg-hint mt-1">
                  {o.created_at ? new Date(o.created_at).toLocaleString() : ""}
                </p>
              </div>
              <div className="text-right shrink-0 space-y-1">
                <Badge tone={STATUS_TONE[o.status] || "brand"}>{o.status}</Badge>
                <p className="text-xs text-tg-hint">
                  {o.payment_method === "credit"
                    ? "🎁 kredit"
                    : o.payment_method === "free"
                    ? "🆓 free"
                    : `${o.total_price} ⭐`}
                </p>
              </div>
            </div>
            {o.pack_url && (
              <a href={o.pack_url} target="_blank" rel="noreferrer" className="btn-ghost w-full mt-3">
                {t("open_telegram")} ↗
              </a>
            )}
            {o.error_message && <p className="text-xs text-red-400 mt-2">{o.error_message}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
