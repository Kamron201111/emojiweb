import { useState } from "react";
import { haptic } from "@/lib/telegram";
import { useI18n } from "@/i18n";

const PRESETS = [
  "#FFFFFF", "#000000", "#FF3B30", "#FF9500", "#FFCC00", "#34C759",
  "#00C7BE", "#30B0C7", "#007AFF", "#5856D6", "#AF52DE", "#FF2D55",
  "#8E8E93", "#1f2937", "#f5b301", "#6366f1",
];

const HEX_RE = /^#?[0-9a-fA-F]{6}$/;

// A graphical color control: presets + native color picker + HEX + reset.
export function ColorControl({
  label,
  value,
  onChange,
  skippable = false,
}: {
  label: string;
  value: string | null;
  onChange: (hex: string | null) => void;
  skippable?: boolean;
}) {
  const { t } = useI18n();
  const [hexInput, setHexInput] = useState(value || "");

  const apply = (hex: string) => {
    haptic("select");
    onChange(hex.toUpperCase());
    setHexInput(hex.toUpperCase());
  };

  return (
    <div className="card p-4 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <span className="font-semibold text-sm">{label}</span>
        <div className="flex items-center gap-2">
          <span
            className="h-7 w-7 rounded-full border-2 border-tg-border shadow-inner"
            style={{ background: value || "transparent", backgroundImage: value ? undefined : "repeating-conic-gradient(#8884 0 25%, transparent 0 50%)", backgroundSize: "10px 10px" }}
          />
          {skippable && (
            <button
              className="text-xs text-tg-hint underline"
              onClick={() => {
                onChange(null);
                setHexInput("");
                haptic("light");
              }}
            >
              {t("original_color")}
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-8 gap-2 mb-3">
        {PRESETS.map((c) => (
          <button
            key={c}
            aria-label={c}
            onClick={() => apply(c)}
            className={`aspect-square rounded-xl border transition-transform active:scale-90 ${
              value?.toUpperCase() === c ? "ring-2 ring-brand-500 border-transparent" : "border-tg-border"
            }`}
            style={{ background: c }}
          />
        ))}
      </div>

      <div className="flex items-center gap-2">
        <label className="relative h-10 w-10 shrink-0 rounded-xl overflow-hidden border border-tg-border cursor-pointer">
          <input
            type="color"
            value={value || "#6366f1"}
            onChange={(e) => apply(e.target.value)}
            className="absolute -inset-2 h-14 w-14 cursor-pointer"
          />
        </label>
        <input
          className="input flex-1"
          placeholder={t("custom_hex")}
          value={hexInput}
          maxLength={7}
          onChange={(e) => setHexInput(e.target.value)}
          onBlur={() => {
            if (HEX_RE.test(hexInput)) apply(hexInput.startsWith("#") ? hexInput : `#${hexInput}`);
          }}
        />
      </div>
    </div>
  );
}
