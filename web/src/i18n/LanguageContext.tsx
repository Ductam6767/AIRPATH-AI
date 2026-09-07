import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { STRINGS, type AppLang } from './strings'

const STORAGE_KEY = 'airpath_lang'

function readLang(): AppLang {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === 'vi' || raw === 'en') return raw
  } catch {
    /* ignore */
  }
  return 'en'
}

interface LanguageContextValue {
  lang: AppLang
  setLang: (lang: AppLang) => void
  t: (typeof STRINGS)[AppLang]
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<AppLang>(readLang)

  const setLang = (next: AppLang) => {
    setLangState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      /* ignore */
    }
  }

  const value = useMemo(
    () => ({
      lang,
      setLang,
      t: STRINGS[lang],
    }),
    [lang],
  )

  return (
    <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
  )
}

export function useI18n(): LanguageContextValue {
  const ctx = useContext(LanguageContext)
  if (!ctx) {
    return {
      lang: 'en',
      setLang: () => {},
      t: STRINGS.en,
    }
  }
  return ctx
}
