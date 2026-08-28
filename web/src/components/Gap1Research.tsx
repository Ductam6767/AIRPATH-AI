import type { Gap1Exhibit, Gap1Disagreement } from '../types'

function pct(value: number, digits = 2): string {
  return `${(value * 100).toFixed(digits)}%`
}

function DisagreementTable({ rows }: { rows: Gap1Disagreement[] }) {
  if (rows.length === 0) {
    return <p className="muted">No constrained-selection disagreements in this panel.</p>
  }
  return (
    <div className="gap1-table-wrap">
      <table className="gap1-table">
        <thead>
          <tr>
            <th>OD</th>
            <th>Mode</th>
            <th>δ (min)</th>
            <th>Static pick</th>
            <th>AIRPATH pick</th>
            <th>Oracle Δ</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={`${row.departure_time ?? ''}-${row.scenario_id}-${row.mode}-${row.delta_minutes}`}
            >
              <td>
                {row.scenario_id}
                {row.departure_time ? (
                  <div className="muted small">{row.departure_time.slice(11, 16)}</div>
                ) : null}
              </td>
              <td>{row.mode}</td>
              <td>{row.delta_minutes}</td>
              <td>{row.static_selected_route_id}</td>
              <td>{row.airpath_selected_route_id}</td>
              <td>
                {row.oracle_percent_improvement_airpath_over_static.toFixed(3)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Gap1Research({
  exhibit,
  onBack,
}: {
  exhibit: Gap1Exhibit
  onBack: () => void
}) {
  return (
    <section className="gap1-panel" aria-label="Gap 1 research exhibit">
      <p className="pilot-chip">Research exhibit · not the product map · no simulated street PM</p>
      <h2>Gap 1 — static snapshot vs arrival-time hour</h2>
      <p>{exhibit.question}</p>
      <p>
        <strong>Conclusion. </strong>
        {exhibit.freeze_gap1_conclusion}
      </p>

      <h3>Desired quantity (not in the dataset)</h3>
      <p>
        <code>PM2.5_road(x_D, t_arrival)</code> — {exhibit.desired_quantity}
      </p>
      <p className="muted small">HealthyAir does not contain this field. Gap 1 does not invent it.</p>
      <ul>
        {exhibit.not_available.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      <h3>Data that would be required to claim street-level arrival PM</h3>
      <ul>
        {exhibit.data_required_for_street_pm.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      <h3>Substitution actually computed</h3>
      <p>{exhibit.available_substitution}</p>
      <p className="muted small">{exhibit.ceiling_rule}</p>
      <p className="muted small">
        Forecaster {exhibit.forecaster} · spatial {exhibit.spatial_model} ·{' '}
        {exhibit.exposure_definition} in {exhibit.exposure_unit}. Simulated
        on-road PM used: {exhibit.uses_simulated_onroad_pm ? 'yes' : 'no'}.
      </p>
      {exhibit.worked_example ? (
        <div className="gap1-table-wrap">
          <table className="gap1-table">
            <thead>
              <tr>
                <th>Event</th>
                <th>Clock</th>
                <th>Hour used</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Forecast origin</td>
                <td>{exhibit.worked_example.forecast_origin}</td>
                <td>—</td>
              </tr>
              <tr>
                <td>Departure</td>
                <td>{exhibit.worked_example.departure}</td>
                <td>{exhibit.worked_example.departure}</td>
              </tr>
              <tr>
                <td>On segment at</td>
                <td>{exhibit.worked_example.segment_passage}</td>
                <td>{exhibit.worked_example.hour_used} (ceil)</td>
              </tr>
            </tbody>
          </table>
          <p className="muted small">{exhibit.worked_example.note}</p>
        </div>
      ) : null}

      <h3>P0-2A · {exhibit.p0_2a.label}</h3>
      <p>{exhibit.p0_2a.classification}</p>
      <ul>
        <li>
          Selection differs: {pct(exhibit.p0_2a.nontrivial_selection_difference_rate)} of
          nontrivial cases
        </li>
        <li>
          Spearman static vs AIRPATH:{' '}
          {exhibit.p0_2a.mean_spearman_static_vs_airpath.toFixed(3)}
        </li>
        <li>
          Mean oracle gain when they differ:{' '}
          {exhibit.p0_2a.mean_oracle_percent_improvement_when_differ.toFixed(3)}%
        </li>
      </ul>
      <DisagreementTable rows={exhibit.p0_2a.representative_disagreements} />

      <h3>P0-2B · {exhibit.p0_2b.label}</h3>
      <p>{exhibit.p0_2b.classification}</p>
      <ul>
        <li>
          Selection differs: {pct(exhibit.p0_2b.nontrivial_selection_difference_rate)}{' '}
          pooled
        </li>
        <li>
          Spearman: {exhibit.p0_2b.mean_spearman_static_vs_airpath.toFixed(3)}
        </li>
        <li>
          Mean oracle gain when they differ:{' '}
          {exhibit.p0_2b.mean_oracle_percent_improvement_when_differ.toFixed(3)}%
        </li>
      </ul>
      {exhibit.p0_2b.by_clock ? (
        <div className="gap1-table-wrap">
          <table className="gap1-table">
            <thead>
              <tr>
                <th>Clock</th>
                <th>Differ rate</th>
                <th>Spearman</th>
                <th>Oracle gain if differ</th>
              </tr>
            </thead>
            <tbody>
              {exhibit.p0_2b.by_clock.map((row) => (
                <tr key={row.clock_time}>
                  <td>{row.clock_time}</td>
                  <td>{pct(row.nontrivial_selection_difference_rate)}</td>
                  <td>{row.mean_spearman.toFixed(3)}</td>
                  <td>
                    {row.mean_oracle_pct_improvement_when_differ == null
                      ? '—'
                      : `${row.mean_oracle_pct_improvement_when_differ.toFixed(3)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <DisagreementTable rows={exhibit.p0_2b.representative_disagreements} />

      <h3>Sentence allowed in the paper</h3>
      <p>{exhibit.paper_claim_allowed}</p>
      <h3>Do not write</h3>
      <ul>
        {exhibit.paper_claim_forbidden.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      <button type="button" className="primary-btn" onClick={onBack}>
        Back to route demo
      </button>
    </section>
  )
}
