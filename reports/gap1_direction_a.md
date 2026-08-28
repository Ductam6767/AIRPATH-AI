# Gap 1 Direction A — paper exhibit (frozen engine)

**Status:** research exhibit only. Not the product map. No simulated on-road PM.
**Engine:** frozen (`C_xgboost_current_pm`, IDW p=1, `Σ PM × minutes`).
**Decision:** MIXED/WEAK (P0-2A, replicated P0-2B). Do not claim a large
arrival-time routing benefit from hourly station buckets.

This note is written so the substitution is inspectable in a methods section.

## 1. What Gap 1 asks

Same candidate routes, two exposure fields, then the same constrained selector
(fastest always feasible; keep routes with time ≤ fastest + δ; pick the lowest
predicted exposure).

- **Static (Method A):** PM at every segment is the **departure-time** station
  snapshot, interpolated with IDW p=1. ETA is recorded but does not change PM.
- **AIRPATH / arrival-time (Method B):** PM at segment *i* uses the **hourly
  forecast bucket of that segment’s ETA**, then the same IDW p=1.

Gap 1 is whether Method B **changes the selected route** relative to Method A,
and whether that change is better under the IDW-derived oracle.

It is **not** whether we have measured PM on the asphalt at the arrival minute.

## 2. The quantity we do *not* have

Desired, unavailable quantity:

`PM2.5_road(x_D, t_arrival)`

= concentration on segment D at the exact minute the traveller reaches D.

That would require on-road / mobile monitoring (or an equivalent street-level
network) time-aligned with the trajectory. **HealthyAir does not provide it.**
The public file is hourly at six fixed stations. Minute records from the
instruments were not released for this project.

So Gap 1 in this thesis is **not** “we predicted the street.” It is “we tested
the only operational substitute the dataset supports.”

## 3. The substitution AIRPATH actually computes

Forecast origin is **one hour before departure**. Supported targets are
**t+1h, t+2h, t+3h** (exact hours only).

Mapping (`src/target_time_integration.py`):

1. Constant-speed ETA gives a segment passage time `t` (seconds).
2. If `t` is already an exact hour, use that hour.
3. Otherwise **ceil to the next exact hour, no interpolation**.
   Example: 17:03 → 18:00. This estimates the supported hourly target, not
   PM2.5 at 17:03.
4. Model C (`C_xgboost_current_pm`) forecasts PM2.5 at each of the six
   stations for that hour.
5. IDW p=1 interpolates those six forecasts to the segment midpoint.
6. Route exposure: `E = Σ_i PM_IDW(x_i, hour_i) × duration_i`  [(µg/m³)·min].

Worked example (walking, depart 06:00, origin 05:00):

| Event | Time | Hour used | Horizon from 05:00 |
|---|---|---|---|
| Departure | 06:00 | 06:00 | t+1h |
| Mid-block at 06:17 | 06:17 | **07:00** (ceil) | t+2h |
| Arrival ~06:40 | 06:40 | **07:00** (ceil) | t+2h |

Static Method A would put **06:00 observed** PM on every block, including 06:17.

Both methods use **real HealthyAir observations** (lags / snapshot) and a
**trained station forecaster**. Neither uses a fake street sensor. The
uncertainty is spatial (6 stations) and temporal (hour buckets), not “empty
data.”

## 4. What would be simulated — and is *not* used here

The product map’s OSM traffic-class layer is **demo-only**. Direction A forbids
feeding it into Gap 1.

Do not import:

- invented arterial vs alley multipliers as if they were measurements;
- Chinese 走航监测 vehicle files (not in this corpus);
- minute interpolation of hourly stations.

Those belong to a later **on-road heterogeneity** study, not to Gap 1 claims.

## 5. Frozen numerical result (copy into the paper)

P0-2A (2022-02-28 06:00, 30 OD × 2 modes, δ > 0):

- Selection differs in **6.33%** of nontrivial cases.
- Spearman of static vs AIRPATH route ranks: **0.992**.
- When selections differ, mean oracle improvement of AIRPATH over static:
  **0.11%**.

P0-2B (five clock times on 2022-02-27):

- Selection differs in **1.33%** of nontrivial cases (range 0–5% by hour).
- Strongest disagreement: 06:00 and 08:00; **12:00, 17:00, 20:00: 0%**.
- Mean oracle improvement when they differ: **0.02%**.
- Gap 1 conclusion **unchanged** vs P0-2A.

Classification: **MIXED/WEAK**. Allowed sentence:

> Hourly forecast-bucket-aware exposure, constructed by ceiling ETA to the next
> HealthyAir hour and IDW from six station forecasts, rarely changes
> constrained route selection relative to a static departure snapshot in this
> pilot.

Forbidden sentences: medical benefit; “we know PM on street D at arrival”;
“large routing gain from arrival-time.”

## 6. Why this is not a meaningless exercise

A negative / weak identification result is still a result. It answers a
decision that maps products usually skip: *if we only have hourly stations,
should we rank routes by future hours?* In this geometry and network, **almost
never**. That justifies (a) not overselling the prototype, and (b) requiring
on-road data before claiming Gap 1 as a product lever.

Meaningless would be: treating the substitution as if it were `PM2.5_road`,
or using demo traffic-class PM to reverse the MIXED/WEAK finding.

## 7. Later competitions

Documenting MIXED/WEAK **protects** later work. A future mobile-monitoring
campaign can be framed as: *the station-hourly substitute was insufficient;
here is the street-level field that can reopen Gap 1.* Retracting a fabricated
large Gap 1 benefit would be worse than an honest weak result.

## 8. JIGS methods paragraph (copy)

Gap 1 does **not** estimate `PM2.5_road(x_D, t_arrival)`. HealthyAir is hourly
at six stations. The operational substitute is: constant-speed ETA → ceil to
the next exact hour (no interpolation) → Model C station forecasts from an
origin one hour before departure → IDW p=1 to the segment midpoint →
`E = Σ PM × duration` in `(µg/m³)·min`. Static ranking uses the departure-hour
observed snapshot on every segment. Same candidates, same δ-constraint.

To claim knowledge of PM on street D at the arrival minute one would need
on-road / mobile-monitoring (or an equivalently dense street network)
time-aligned to the trajectory. That file is **not** in this corpus. Inventing
arterial multipliers, interpolating minutes, or reusing the product-map traffic
layer would change the quantity and is excluded from Gap 1 (Direction A).

The frozen identification result is MIXED/WEAK: constrained selections rarely
change, and oracle gains when they do are ~0.11% (P0-2A) and ~0.02% (P0-2B).
This is a negative/weak result about **hourly station buckets**, not proof that
arrival-time routing is useless once street-level PM exists.

## 9. How to prove “rarely” if asked

“Rarely” is a **count**, not a vibe.

1. File: `data/processed/static_vs_arrival_exposure/constrained_selection_comparison.csv`
   (P0-2B: `temporal_gap_analysis/constrained_selection_comparison.csv`).
2. Keep rows with `delta_time_allowed_minutes > 0`.
3. Rate = `mean(selections_differ)`.

| Experiment | Differ / cells | Rate | Spearman | Oracle gain if differ |
|---|---|---|---|---|
| P0-2A | **19 / 300** | 6.33% | 0.992 | 0.11% |
| P0-2A walking | 9 / 150 | 6.00% | — | — |
| P0-2A motorbike | 10 / 150 | 6.67% | — | — |
| P0-2B pooled | **20 / 1500** | 1.33% | 0.997 | 0.02% |
| P0-2B 12:00, 17:00, 20:00 | **0** | 0% | ~0.999 | — |

At 12:00 the **exposure numbers** still differ (mean |ΔE| ≈ 17%) but the **chosen route** never does. So “rare” = rare **reselection**, not identical indices.

Copy-paste reviewer sentence is in `exhibit.json` → `how_to_prove_rare.reviewer_sentence`.

## 10. Backup branch: peak hour (walk / motorbike)

**Hypothesis you stated:** later, with measured data, some roads at some hours are congested and therefore dirtier; the selector should output differently at peak vs off-peak, separately for walking and motorbike.

**With HealthyAir only, you can already say:**

- Model C has learned a **city-wide** diurnal pattern at six stations.
- Walking vs motorbike already differ because duration (and therefore ceil-hour) differs.
- P0-2B: reselection happens only at **06:00 and 08:00**. Walking 15/750, motorbike 5/750. Later clocks: 0.

**You cannot yet say** which street is jammed, or that pollution is the consequence of that jam.

**When on-road PM (+ traffic) exists:** learn `E[PM | road class or segment, hour, mode]`, keep the same δ-constraint. That study replaces IDW-from-six-stations. Do not back-port demo OSM multipliers into Gap 1.

The map toggle “Morning peak / Midday / Evening peak” is a **demo congestion proxy** on OSM class. It is allowed as product illustration. It is not evidence for section 10.
