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
          <li>
            Station forecasts are interpolated as a background field, then the demo
            applies a simulated on-road increment so busier road classes are dirtier
            than quiet streets.
          </li>
          <li>Route segments receive estimated travel times.</li>
          <li>Exposure is aggregated across segments as a time-weighted PM2.5 proxy.</li>
          <li>
            The fastest route is the shortest travel time among generated
            candidates. Walking and motorbike fill up to three cleaner
            alternatives only when they exist: slightly slower, second-fastest,
            and near your extra-time limit. A missing archetype is omitted. If
            the best alternative is the fastest route itself, AIRPATH shows one
            card that is both fastest and lowest-exposure. AIRPATH compares those
            alternatives rather than guaranteeing a cleaner route.
          </li>
        </ol>
        <h3>Limitations</h3>
        <ul className="drawer__limits">
          <li>Current demo uses hourly HealthyAir data.</li>
          <li>Pilot-area only (stations 2–6 polygon).</li>
          <li>Road PM2.5 in this demo is simulated, not measured on each street.</li>
          <li>
            Busy-road pollution is a traffic-class proxy (OSM highway type, lanes,
            junctions, time of day) inspired by mobile-monitoring frameworks — not
            live congestion and not a Chinese probe-vehicle dataset. Morning /
            midday / evening only change the arterial multiplier.
          </li>
          <li>
            Exposure is a time-weighted proxy — not inhaled dose, medical risk, or
            medical advice.
          </li>
          <li>This UI uses precomputed demo scenarios. Candidate routes and travel times stay frozen; only demo road PM is simulated.</li>
          <li>
            A lower-exposure feasible alternative is still not guaranteed. AIRPATH
            compares feasible candidates rather than promising a cleaner route.
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
