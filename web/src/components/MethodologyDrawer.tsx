import { useEffect, useRef } from 'react'
import { useI18n } from '../i18n/LanguageContext'

interface MethodologyDrawerProps {
  open: boolean
  onClose: () => void
}

export function MethodologyDrawer({ open, onClose }: MethodologyDrawerProps) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const { t } = useI18n()

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="drawer-backdrop" role="presentation" onClick={onClose}>
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="methodology-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="drawer__header">
          <h2 id="methodology-title">{t.methodologyTitle}</h2>
          <button
            ref={closeRef}
            type="button"
            className="icon-btn"
            onClick={onClose}
            aria-label={t.methodologyCloseAria}
          >
            {t.close}
          </button>
        </div>
        <ol className="drawer__steps">
          {t.methodologySteps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
        <h3>{t.methodologyWhyFastestTitle}</h3>
        {t.methodologyWhyFastest.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
        <h3>{t.methodologyFromToTitle}</h3>
        {t.methodologyFromTo.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
        <h3>{t.methodologyLimitsTitle}</h3>
        <ul className="drawer__limits">
          {t.methodologyLimits.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="muted small">{t.methodologyMetricsNote}</p>
      </aside>
    </div>
  )
}
