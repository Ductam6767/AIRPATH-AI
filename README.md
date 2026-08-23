# AIRPATH-AI

AIRPATH-AI investigates whether forecast-based PM2.5 estimates can support
**time-constrained route comparison** in a HealthyAir HCMC pilot area
(stations 2–6).

## Research engine status: FROZEN

The scientific pipeline is frozen after P0-3 robustness validation.

| Component | Frozen choice |
|-----------|----------------|
| Forecaster | `C_xgboost_current_pm` |
| Spatial | IDW p=1 |
| Exposure | `Σ PM2.5_i × duration_i` in `(µg/m³)·min` |
| Routing | candidates → fastest baseline → absolute `+δ` minutes feasibility → rank feasible by predicted exposure → fastest + up to 3 alternatives |

Do **not** retrain models, change IDW, invent minute-level PM2.5, or claim
global optimality / medical risk in product copy.

Freeze manifest: `data/processed/final_robustness/freeze_manifest.json`.

## WEB-1: demo data pack + thin FastAPI backend

The first web milestone packages **frozen Model-C outputs** into a compact demo
dataset and serves them with a read-only FastAPI app. It does **not** run
XGBoost, IDW, OSM routing, or route optimization at request time.

```
data/processed/web_demo/   # scenarios.json, routes.json, metadata.json
api/                       # FastAPI app (packaging/serving only)
web/                       # placeholder — React UI not built yet
```

Demo scenarios (8 OD pairs) are a **distance-stratified subset** of the P0-2B
30-OD panel (evenly spaced straight-line distance ranks). They were not
cherry-picked for exposure reduction or map aesthetics. Departure time for the
pack is `2022-02-27T06:00:00` (forecast origin `05:00`).

Regenerate the pack (packaging only):

```bash
python3 -m src.web_demo_export
```

### Run the demo API locally

```bash
python3 -m pip install -r api/requirements.txt
# from repository root
python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Endpoint examples

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/demo/scenarios | head
curl -s "http://127.0.0.1:8000/demo/routes?scenario_id=od_01&mode=walking&delta_minutes=5"
```

`/demo/routes` returns `{ scenario_id, mode, delta_minutes, fastest_route, alternatives, metadata }`.
Alternatives are **top feasible lower-exposure candidates among generated routes**
for that `+δ` allowance — not a globally optimal cleanest path. At `delta_minutes=0`
there may be **no** alternatives.

### Tests

```bash
python3 -m pytest
```

## Dataset (research)

Expected input for full research reproduction:

`data/raw/Air Quality Ho Chi Minh City.csv`

Station observations are **not** direct road-level PM2.5 measurements.

## Scientific limitations (product + research)

- Hourly HealthyAir data; no validated minute-level PM2.5 prediction
- Pilot-area only (stations 2–6 polygon)
- Road PM2.5 is **model-estimated** (sparse network + IDW), not measured on roads
- No road-level ground truth for exposure
- Constant-speed ETA; **no live traffic**
- Exposure is a **time-weighted PM2.5 proxy**, not inhaled dose or medical risk
- Not a medical recommendation

## Milestone 1 note

Early audit / preprocessing workflows remain under `src/data_validation.py` and
`notebooks/01_data_audit.ipynb`. Later milestones (forecasting fairness, spatial
ETA, constrained routing, Gap-1 analyses, freeze) live under `src/`,
`reports/`, and `data/processed/`.
