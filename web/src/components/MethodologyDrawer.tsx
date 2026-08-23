interface MethodologyDrawerProps {
  open: boolean
  onClose: () => void
}

export function MethodologyDrawer({ open, onClose }: MethodologyDrawerProps) {
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
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            Close
          </button>
        </div>
        <ol className="drawer__steps">
          <li>PM2.5 is forecast from historical station data.</li>
          <li>Spatial estimation is performed from monitoring stations.</li>
          <li>Route segments are assigned estimated travel times.</li>
          <li>Exposure is accumulated along segments as a time-weighted PM2.5 proxy.</li>
          <li>
            Routes are filtered by your maximum additional travel time, then ranked by
            predicted exposure among feasible candidates.
          </li>
        </ol>
        <h3>Limitations</h3>
        <ul className="drawer__limits">
          <li>Current demo uses hourly HealthyAir data.</li>
          <li>Pilot area only (stations 2–6 polygon).</li>
          <li>Road PM2.5 is model-estimated, not measured on each road.</li>
          <li>No live traffic.</li>
          <li>Not medical advice — exposure is not an inhaled dose or health risk score.</li>
          <li>This UI uses precomputed demo scenarios from the frozen research pack.</li>
        </ul>
        <p className="muted small">
          Research metrics such as MAE or R² belong in the scientific reports, not on
          this comparison screen.
        </p>
      </aside>
    </div>
  )
}
