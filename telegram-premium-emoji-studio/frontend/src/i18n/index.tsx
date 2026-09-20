import { createContext, useContext, useMemo } from "react";
import type { Lang } from "@/types";
import { translations, type TransKey } from "./translations";

interface I18nCtx {
  lang: Lang;
  t: (key: TransKey, vars?: Record<string, string | number>) => string;
}

const Ctx = createContext<I18nCtx>({ lang: "uz", t: (k) => k });

function format(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`));
}

export function I18nProvider({ lang, children }: { lang: Lang; children: React.ReactNode }) {
  const value = useMemo<I18nCtx>(() => {
    const dict = translations[lang] || translations.uz;
    return {
      lang,
      t: (key, vars) => format(dict[key] ?? translations.uz[key] ?? String(key), vars),
    };
  }, [lang]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n() {
  return useContext(Ctx);
}
