/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Telegram-inspired palette, driven by CSS variables (theme-aware).
        tg: {
          bg: "var(--tg-bg)",
          card: "var(--tg-card)",
          "card-2": "var(--tg-card-2)",
          text: "var(--tg-text)",
          hint: "var(--tg-hint)",
          link: "var(--tg-link)",
          accent: "var(--tg-accent)",
          border: "var(--tg-border)",
        },
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
        },
        gold: "#f5b301",
      },
      fontFamily: {
        sans: ["Inter", "SF Pro Display", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl2: "1.25rem",
        "3xl": "1.75rem",
      },
      boxShadow: {
        soft: "0 8px 30px rgba(0,0,0,0.12)",
        glow: "0 0 0 1px rgba(99,102,241,0.35), 0 10px 40px rgba(99,102,241,0.25)",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "sheet-up": {
          "0%": { transform: "translateY(100%)" },
          "100%": { transform: "translateY(0)" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.35s ease both",
        "scale-in": "scale-in 0.25s ease both",
        shimmer: "shimmer 1.5s infinite",
        "sheet-up": "sheet-up 0.3s cubic-bezier(0.22,1,0.36,1) both",
        float: "float 3s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
