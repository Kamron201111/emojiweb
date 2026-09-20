import { useEffect, useMemo, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { catalogApi } from "@/api/endpoints";
import type { TemplateItem } from "@/types";
import { Skeleton, EmptyState, ErrorState } from "./ui";
import { useI18n } from "@/i18n";
import { haptic } from "@/lib/telegram";

const PAGE_SIZE = 24;

// A visual, paginated (lazy-loading) template gallery with search and select.
export function TemplateGallery({
  kind,
  selectedId,
  onSelect,
}: {
  kind: string;
  selectedId: string | null;
  onSelect: (item: TemplateItem) => void;
}) {
  const { t } = useI18n();
  const [search, setSearch] = useState("");

  const query = useInfiniteQuery({
    queryKey: ["templates", kind],
    initialPageParam: 1,
    queryFn: ({ pageParam }) => catalogApi.templates(kind, pageParam as number, PAGE_SIZE),
    getNextPageParam: (last) => {
      const loaded = last.page * last.page_size;
      return loaded < last.total ? last.page + 1 : undefined;
    },
  });

  const items = useMemo(() => {
    const all = query.data?.pages.flatMap((p) => p.items) ?? [];
    if (!search.trim()) return all;
    const s = search.trim().toLowerCase();
    return all.filter(
      (i) => i.label.toLowerCase().includes(s) || i.id.includes(s) || String(i.number ?? "").includes(s)
    );
  }, [query.data, search]);

  // Auto-load next page when scrolling near bottom.
  useEffect(() => {
    const onScroll = (e: Event) => {
      const el = e.target as HTMLElement;
      if (el.scrollHeight - el.scrollTop - el.clientHeight < 240 && query.hasNextPage && !query.isFetchingNextPage) {
        query.fetchNextPage();
      }
    };
    const container = document.getElementById("gallery-scroll");
    container?.addEventListener("scroll", onScroll);
    return () => container?.removeEventListener("scroll", onScroll);
  }, [query]);

  if (query.isError) {
    return <ErrorState message={t("error")} onRetry={() => query.refetch()} retryLabel={t("retry")} />;
  }

  return (
    <div>
      <input
        className="input mb-3"
        placeholder={t("search")}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <div id="gallery-scroll" className="grid grid-cols-3 gap-2.5 max-h-[52vh] overflow-y-auto no-scrollbar pb-2">
        {query.isLoading &&
          Array.from({ length: 9 }).map((_, i) => <Skeleton key={i} className="aspect-square" />)}

        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => {
              haptic("select");
              onSelect(item);
            }}
            className={`relative aspect-square rounded-2xl border p-2 flex flex-col items-center justify-center gap-1 transition-all active:scale-95 ${
              selectedId === item.id
                ? "border-brand-500 bg-brand-500/10 ring-2 ring-brand-500"
                : "border-tg-border bg-tg-card-2"
            }`}
          >
            <div className="text-2xl font-black text-tg-hint">{item.number ?? "Aa"}</div>
            <div className="text-[10px] text-tg-hint truncate w-full text-center">{item.label}</div>
            {selectedId === item.id && (
              <span className="absolute top-1 right-1 h-4 w-4 rounded-full bg-brand-500 text-white text-[10px] flex items-center justify-center">
                ✓
              </span>
            )}
          </button>
        ))}

        {query.isFetchingNextPage &&
          Array.from({ length: 3 }).map((_, i) => <Skeleton key={`n${i}`} className="aspect-square" />)}
      </div>

      {!query.isLoading && items.length === 0 && <EmptyState title={t("empty")} />}
    </div>
  );
}
