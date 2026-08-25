import { useEffect, useRef } from 'react'

interface MethodologyDrawerProps {
  open: boolean
  onClose: () => void
}

export function MethodologyDrawer({ open, onClose }: MethodologyDrawerProps) {
  const closeRef = useRef<HTMLButtonElement>(null)

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
          <h2 id="methodology-title">How AIRPATH works</h2>
          <button
            ref={closeRef}
            type="button"
            className="icon-btn"
            onClick={onClose}
            aria-label="Close methodology"
          >
            Close
          </button>
        </div>
        <ol className="drawer__steps">
          <li>Historical monitoring data are used to forecast PM2.5.</li>
          <li>Station forecasts are spatially estimated across the road network.</li>
          <li>Route segments receive estimated travel times.</li>
          <li>Exposure is aggregated across segments as a time-weighted PM2.5 proxy.</li>
          <li>
            Routes are filtered by your maximum additional travel time, then ranked by
            predicted exposure among feasible candidates. AIRPATH compares those
            feasible alternatives rather than guaranteeing a cleaner route.
          </li>
        </ol>
        <h3>Limitations</h3>
        <ul className="drawer__limits">
          <li>Current demo uses hourly HealthyAir data.</li>
          <li>Pilot-area only (stations 2–6 polygon).</li>
          <li>Road PM2.5 is estimated, not directly measured on each road.</li>
          <li>No live traffic model.</li>
          <li>
            Exposure is a time-weighted proxy — not inhaled dose, medical risk, or
            medical advice.
          </li>
          <li>This UI uses precomputed demo scenarios from the frozen research pack.</li>
          <li>
            A lower-exposure feasible alternative is not guaranteed; on the frozen
            research panel it is uncommon, and any predicted reduction is typically
            small.
          </li>
        </ul>
        <p className="muted small">
          Research metrics such as MAE or R² belong in the scientific reports, not on
          this comparison screen.
        </p>
      </aside>
    </div>
  )
}
