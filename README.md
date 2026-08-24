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
web/                       # Vite + React + Leaflet map-first UI (WEB-2)
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

## WEB-2: map-first React frontend

The UI under `web/` renders frozen demo API results only. It does **not**
recompute forecasts, IDW, exposure, ETA, or routing in the browser.

```bash
# terminal 1 — API
python3 -m uvicorn api.main:app --reload --port 8000

# terminal 2 — UI
cd web
npm install
npm run dev
```

Vite proxies `/demo` and `/health` to the API. Frontend checks:

```bash
cd web && npm test && npm run build
```

Product copy compares the **fastest route** with **top feasible lower-exposure
alternatives among generated candidates** under an absolute `+δ` minute limit.

WEB-3 polished labels, spacing, accessibility, and empty/error states for
demo readiness. Origin/destination dropdowns use stable labels such as
`Origin 26` (coordinates remain secondary).

## Deploying AIRPATH-AI

The prototype stays precomputed and read-only. Do not enable live routing.

1. Deploy the **airpath-api** Web Service from `render.yaml` (repo root so
   `uvicorn api.main:app --host 0.0.0.0 --port $PORT` can load
   `data/processed/web_demo`).
2. Copy the API public URL (for example `https://airpath-api.onrender.com`).
3. Set **VITE_API_URL** on the **airpath-frontend** Static Site to that URL
   (no trailing slash), then deploy/rebuild the frontend.
4. Set **AIRPATH_ALLOWED_ORIGINS** on the API to the frontend origin
   (comma-separated if you have more than one; do not use `*`).
5. Deploy the **airpath-frontend** Static Site (`web/`, `npm ci && npm run build`,
   publish `dist`).

Local development is unchanged: leave `VITE_API_URL` unset so Vite proxies
`/demo` and `/health` to `http://127.0.0.1:8000`. Unset
`AIRPATH_ALLOWED_ORIGINS` allows `http://localhost:5173` and
`http://127.0.0.1:5173`.

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
