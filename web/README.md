# AIRPATH-AI web frontend (WEB-2)

Map-first React prototype that **only renders** the frozen FastAPI demo pack.

## Stack

- Vite + React + TypeScript
- Leaflet / React-Leaflet (Carto Positron tiles — no API key)

## Develop

Start the WEB-1 API first:

```bash
# repo root
python3 -m pip install -r api/requirements.txt
python3 -m uvicorn api.main:app --reload --port 8000
```

Then:

```bash
cd web
npm install
npm run dev
```

Vite proxies `/demo` and `/health` to `http://127.0.0.1:8000`.

## Test / build

```bash
npm test
npm run build
```

## Notes

- Scenarios and routes are loaded from the API — not hard-coded.
- No forecasting, IDW, exposure math, or routing is performed in the browser.
