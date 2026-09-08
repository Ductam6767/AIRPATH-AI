import { useI18n } from '../i18n/LanguageContext'

interface TopBarProps {
  onOpenMore: () => void
}

export function TopBar({ onOpenMore }: TopBarProps) {
  const { t, lang, setLang } = useI18n()

  return (
    <header className="top-bar">
      <div className="top-bar__brand">
        <h1 className="brand">AIRPATH-AI</h1>
        <p className="top-bar__subtitle">{t.hero}</p>
      </div>
      <div className="top-bar__actions">
        <div className="lang-toggle" role="group" aria-label="Language">
          <button
            type="button"
            className={lang === 'en' ? 'lang-btn is-active' : 'lang-btn'}
            onClick={() => setLang('en')}
          >
            {t.langEn}
          </button>
          <button
            type="button"
            className={lang === 'vi' ? 'lang-btn is-active' : 'lang-btn'}
            onClick={() => setLang('vi')}
          >
            {t.langVi}
          </button>
        </div>
        <button type="button" className="icon-btn" onClick={onOpenMore}>
          {t.more}
        </button>
      </div>
    </header>
  )
}
