import { useState } from 'react'
import { useI18n } from '../i18n/LanguageContext'

interface AIAnalysisProps {
  onOpenMethodology: () => void
  onOpenGap1?: () => void
}

export function AIAnalysis({ onOpenMethodology, onOpenGap1 }: AIAnalysisProps) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const steps = [
    t.aiStepEnv,
    t.aiStepForecast,
    t.aiStepSpatial,
    t.aiStepRoad,
    t.aiStepSelect,
  ]

  return (
    <section className="ai-analysis">
      <button
        type="button"
        className="ai-analysis__toggle"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {t.aiTitle}
      </button>
      {open ? (
        <div className="ai-analysis__body">
          <p className="muted">{t.aiIntro}</p>
          <ol className="ai-pipeline">
            {steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <button type="button" className="linkish" onClick={onOpenMethodology}>
            {t.howItWorks}
          </button>
          {onOpenGap1 ? (
            <button type="button" className="linkish" onClick={onOpenGap1}>
              {t.gap1Link}
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}
