import { CUSTOM_EMOJI, type CustomEmojiKey } from "@/lib/customEmoji";

// Renders a Telegram custom emoji when possible, else the fallback glyph.
// In a WebView we cannot render arbitrary custom_emoji_id inline, so we show a
// styled fallback — but the id is preserved (data attribute) for contexts that
// can upgrade it (e.g. message entities produced by the bot).
export function CustomEmoji({
  name,
  className = "",
}: {
  name: CustomEmojiKey;
  className?: string;
}) {
  const e = CUSTOM_EMOJI[name];
  return (
    <span
      className={`inline-block leading-none ${className}`}
      data-custom-emoji-id={e.id}
      role="img"
      aria-label={name}
    >
      {e.fallback}
    </span>
  );
}
