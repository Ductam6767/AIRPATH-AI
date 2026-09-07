import { useI18n } from '../i18n/LanguageContext'

const ONBOARD_KEY = 'airpath_onboard_v1'

export function OnboardingCard({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) {
  const { t } = useI18n()
  if (!open) return null

  return (
    <div className="onboard-backdrop" role="presentation">
      <div className="onboard-card" role="dialog" aria-labelledby="onboard-title">
        <h2 id="onboard-title">{t.onboardingTitle}</h2>
        <p>{t.onboardingBody}</p>
        <button
          type="button"
          className="primary-btn"
          onClick={() => {
            try {
              localStorage.setItem(ONBOARD_KEY, '1')
            } catch {
              /* ignore */
            }
            onClose()
          }}
        >
          {t.onboardingOk}
        </button>
      </div>
    </div>
  )
}

export function shouldShowOnboarding(): boolean {
  try {
    return localStorage.getItem(ONBOARD_KEY) !== '1'
  } catch {
    return true
  }
}
