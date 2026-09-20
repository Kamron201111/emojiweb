import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useI18n } from "@/i18n";
import { settingsApi } from "@/api/endpoints";
import { CustomEmoji } from "@/components/CustomEmoji";
import { Badge } from "@/components/ui";
import { haptic } from "@/lib/telegram";
import type { CustomEmojiKey } from "@/lib/customEmoji";

const CATS: {
  kind: string;
  route: string;
  titleKey: Parameters<ReturnType<typeof useI18n>["t"]>[0];
  descKey: Parameters<ReturnType<typeof useI18n>["t"]>[0];
  emoji: CustomEmojiKey;
  priceKey: string;
}[] = [
  { kind: "name", route: "/studio/name", titleKey: "cat_name", descKey: "cat_name_desc", emoji: "lightning", priceKey: "name" },
  { kind: "logo", route: "/studio/logo", titleKey: "cat_logo", descKey: "cat_logo_desc", emoji: "black_star", priceKey: "logo" },
  { kind: "logo2", route: "/studio/logo2", titleKey: "cat_extra1", descKey: "cat_extra1_desc", emoji: "gold_star", priceKey: "logo2" },
  { kind: "logo3", route: "/studio/logo3", titleKey: "cat_extra2", descKey: "cat_extra2_desc", emoji: "green_check", priceKey: "logo3" },
  { kind: "pf", route: "/studio/pf", titleKey: "cat_pf", descKey: "cat_pf_desc", emoji: "fire", priceKey: "pf" },
];

export default function CreatePage() {
  const nav = useNavigate();
  const { t } = useI18n();
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: settingsApi.get });

  return (
    <div className="px-4 pt-5">
      <h1 className="text-2xl font-extrabold mb-1">{t("nav_create")}</h1>
      <p className="text-tg-hint text-sm mb-5">Premium emoji design studio</p>

      <div className="space-y-3">
        {CATS.map((c) => (
          <button
            key={c.kind}
            onClick={() => {
              haptic("medium");
              nav(c.route);
            }}
            className="card p-4 w-full flex items-center gap-4 text-left active:scale-[0.98] transition-transform"
          >
            <div className="h-14 w-14 rounded-2xl bg-tg-card-2 flex items-center justify-center text-2xl shrink-0">
              <CustomEmoji name={c.emoji} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-bold">{t(c.titleKey)}</p>
              <p className="text-xs text-tg-hint">{t(c.descKey)}</p>
            </div>
            <div className="text-right">
              {settings?.prices?.[c.priceKey] != null && (
                <Badge tone="gold">{settings.prices[c.priceKey]} ⭐</Badge>
              )}
              <div className="text-tg-hint mt-1">→</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
