# PurpleAir HCMC sensor verification

Review date: 2026-08-20.

## Scope and method

This report verifies whether PurpleAir can supply a **concrete, publicly accessible
sub-hourly PM2.5 source in Ho Chi Minh City (HCMC)** for possible future external
validation of AIRPATH-AI. It is a source audit only.

Constraints observed:

- No project code, datasets, models, splits, or notebooks were modified.
- No historical PurpleAir file was downloaded.
- No HealthyAir merge, retraining, or synthetic minute-level data were performed.

Evidence was taken from PurpleAir's official map pages, API/documentation pages,
community guidance authored by PurpleAir staff, and live probes of public endpoints.
Where numeric coordinates or historical periods require an authenticated API read
key, that limitation is stated explicitly rather than inferred.

HCMC bounds used for coordinate checks: approximately **10.35–11.05°N,
106.50–107.00°E**.

## Executive result

**Classification: B. VERIFIED HCMC SENSOR + SUITABLE ONLY FOR PROTOTYPE/CURRENT-STATE USE**

One public PurpleAir sensor in HCMC was identified on PurpleAir's official HCMC map
interface. Its **sensor index, public status, HCMC map placement, and PM2.5
availability** were verified from publicly accessible PurpleAir sources.

However, **authoritative numeric latitude/longitude were not retrievable without an
API read key**, post-cutoff **historical continuity and exact earliest/latest
periods were not accessed**, and PurpleAir's **licensing plus community-sensor
calibration constraints** make this source unsuitable, on present evidence, for a
rigorous untouched scientific holdout without further authenticated metadata and QA
work.

## Verified candidate sensor

### Summary table

| Item | Verified value | Evidence |
|---|---|---|
| Sensor index / ID | **952095** | Official map URL parameter `select=952095`; PurpleAir documents that the index appears after `select=` when a map marker is clicked ([Sensor Indexes and Read Keys](https://community.purpleair.com/t/sensor-indexes-and-read-keys/4000)) |
| Sensor name | **VNJ-HCM** | Map popup label when sensor 952095 is selected on the HCMC map (2026-08-20 browser inspection). Minor display variants (`YNH-HCM`, `YNK1-HCM`) were seen in earlier map loads and are treated as the same registered device unless contradicted by authenticated metadata. |
| Latitude | **Not verified numerically** | Requires authenticated real-time API field `latitude` ([API Fields Descriptions](https://community.purpleair.com/t/api-fields-descriptions/4652)). Unauthenticated requests to `https://api.purpleair.com/v1/sensors/952095` returned `ApiKeyMissingError`. |
| Longitude | **Not verified numerically** | Same as latitude. |
| Public? | **Yes** | Sensor is visible on the public HCMC map without a private read key. PurpleAir staff state that sensors visible on the public map are public and queryable ([Making API Calls with the PurpleAir API](https://community.purpleair.com/t/making-api-calls-with-the-purpleair-api/180)). |
| PM2.5 available? | **Yes** | Map popup displayed US EPA PM2.5 AQI for the selected sensor; API exposes `pm2.5`, `pm2.5_atm`, `pm2.5_alt`, and related fields ([API Fields Descriptions](https://community.purpleair.com/t/api-fields-descriptions/4652)). |
| Native / reported interval | **About 2 minutes at the sensor/server real-time layer** | HCMC map page meta description states sensors provide updates "With two minute updates" ([HCMC map](https://map.purpleair.com/vietnam/ho-chi-minh-city)). PurpleAir's Data Download Tool documentation labels the finest server average as **"Real-time (2-min)"** ([historical download guide](https://community.purpleair.com/t/how-to-get-historical-sensor-data-step-by-step-using-the-data-download-tool/11934)). The live map popup for this sensor displayed a **10-minute average** AQI layer, which is a map display aggregate, not the native upload cadence. |
| Historical data available? | **Yes, in principle, via authenticated history API** | Official API exposes `/v1/sensors/:sensor_index/history` ([PurpleAir API](https://www.purpleair.com/api)). No historical pull was performed here. |
| Historical 2-minute averages requestable? | **Yes, in principle, as `average=real-time` / finest server average** | Data Download Tool: "Real-time (2-min) → one average over a 2 minute period." R/API clients map this to the finest history average (`0` / `real-time`) ([PurpleAir R package docs](https://cloud.r-project.org/web/packages/PurpleAir/PurpleAir.pdf)). This is **not** a separate one-minute product. |
| Earliest accessible historical period | **Unknown (not accessed)** | Would require authenticated history queries and inspection of returned timestamps plus `date_created` from the real-time endpoint. Not evaluated here to avoid data acquisition. |
| Latest accessible historical period | **Current/recent only confirmed from map** | Map showed a live reading on 2026-08-20; exact `last_seen` timestamp was not retrieved without API key. |
| API / account requirements | **PurpleAir developer account + READ API key required** | `https://api.purpleair.com/v1/sensors` and single-sensor endpoints returned `ApiKeyMissingError` without `X-API-Key`. Account creation is documented at [develop.purpleair.com](https://develop.purpleair.com/) and in PurpleAir's download guide. Requests are points-based under the Fair Use Policy. |
| Usage / attribution restrictions | **Restrictive** | [Data License](https://www.purpleair.com/license) (updated 2022-07-18): attribution required, grantback license, no raw data/API resale, distribution limited to one level removed (end-user products only), Fair Use Policy applies. [Attribution guide](https://www.purpleair.com/attribution) requires visible PurpleAir sourcing and, for some product types, disclaimers about consumer-sensor accuracy. Open redistribution through open-source distribution channels is explicitly constrained in PurpleAir terms/community guidance. |

### HCMC location verification (non-coordinate evidence)

The sensor was verified on PurpleAir's **HCMC-specific official map surface**:

- Map entry point: [Ho Chi Minh City, Vietnam Real-Time Interactive Map](https://map.purpleair.com/vietnam/ho-chi-minh-city)
- Selected sensor URL pattern: `https://map.purpleair.com/...?...&select=952095#...`

When sensor **952095** was selected on that HCMC map view (2026-08-20), the marker
and popup appeared over the **southern Vietnam HCMC metropolitan area**, with nearby
map labels such as **Thu Duc**, **Binh Thanh**, **Hoc Mon**, **Di An**, and **Thuan
An**. The marker was **not** in northern Vietnam (for example Hanoi).

This satisfies the task requirement to avoid inferring HCMC location from "Vietnam"
alone. It does **not** substitute for numeric coordinates.

### Important caveat on URL coordinates

PurpleAir staff explicitly state that **latitude/longitude values in the map URL hash
reflect the current map viewport, not the registered sensor coordinates**
([Download Sensor Locations](https://community.purpleair.com/t/download-sensor-locations/7872)).
During inspection, selecting sensor 952095 produced URLs whose hash included values
such as `10.6505` and `106.6922`; these are **map-view coordinates only** and were
**not** treated as verified sensor metadata in this report.

Authoritative coordinates must come from the authenticated real-time API fields
`latitude` and `longitude` ([API Fields Descriptions](https://community.purpleair.com/t/api-fields-descriptions/4652)).

## Public endpoint probes performed

The following probes were executed without downloading historical archives:

| Request | Result |
|---|---|
| `GET https://api.purpleair.com/v1/sensors/952095?fields=name,latitude,longitude,private,location_type,pm2.5` | `ApiKeyMissingError` |
| `GET https://api.purpleair.com/v1/sensors?...` HCMC bounding box | `ApiKeyMissingError` |
| Legacy `https://www.purpleair.com/json?show=952095` | Empty / unavailable |
| `GET https://map.purpleair.com/v1/sensors?select=952095&fields=...` from shell and browser `fetch()` | `ApiKeyMissingError` in this environment |

The HCMC map web application loads sensor markers in-browser, but **programmatic
coordinate confirmation from this verification environment requires a READ API key**.

## Historical access details relevant to AIRPATH

From PurpleAir's official/community documentation:

| Average requested | Documented meaning | Documented max span per history request |
|---|---|---|
| Real-time / finest (`average=0` or `real-time`) | About **2-minute** server averages | **2 days** per request ([New Version of the PurpleAir API](https://community.purpleair.com/t/new-version-of-the-purpleair-api-on-july-18th/1251), staff reply by Chloe_CTDEEP) |
| 10-minute | 10-minute averages | 3 days |
| 30-minute | 30-minute averages | 7 days |
| 60-minute / 1-hour | Hourly averages | 14 days |
| 1440-minute / 1-day | Daily averages | 1 year |

Implications for a post-2022-06-21 holdout:

- Sub-hourly history is **technically supported**, but acquisition is **API-keyed,
  points-limited, and windowed** (2 days of 2-minute data per call for real-time
  averages).
- Building a long retrospective record requires many authenticated calls and a
  documented QA pipeline; it is not an open archive download.
- Latitude/longitude are **not available from historical endpoints**; they must be
  captured from real-time metadata separately ([Download Sensor Locations](https://community.purpleair.com/t/download-sensor-locations/7872)).

## HCMC network coverage observed

During HCMC map inspection on 2026-08-20, **only one clearly visible public sensor**
was found in the HCMC metropolitan view: **952095 (VNJ-HCM)**. PurpleAir does publish
many HCMC district/ward map pages, which indicates platform support for the region,
but **practical public sensor density in HCMC appears sparse** compared with the
number of map landing pages.

This sparse coverage is itself a limitation for spatially representative external
validation across HealthyAir's multi-station network.

## Suitability for scientific external validation

### What is promising

- Official PurpleAir documentation confirms **2-minute server averages** exist.
- The verified sensor is **public**, reports **PM2.5**, and is **placed on PurpleAir's
  HCMC map**, so it is a concrete HCMC candidate rather than a generic "Vietnam"
  mention.
- Historical PM2.5 fields (`pm2.5_atm`, `pm2.5_alt`, channel A/B variants) are
  documented for research use with correction factors ([API Fields Descriptions](https://community.purpleair.com/t/api-fields-descriptions/4652)).

### What blocks Class A suitability today

| Issue | Why it matters |
|---|---|
| Numeric coordinates not retrieved | Cannot compute distance to HealthyAir stations or confirm exact placement without authenticated metadata. |
| Historical period not inspected | Post-2022-06-21 continuity, gaps, and exact earliest/latest timestamps remain unknown. |
| Community optical sensor | PurpleAir is not reference-grade; local HCMC correction and colocation would be required before validation claims. Prior HCMC PurpleAir work ended in 2021 and does not establish post-cutoff continuity ([AAQR HCMC PurpleAir study](https://doi.org/10.4209/aaqr.230186)). |
| Restrictive license | Redistribution, grantback, and one-level-removed use constraints complicate publishing a frozen external holdout inside an open research repo. |
| Sparse HCMC coverage | A single community sensor cannot represent city-wide multi-station forecasting validation. |
| API friction | External holdout construction would depend on PurpleAir account points, chunked 2-day real-time history pulls, and ongoing service availability. |

## Recommended next step if PurpleAir is pursued

1. Create a PurpleAir READ API key at [develop.purpleair.com](https://develop.purpleair.com/).
2. Query `GET https://api.purpleair.com/v1/sensors/952095?fields=sensor_index,name,latitude,longitude,private,location_type,date_created,last_seen,hardware,confidence,pm2.5`.
3. Query a **small** history window only (for example one day) with
   `average=real-time` and `fields=pm2.5_atm` to confirm post-2022-06-21 data exist
   and inspect timestamp cadence.
4. Run a bounding-box metadata query for HCMC to determine whether additional public
   outdoor sensors exist beyond 952095.
5. Review [PurpleAir data license](https://www.purpleair.com/license) against AIRPATH
   publication/redistribution requirements before any holdout is frozen.

## Classification rationale

**B. VERIFIED HCMC SENSOR + SUITABLE ONLY FOR PROTOTYPE/CURRENT-STATE USE**

Chosen because:

- A **specific public HCMC sensor** (`952095`, name `VNJ-HCM`) was verified on
  PurpleAir's official HCMC map with PM2.5 shown.
- **Numeric coordinates, historical span, and continuity** were **not** verified
  without authenticated API access.
- Even after metadata retrieval, PurpleAir would remain a **community sensor source
  under restrictive terms**, better suited to prototype sub-hourly integration or
  current-state demonstrations than to a standalone rigorous external validation
  holdout without additional calibration and licensing review.

**Not Class A** because scientific holdout suitability is not established.

**Not Class C** because an HCMC public sensor was identified and verified on the
official HCMC map, even though coordinates remain unconfirmed numerically.

## Sources

- [Ho Chi Minh City map](https://map.purpleair.com/vietnam/ho-chi-minh-city)
- [Selected sensor 952095 on map](https://map.purpleair.com/?select=952095)
- [PurpleAir API landing page](https://www.purpleair.com/api)
- [PurpleAir data license](https://www.purpleair.com/license)
- [PurpleAir attribution guide](https://www.purpleair.com/attribution)
- [Sensor Indexes and Read Keys](https://community.purpleair.com/t/sensor-indexes-and-read-keys/4000)
- [API Fields Descriptions](https://community.purpleair.com/t/api-fields-descriptions/4652)
- [Historical download guide (2-minute averages)](https://community.purpleair.com/t/how-to-get-historical-sensor-data-step-by-step-using-the-data-download-tool/11934)
- [History API span limits](https://community.purpleair.com/t/new-version-of-the-purpleair-api-on-july-18th/1251)
- [Map URL coordinates are viewport, not sensor location](https://community.purpleair.com/t/download-sensor-locations/7872)
- [Bounding-box discovery guidance](https://community.purpleair.com/t/finding-large-amounts-of-sensor-indexes-bounding-box-api-call/5688)
