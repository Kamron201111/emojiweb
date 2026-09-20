// Centralized Telegram custom emoji configuration (preserved from the original
// project) + graceful fallbacks. When custom emoji rendering is unavailable in
// the current WebView, we show the fallback glyph.

export const CUSTOM_EMOJI = {
  black_star: { id: "5271842983111564386", fallback: "✦" },
  gold_star: { id: "5060263625571173566", fallback: "★" },
  green_check: { id: "5060253931829986667", fallback: "✅" },
  lightning: { id: "5474577070254237092", fallback: "⚡" },
  fire: { id: "5438436024264987566", fallback: "🔥" },
  warning: { id: "5440603840288165037", fallback: "ℹ️" },
  stars: { id: "5422367241645611298", fallback: "⭐" },
  globe: { id: "5188381825701021648", fallback: "🌐" },
  flag_uz: { id: "5438215555003737737", fallback: "🇺🇿" },
  flag_ru: { id: "5174669313679819503", fallback: "🇷🇺" },
  flag_en: { id: "5202196682497859879", fallback: "🇬🇧" },
} as const;

export type CustomEmojiKey = keyof typeof CUSTOM_EMOJI;
