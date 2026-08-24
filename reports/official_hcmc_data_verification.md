# Official HCMC environmental monitoring portal verification

Review date: 2026-08-20.

## Scope and method

This report verifies whether the **official Ho Chi Minh City environmental
monitoring portal** can provide historical PM2.5 observations at a finer temporal
resolution than the hourly HealthyAir dataset used in AIRPATH-AI.

Portal investigated:

- https://thongtinquantrac.moitruonghcm.vn/

Constraints observed:

- No project code, datasets, models, splits, or notebooks were modified.
- No large historical file was downloaded and no bulk scrape was performed.
- Only lightweight HTTP probes, public CMS content, and client-side route inspection
  were used to verify the **actual data access mechanism**.

Evidence sources:

- Live endpoint probes on 2026-08-20 (repeated at report finalization).
- Portal client bundles (`/_next/static/chunks/pages/environment-*.js`).
- Embedded runtime config (`window.__ENV__` on `/vi/environment/AQIAuto`).
- Strapi CMS content at `https://api-thongtinquantrac.moitruonghcm.vn/`.
- Browser inspection during the same review window (map loaded; AQI markers absent
  when AQI upstream failed).

## Executive result

**Classification: C. Historical PM2.5 data cannot currently be accessed/reproduced**

The portal is **designed** to expose PM2.5 concentrations (`PM2_5`) alongside
VN_AQI and other pollutants, with **hourly / daily / monthly** history views.
However, during verification **no reproducible AQI or PM2.5 time series could be
retrieved** through the portal’s public proxy routes or configured upstream AQI
service. The finest documented temporal granularity for air-quality history on
this portal is **hourly**, not sub-hourly — so it would **not** exceed HealthyAir’s
hourly resolution even if the upstream service were working.

## Portal architecture (verified)

| Component | URL / route | Role |
|---|---|---|
| Public portal | `https://thongtinquantrac.moitruonghcm.vn/` | Next.js UI (map, AQI/WQI pages) |
| Portal proxy APIs | `/api/aqi`, `/api/aqi-share`, `/api/aqi-share-history`, `/api/wqi`, `/api/stationFixed`, `/api/weather/*` | Server-side proxies to upstream services |
| CMS (Strapi) | `https://api-thongtinquantrac.moitruonghcm.vn/` | Methodology articles, categories, media — **not** time-series store |
| Configured AQI upstream | `https://airlotus-api.ilotusland.com` | Referenced in `window.__ENV__.AQI_API_URL` |
| Configured WQI upstream | `http://113.190.254.225:5300` | Referenced in `window.__ENV__.WQI_API_URL` (JWT embedded in client config) |
| Mobile apps | AirLotus iOS/Android URLs in `window.__ENV__` | Alternate client; not evaluated here |

Embedded config excerpt (AQI page, 2026-08-20):

```json
{
  "AQI_API_URL": "https://airlotus-api.ilotusland.com",
  "WQI_API_URL": "http://113.190.254.225:5300",
  "ENABLE_BLOCK_AQI": "false",
  "ENABLE_BLOCK_WQI": "false"
}
```

Client-side API map (portal bundle):

```text
aqi: "/api/aqi"
aqiShare: "/api/aqi-share"
aqiShareHistory: "/api/aqi-share-history"
wqi: "/api/wqi"
stationFixed: "/api/stationFixed"
```

## Endpoint probe results (2026-08-20)

| Endpoint | HTTP result | PM2.5 / AQI payload retrieved? | Notes |
|---|---:|---|---|
| `GET /api/weather/newest-data` | 200 | No | Weather only (`temp`, `rh`, `wind_spd`, …) |
| `GET /api/weather/forecast-data` | 200 | No | Weather forecast only |
| `GET /api/aqi` | Timeout (~20–504 s) | No | No JSON body returned within probe window |
| `GET /api/aqi-share` | 500 | No | `{"success":false,"message":"Failed to fetch AQI Share data"}` |
| `GET /api/aqi-share-history?stationKey=KK_ThanhCong&from=…&to=…` | 500 | No | Same failure message |
| `GET /api/aqi-share/KK_ThanhCong/history-by-hour?date=2025-08-19` | 302 → HTML 404 | No | Redirect to `/vi/api/...` then portal 404 page |
| `GET /api/stationFixed` | 302 → HTML 404 | No | Redirect chain ends at portal 404 page |
| `GET /localres/en/aqi/aqiStations.json` | 302 → HTML 404 | No | Static station list not served |
| `GET https://airlotus-api.ilotusland.com/` (and `/stations`, `/api/stations`) | 404 | No | Upstream not reachable on tested paths from this environment |
| `GET /api/wqi` | 200 | No (water quality) | 128 WQI stations with keys, names, lat/lng |
| `GET /api/wqi/RSG2/history-by-month` | 200 | No (WQI, not PM2.5) | Monthly WQI history for one station |
| `GET /api/wqi/RSG2/history-by-day?from=…&to=…` | 302 → HTML 404 | No | Daily WQI proxy route broken like AQI history |

**Important:** Working WQI endpoints demonstrate that the portal proxy layer can
serve some environmental time series, but **they are water-quality (WQI) data,
not air PM2.5**.

## Answers to the ten verification questions

### 1. Does the portal provide PM2.5 measurements, not only AQI?

**Designed: yes. Verified live access: no.**

- CMS methodology (Decision 1459/QD-TCMT / VN_AQI) states parameters include
  **PM2.5** alongside SO2, CO, NO2, O3, and PM10.
- Portal client code maps upstream field `PM2_5` to display field `pm25` together
  with `aqi`, `CO`, `NO2`, and `PM10`.
- **No successful API response during verification contained PM2.5 or AQI values.**
  The public UI therefore could not be used to confirm current PM2.5 readings.

### 2. Which HCMC monitoring stations provide PM2.5?

**Not verifiable from accessible data during this review.**

- The intended AQI station inventory would come from `/api/aqi`, `/api/aqi-share`,
  or `localres/.../aqiStations.json`.
- All tested AQI station-list routes failed (timeout, HTTP 500, or 404 after redirect).
- The only station list successfully retrieved (`GET /api/wqi`, 128 entries) is for
  **surface-water WQI stations** (keys such as `RSG2`, `RSG5`, `DN2`), not air monitors.
- Client code uses a default example AQI station key `KK_ThanhCong`, but that key could
  not be resolved to live metadata or coordinates through working endpoints.

### 3. Are station IDs/names and coordinates available?

**For AQI / PM2.5 stations: not accessible.**

**For WQI stations only:** yes — each WQI record includes `point.key`, `point.name`,
and `point.mapLocation.lat` / `lng`. These are **not substitutes** for air-monitor
metadata.

Static `aqiStations.json` (which would normally hold AQI station metadata) redirected
to a 404 HTML page.

### 4. Can historical measurements be accessed or downloaded?

**Not reproducibly for PM2.5 / AQI during verification.**

Designed client history routes (from portal JavaScript):

| Intended route pattern | Granularity |
|---|---|
| `/{stationKey}/history-by-hour?date=` | Hourly |
| `/{stationKey}/history-by-day?from=&to=` | Daily |
| `/history?stationKey=&from=&to=` | Range history |
| `/api/aqi-share-history?stationKey=&from=&to=` | Share/history proxy |

All tested AQI history proxies returned **HTTP 500** or **404 HTML**, so no historical
PM2.5 series could be opened, exported, or sampled.

By contrast, **WQI monthly history** for station `RSG2` returned JSON successfully
(33 monthly records from `2023-1` through `2025-9`), confirming the portal can expose
*some* historical environmental data — but not air PM2.5.

No CMS `/download`, `/export`, or bulk-report endpoint for AQI time series was found.

### 5. Actual temporal resolution of historical PM2.5 observations

**Verified accessible resolution: none (data not retrieved).**

**Designed / documented resolution (portal only): hourly, daily, monthly — not sub-hourly.**

Evidence:

- History UI/API naming: `history-by-hour`, `history-by-day`, `history-by-month`.
- VN_AQI CMS guidance describes **1-hour averages** for hourly AQI and **24-hour
  averages** for daily AQI.
- No client route or CMS documentation referenced 1-, 5-, 10-, 15-, or 30-minute
  PM2.5 products on this portal.

| Candidate interval | Status on this portal |
|---|---|
| 1 min | Not evidenced |
| 5 min | Not evidenced |
| 10 min | Not evidenced |
| 15 min | Not evidenced |
| 30 min | Not evidenced |
| **Hourly** | **Designed** (`history-by-hour`) but **not accessible** in probes |
| Unknown | **Applies to live PM2.5 retrieval today** because upstream failed |

**Comparison to HealthyAir:** even if hourly AQI history were working, this portal
would be **at best equal to** HealthyAir’s hourly PM2.5 — not finer.

### 6. Earliest and latest historical period actually accessible

**PM2.5 / AQI: not determined — no historical payload retrieved.**

Because no AQI history response succeeded, earliest/latest PM2.5 dates **cannot be
stated from verified observations**.

Illustrative non-PM2.5 control: WQI monthly history for `RSG2` spanned **`2023-1`
to `2025-9`**. That range applies to **water quality**, not air PM2.5.

### 7. Continuous history vs current/live observations only

**PM2.5 / AQI: neither live nor historical series could be reproduced.**

- `/api/aqi-share` failure prevented current-state AQI/PM2.5 tables and map markers.
- History routes also failed, so continuity, gaps, and archive depth for PM2.5
  **could not be assessed**.
- Browser inspection: HCMC map rendered, but **no AQI station markers** appeared when
  the AQI share API failed — consistent with live-only display depending on the same
  broken upstream.

### 8. API, downloadable file, export, or other reproducible access method

**No reproducible PM2.5 access method was verified.**

| Mechanism | PM2.5 reproducible? |
|---|---|
| `/api/aqi` | No — timeout |
| `/api/aqi-share` | No — HTTP 500 |
| `/api/aqi-share-history` | No — HTTP 500 |
| Per-station `history-by-hour/day/month` proxies | No — 500 or 404 |
| `localres/.../aqiStations.json` | No — 404 after redirect |
| Direct `airlotus-api.ilotusland.com` | No — 404 on tested paths |
| Strapi CMS posts/categories | Metadata only; no time series |
| CSV/Excel/ZIP export | Not found |
| Mobile AirLotus app | Separate client; not evaluated; likely same upstream |

The portal therefore lacks a **currently working, documented, unauthenticated,
machine-readable PM2.5 history API** suitable for scripted external validation.

### 9. Are PM2.5 values available, rather than only AQI?

**In principle (schema/docs): yes — field `PM2_5` / `pm25`.**

**In verified responses: no.**

Client transformation expects concentration fields:

```javascript
pm25: e.PM2_5 || null
```

together with `aqi`, `CO`, `NO2`, `PM10`. Because every AQI proxy failed, **only AQI
without PM2.5** was *not* observed either — **no pollutant time series at all** were
returned.

### 10. Licensing / usage restrictions relevant to a scientific prototype

No open-data license, bulk-download terms, or API developer agreement was published
on the portal for AQI time-series reuse.

Observed constraints:

- Government portal operated under Ho Chi Minh City Department of Natural Resources
  and Environment (`sonnmt.hochiminhcity.gov.vn` footer links).
- Content is informational; CMS posts cite Vietnamese regulatory decisions (1459/QD-TCMT
  for VN_AQI).
- A JWT for the private WQI upstream is embedded in public client config — indicating
  some backends were not intended for anonymous third-party reuse.
- Third-party AirLotus mobile apps are promoted; no separate data-sharing policy for
  research redistribution was found.

For a scientific prototype, treat any future access as **requiring explicit permission
from the portal operator / data owner**, with attribution to the official HCMC
monitoring programme. Do not assume open redistribution rights.

## PM2.5 vs AQI display caveat

The portal’s public messaging and map layers emphasize **VN_AQI** categories and colors.
That UI focus does **not** prove sub-hourly or even hourly PM2.5 archives are exposed.
This review verified the **data plumbing**, not marketing labels alone.

## Comparison to AIRPATH HealthyAir baseline

From prior AIRPATH audits, HealthyAir’s public analytical file is **hourly** PM2.5 for
HCMC stations over a bounded 2021–2022 window. This official portal:

- does **not** expose verified sub-hourly PM2.5;
- does **not** currently expose verified hourly PM2.5 history through public APIs;
- therefore **cannot serve as a finer-resolution external validation source** relative
  to HealthyAir on present evidence.

## Limitations of this review

1. Upstream AQI service failure may be transient; endpoints could recover later without
   documentation changes.
2. The AirLotus mobile app or undisclosed authenticated routes were not exhaustively
   reverse-engineered.
3. No attempt was made to contact portal administrators for official exports.
4. WQI success does not transfer to air-quality availability.

## Final classification

### C. Historical PM2.5 data cannot currently be accessed/reproduced

Rationale:

1. **No PM2.5 or AQI JSON time series** were retrieved from any working public route.
2. **Designed temporal resolution is hourly at best**, so the portal would not beat
   HealthyAir’s hourly cadence even if restored.
3. **No export/download mechanism** for PM2.5 history was verified.
4. **Station metadata for air monitors** could not be enumerated reproducibly.
5. Working data on the same site (**WQI**) confirms partial portal functionality but
   **does not provide PM2.5**.

**Stop condition met:** verification only; no forecasting code, models, datasets, splits,
or notebooks were modified.
