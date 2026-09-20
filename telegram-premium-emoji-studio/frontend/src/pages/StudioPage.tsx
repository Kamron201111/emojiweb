import { useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useI18n } from "@/i18n";
import { catalogApi, renderApi, type OrderInput } from "@/api/endpoints";
import type { ProductKind, TemplateItem, PackKind } from "@/types";
import { TemplateGallery } from "@/components/TemplateGallery";
import { ColorControl } from "@/components/ColorControl";
import { LottiePlayer } from "@/components/LottiePlayer";
import { CheckoutSheet } from "@/components/CheckoutSheet";
import { Sheet, Spinner, SectionTitle } from "@/components/ui";
import { useDebounced } from "@/hooks/useDebounced";
import { haptic } from "@/lib/telegram";

const VALID: ProductKind[] = ["name", "logo", "logo2", "logo3", "pf"];

const TITLES: Record<ProductKind, string> = {
  name: "Name Emoji Studio",
  logo: "Logo/Text Studio",
  logo2: "Extra Emoji Studio",
  logo3: "Extra Emoji Studio 2",
  pf: "Profil foni Studio",
};

export default function StudioPage() {
  const { kind } = useParams<{ kind: string }>();
  const nav = useNavigate();
  const { t } = useI18n();

  const productKind = (VALID.includes(kind as ProductKind) ? kind : "name") as ProductKind;
  const isLogoLike = productKind !== "name";
  const usesFont = productKind !== "name";
  const maxLen = productKind === "pf" ? 5 : productKind === "name" ? 12 : 32;

  const [text, setText] = useState("");
  const [template, setTemplate] = useState<TemplateItem | null>(null);
  const [outer, setOuter] = useState<string | null>(null);
  const [inner, setInner] = useState<string | null>(null);
  const [color, setColor] = useState<string | null>(null);
  const [fontKey, setFontKey] = useState<string | null>(null);
  const [packKind, setPackKind] = useState<PackKind>("emoji");
  const [packTitle, setPackTitle] = useState("");

  const [galleryOpen, setGalleryOpen] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);

  const fonts = useQuery({
    queryKey: ["fonts", usesFont, productKind],
    queryFn: () => catalogApi.fonts(productKind === "pf"),
    enabled: usesFont,
  });

  // Debounced live preview.
  const debText = useDebounced(text, 550);
  const debOuter = useDebounced(outer, 550);
  const debInner = useDebounced(inner, 550);
  const debColor = useDebounced(color, 550);
  const debFont = useDebounced(fontKey, 550);

  const canPreview = Boolean(template && debText.trim());
  const preview = useQuery({
    queryKey: ["preview", productKind, template?.id, debText, debOuter, debInner, debColor, debFont],
    queryFn: () =>
      renderApi.preview({
        kind: productKind,
        text: debText.trim(),
        template: template!.id,
        outer_hex: debOuter,
        inner_hex: debInner,
        color_hex: debColor,
        font_key: debFont,
      }),
    enabled: canPreview,
    retry: 0,
  });

  const colorLabel3 = productKind === "name" ? t("text_color") : t("logo_color");

  const buildInput = (): OrderInput => ({
    kind: productKind,
    pack_kind: packKind,
    text: text.trim(),
    templates: template!.id,
    outer_hex: outer,
    inner_hex: inner,
    color_hex: color,
    font_key: fontKey,
    pack_title: packTitle || `${TITLES[productKind]} — ${text}`,
  });

  const readyToGenerate = Boolean(template && text.trim());

  return (
    <div className="px-4 pt-4 pb-4">
      <header className="flex items-center gap-3 mb-4">
        <button className="btn-ghost !px-3 !py-2" onClick={() => nav(-1)}>
          ←
        </button>
        <h1 className="text-lg font-bold flex-1">{TITLES[productKind]}</h1>
      </header>

      {/* Live preview */}
      <div className="card p-4 mb-4 flex flex-col items-center">
        <div className="w-40 h-40 rounded-3xl bg-tg-card-2 flex items-center justify-center overflow-hidden relative">
          {preview.isFetching && (
            <div className="absolute inset-0 flex items-center justify-center bg-tg-card-2/70 z-10">
              <Spinner className="h-7 w-7 text-brand-500" />
            </div>
          )}
          {preview.data ? (
            <LottiePlayer data={preview.data.lottie} className="w-full h-full" />
          ) : preview.isError ? (
            <span className="text-xs text-red-400 px-3 text-center">{(preview.error as Error)?.message || t("error")}</span>
          ) : (
            <span className="text-tg-hint text-sm text-center px-4">{t("live_preview")}</span>
          )}
        </div>
        {preview.data?.watermark && <p className="text-[10px] text-tg-hint mt-2">preview • watermark</p>}
      </div>

      {/* Template selector */}
      <div className="card p-4 mb-4">
        <SectionTitle>{t("choose_template")}</SectionTitle>
        <button
          className="btn-ghost w-full justify-between"
          onClick={() => {
            haptic("light");
            setGalleryOpen(true);
          }}
        >
          <span>{template ? template.label : t("choose_template")}</span>
          <span className="text-tg-hint">→</span>
        </button>
      </div>

      {/* Text input */}
      <div className="card p-4 mb-4">
        <SectionTitle action={<span className="text-xs text-tg-hint">{text.length}/{maxLen}</span>}>
          {productKind === "name" ? t("enter_word") : t("enter_text")}
        </SectionTitle>
        <input
          className="input"
          value={text}
          maxLength={maxLen}
          placeholder={productKind === "pf" ? "Ali" : "Salom"}
          onChange={(e) => setText(e.target.value)}
        />
      </div>

      {/* Font (logo/pf only) */}
      {usesFont && (
        <div className="card p-4 mb-4">
          <SectionTitle>{t("font")}</SectionTitle>
          <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
            {fonts.data?.map((f) => (
              <button
                key={f.key}
                onClick={() => {
                  haptic("select");
                  setFontKey(f.key);
                }}
                className={`chip whitespace-nowrap border ${
                  fontKey === f.key ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-tg-border"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Colors */}
      <SectionTitle>{t("colors")}</SectionTitle>
      <div className="space-y-3 mb-4">
        <ColorControl label={t("outer_color")} value={outer} onChange={setOuter} skippable />
        <ColorControl label={t("inner_color")} value={inner} onChange={setInner} skippable />
        <ColorControl label={colorLabel3} value={color} onChange={setColor} skippable />
      </div>

      {/* Pack options */}
      <div className="card p-4 mb-4 space-y-3">
        <div>
          <p className="text-sm font-semibold mb-2">{t("pack_type")}</p>
          <div className="grid grid-cols-2 gap-2">
            {(["emoji", "sticker"] as PackKind[]).map((pk) => (
              <button
                key={pk}
                onClick={() => {
                  haptic("select");
                  setPackKind(pk);
                }}
                className={`btn ${packKind === pk ? "btn-primary" : "btn-ghost"}`}
              >
                {pk === "emoji" ? t("pack_emoji") : t("pack_sticker")}
              </button>
            ))}
          </div>
        </div>
        <div>
          <p className="text-sm font-semibold mb-2">{t("pack_title")}</p>
          <input
            className="input"
            value={packTitle}
            placeholder={text ? `${TITLES[productKind]} — ${text}` : t("pack_title")}
            onChange={(e) => setPackTitle(e.target.value)}
          />
        </div>
      </div>

      <button
        className="btn-primary w-full"
        disabled={!readyToGenerate}
        onClick={() => {
          haptic("medium");
          setCheckoutOpen(true);
        }}
      >
        {t("generate")} ✨
      </button>

      {/* Gallery sheet */}
      <Sheet open={galleryOpen} onClose={() => setGalleryOpen(false)} title={t("choose_template")}>
        <TemplateGallery
          kind={productKind}
          selectedId={template?.id ?? null}
          onSelect={(item) => {
            setTemplate(item);
            setGalleryOpen(false);
          }}
        />
      </Sheet>

      {/* Checkout */}
      {readyToGenerate && (
        <CheckoutSheet
          open={checkoutOpen}
          onClose={() => setCheckoutOpen(false)}
          buildInput={buildInput}
          itemCount={1}
        />
      )}
    </div>
  );
}
