# AIRPATH-AI external PM2.5 data feasibility

Review date: 2026-08-19.

## Scope and method

This is a source inventory, not a data acquisition or model experiment. No
external observation file was downloaded, no source was merged with HealthyAir,
and no forecasting code, model, split, or raw project data was changed.

Claims below are limited to public provider documentation, station metadata,
peer-reviewed instrument descriptions, and documented API/archive behavior.
Real-time availability is not treated as proof of historical availability.
Archive file presence is not treated as proof of complete observations.

HealthyAir covers 2021-02-23 21:00 through 2022-06-21 17:00 in the current
project. Its public analytical file is hourly. Although the HealthyAir
instruments acquired measurements every 60 seconds, that does not make
unreleased minute records available as validation data.

## Candidate summary

Classification:

- **A** — suitable or promising for independent hourly external validation.
- **B** — potentially suitable for genuine sub-hourly validation after metadata,
  continuity, calibration, and licensing checks.
- **C** — suitable only for current-state, prospective, or demonstration use
  under presently documented access.
- **D** — unsuitable for the requested continuous PM2.5 validation.

| Source | Date range evidenced publicly | PM2.5 | Documented resolution | Coordinates | License/terms | Historical access | Suitability |
|---|---|---:|---|---|---|---|---|
| AirNow, U.S. Consulate General HCMC | Research confirms 2021-01-01–2023-06-30; an EPA-supplied secondary archive has monthly HCMC files through 2024-01. Exact first/last observations and gaps require inspection. | Yes, µg/m³ | **Hourly** concentration; UTC begin-hour timestamps | About 10.782773, 106.700035; published values differ by tens of metres | Preliminary AirNow data; attribution and use caveats required | Public hourly files; API registration for web services | **A — recommended hourly external-validation candidate** |
| OpenAQ copy of AirNow | Same underlying diplomatic-post series; HCMC-specific latest timestamp not verified without authenticated metadata | Yes | Original measurements plus hourly aggregates; AirNow upstream is hourly | Location metadata available through authenticated API; exact current location ID not established here | Source-specific license plus OpenAQ terms and attribution | Authenticated v3 API | **A — access route only; not independent of AirNow** |
| Sensor.Community HCMC sensors 96485, 34142, 96463 | Post-cutoff activity is indicated by searchable third-party station metadata; exact station periods and gaps are unknown until archive inspection | Yes (`P2`) | Default firmware about **145 seconds plus transmission**, configurable and irregular; map uses recent/five-minute presentation | Textual HCMC addresses found; numeric coordinates not verified | Presented as open data with attribution; exact current database-license terms should be confirmed before redistribution | Public daily/monthly archive and recent API | **B — strongest open sub-hourly feasibility candidate, conditional on QA** |
| PurpleAir HCMC coverage | HCMC city/district/ward coverage pages exist; specific post-cutoff sensor IDs and periods were not verified | Yes | Public server history normally **two-minute averages**; API also supplies coarser aggregates | API can provide coordinates, but no verified HCMC sensor index/coordinate was established | Restrictive API/data license, attribution, redistribution, and grant-back provisions | Authenticated, points-based historical API by sensor | **B conditional — temporal support is good, station identity/access unresolved** |
| Vietnam CEM/EnviSoft, 200 Lý Chính Thắng | Post-cutoff/current publication is visible through CEM-derived feeds; exact start, end, and gaps unknown | Yes | National system documents **five-minute intermediate averages** and hourly products; station analyzer cadence unverified | Street address known; numeric coordinates not verified | No open bulk-data license found | Historical management portal requires login; no anonymous export/API documented | **A/B conditional on an official concentration export** |
| IQAir HCMC station network | Current and rolling recent data; no public long-term station-level hourly archive documented | Yes | Published platform product is **hourly average** | Precise station coordinates may require an eligible API plan | Aggregated data are not established as openly redistributable | Free rolling 48-hour hourly view; longer station history not documented publicly | **C — prospective/current-state use, not retrospective holdout construction** |
| WAQI/AQICN HCMC feeds | Current feeds and daily historical products; station-specific hourly/raw history is request-dependent | Often PM2.5 AQI; concentration availability varies | Current snapshot; free history is **daily pollutant AQI**, not hourly concentration | Varies by feed; U.S. Consulate coordinates are better obtained from AirNow literature | Restrictive attribution, caching, redistribution, and non-official-use terms | Tokenized current API; discretionary hourly/raw history requests | **C for screening; use original provider for validation** |
| HCMC periodic monitoring reports | Post-2022 reports exist, including 2024 campaigns | Not consistently documented | Campaign/periodic samples, not continuous time series | Report-specific and often inaccessible from landing pages | No machine-readable open license established | Report pages, not a stable observation API | **D — unsuitable for continuous forecasting validation** |

### Required metadata inventory

“Unknown” means the value was not established from public documentation without
acquiring observations or authenticated metadata; it is not silently inferred.

| Source / station | Station ID | Coordinates | Pollutants documented | Earliest evidenced | Latest evidenced | Timezone and timestamp form |
|---|---|---|---|---|---|---|
| AirNow U.S. Consulate | Public AQSID not established | Published approximately 10.782773, 106.700035 | PM2.5 confirmed; others not claimed | At least 2021-01-01 in cited research | Monthly file coverage through 2024-01; exact last observation unknown | UTC/GMT begin-hour; `MM/DD/YY\|HH:MM`, separate GMT offset |
| OpenAQ AirNow copy | Current OpenAQ location/sensor IDs unknown without authenticated query | Available from location metadata; not queried | Same AirNow PM2.5 source | Same underlying source | HCMC-specific last timestamp unknown | ISO-8601 UTC and local; exclusive time-ending semantics |
| Sensor.Community, Alley 165 Nguyễn Thái Bình | 96485 | Unknown | PM2.5 (`P2`), typically PM10 (`P1`); environmental fields depend on attached sensor | Unknown | Post-cutoff activity indicated; exact timestamp unknown | Archive text `YYYY-MM-DDTHH:MM:SS`, interpreted as UTC |
| Sensor.Community, Ngô Quang Thắm | 34142 | Unknown | PM2.5 and typically PM10; hardware unverified | Unknown | Post-cutoff activity indicated; exact timestamp unknown | Same Sensor.Community UTC archive convention |
| Sensor.Community, Ký Con Street | 96463 | Unknown | PM2.5 and typically PM10; hardware unverified | Unknown | Post-cutoff activity indicated; exact timestamp unknown | Same Sensor.Community UTC archive convention |
| PurpleAir HCMC candidates | Individual sensor indexes unknown | Unknown pending authenticated metadata | Optical PM1/PM2.5/PM10 fields; temperature/humidity depend on device/API fields | Unknown | Unknown | Unix UTC or ISO-8601 through API |
| CEM, 200 Lý Chính Thắng | `31390912357075263208060500522`; WAQI mirror `A476182` | Unknown | PM2.5 confirmed; complete station parameter list unverified | Unknown | Post-cutoff/current publication evidenced | Native public timestamp convention unverified; WAQI responses include explicit timezone fields |
| IQAir HCMC contributors | Public page slug/name; durable numeric IDs generally unavailable | Usually map/API metadata; exact values not verified | PM2.5 common; other pollutants vary by contributor | Rolling-view dependent | Current/rolling 48 hours | Website uses local interval labels; API serialization is plan-specific |
| WAQI HCMC feeds | Feed IDs vary (`H8767`, `A476182`, etc.) | Feed-specific | Pollutant AQI fields vary; raw concentrations not guaranteed | Feed-specific/unknown | Current snapshot or requested history | ISO-like feed time plus explicit `tz`; verify each feed |
| HCMC periodic reports | Report/campaign identifiers | Report-specific | PM2.5 not guaranteed in every campaign | Report-specific | 2024 reports evidenced | Sampling time/zone must be read from each full report |

## 1. AirNow / U.S. Department of State monitor

### Station, instrument, and variables

- **Provider/operator:** U.S. Department of State, U.S. Consulate General Ho
  Chi Minh City; distributed by U.S. EPA AirNow.
- **Station name:** U.S. Consulate General Ho Chi Minh City / US Diplomatic
  Post: Ho Chi Minh City.
- **Location:** 4 Lê Duẩn, District 1.
- **Published coordinates:** 10.782773, 106.700035. Other peer-reviewed sources
  report rounded or slightly different coordinates, approximately
  10.7831–10.7834, 106.7001–106.7006. The difference is tens of metres and
  should be resolved from the acquired station metadata rather than silently
  selecting one value.
- **Instrument:** Met One BAM-1020 beta-attenuation monitor, described as a
  reference-grade diplomatic-post monitor.
- **Verified pollutant:** hourly PM2.5 mass concentration in µg/m³. Other
  pollutants should not be attributed to this HCMC station without station
  metadata.

Peer-reviewed station/instrument sources:

- [AAQR HCMC U.S. Consulate study](https://aaqr.org/articles/aaqr-23-08-oa-0186)
- [Atmosphere site description](https://doi.org/10.3390/atmos14030579)
- [PM2.5 forecast-system site coordinates](https://aaqr.org/articles/aaqr-21-05-oa-0108)

### Date availability and continuity

A study used this station from 2021-01-01 through 2023-06-30, directly
establishing observations after HealthyAir ended:
[Atmosphere 2024](https://doi.org/10.3390/atmos15101163).

An EPA-support-supplied secondary archive contains monthly HCMC files throughout
2022 and 2023 and for January 2024:
[archive and provenance](https://github.com/dolekhanhdang/Air-Quality-Data-from-U.S.-Embassies).
That repository is not the original provider. Monthly files do not prove every
hour is present. Exact first/last timestamps, invalid codes, and completeness
must be established from an approved observation-level inspection.

The worldwide diplomatic feed was suspended in March 2025. This does **not**
prove that the HCMC monitor reported continuously until that date. Current
third-party pages must not be used to infer continued official operation.

### Resolution, timezone, and format

AirNow's official hourly format is:

```text
MM/DD/YY|HH:MM|AQSID|SiteName|GMTOffset|Parameter|Units|Value|Source
```

The date/time is UTC/GMT and denotes the **beginning** of the one-hour
measurement interval. A value at 17:00 covers 17:00–17:59 UTC. HCMC local time
is UTC+07:00. AirNow republishes files more than once per hour for completeness;
publication frequency is not measurement resolution.

Official documentation:

- [AirNow Hourly Data File fact sheet](https://docs.airnowapi.org/docs/HourlyDataFactSheet.pdf)
- [AirNow Hourly AQ Observations fact sheet](https://docs.airnowapi.org/docs/HourlyAQObsFactSheet.pdf)
- [AirNow API/file-product guidance](https://docs.airnowapi.org/docs/AirNowAPIFactSheet.pdf)

### Access and terms

Historical files follow date/hour directory patterns under
`files.airnowtech.org`; AirNow recommends file products for long periods.
Web-service access requires registration. AirNow observations are preliminary,
subject to revision, require source/AirNow attribution, and are not validated
regulatory data or an unrestricted basis for official trend claims:
[AirNow data-use guidelines](https://docs.airnowapi.org/docs/DataUseGuidelines.pdf).

### HealthyAir overlap and distance

There is temporal overlap from HealthyAir's start through 2022-06-21. It is not
a co-location experiment: HealthyAir used Sensoronic PM SCAN instruments at six
different environments, while AirNow used a BAM-1020 at the consulate.

Haversine distances from 10.782773, 106.700035 to published HealthyAir
coordinates are:

| HealthyAir station | Approximate distance |
|---:|---:|
| 1 | 14.277 km |
| 2 | 10.179 km |
| 3 | 9.458 km |
| 4 | 4.139 km |
| 5 | **1.514 km** |
| 6 | 4.440 km |

Station 5 is nearest but is not co-located. Spatial differences and instrument
differences prevent treating paired timestamps as duplicate measurements.
HealthyAir metadata and coordinates:
[dataset article](https://pmc.ncbi.nlm.nih.gov/articles/PMC9720438/).

### AIRPATH suitability

- **Hourly:** suitable for a genuinely later external temporal evaluation after
  gap, unit, timestamp, and station-ID checks.
- **Sub-hourly:** unsuitable; twice-hourly file refreshes are not observations.
- **Minute-level:** unsuitable.

## 2. OpenAQ

OpenAQ is an aggregator and alternative access layer, not a second HCMC
reference monitor. Its relevant diplomatic-post values originate from AirNow.
Using both AirNow and OpenAQ in an evaluation would duplicate the same source.

OpenAQ v3 exposes original reported measurements and hourly aggregates through
sensor endpoints, with authenticated API access. It returns ISO-8601 UTC and
local timestamps and harmonizes records to an exclusive **time-ending**
convention: an hourly timestamp of 03:00 represents 02:00–02:59. This differs
from AirNow's begin-hour convention and can create a one-hour alignment error if
ignored.

Documentation:

- [OpenAQ measurements](https://docs.openaq.org/resources/measurements)
- [Dates, times, and timezones](https://docs.openaq.org/using-the-api/dates-datetimes)
- [Licenses resource](https://docs.openaq.org/resources/licenses)
- [Terms of use](https://docs.openaq.org/about/terms)

The exact current HCMC OpenAQ location/sensor IDs, coordinates, station-specific
license label, and final timestamp were not established because authenticated
metadata were not queried. Any later acquisition must preserve original
provider attribution and verify the source-specific license.

## 3. Sensor.Community

### HCMC candidates

Searchable AirNet/WAQI metadata attributes these HCMC stations to
Sensor.Community:

| Sensor ID | Publicly described location | Coordinates | Exact period |
|---:|---|---|---|
| 96485 | Alley 165 Nguyễn Thái Bình, District 1 | Not verified | Unknown |
| 34142 | Ngô Quang Thắm road, Nhà Bè | Not verified | Unknown |
| 96463 | Ký Con Street, District 1 | Not verified | Unknown |

The third-party metadata indicates activity well after 2022-06-21, but its
relative “last seen” labels are not exact observation timestamps. The sensors
were absent from the recent live API window at the time of this review. That
means only that they were not currently reporting; it does not establish their
historical range.

Relevant access points:

- [Sensor.Community archive](https://archive.sensor.community/)
- [AirNet Vietnam station inventory](https://aqicn.org/station/country/vn/vietnam/)
- [Recent sensor API pattern](https://data.sensor.community/airrohr/v1/sensor/96485/)

### Resolution and timestamps

Default community firmware reports every 145 seconds plus transmission time.
Operators can change this setting, sensors are not synchronized, and outages
make timestamps irregular. Archived timestamps are UTC in
`YYYY-MM-DDTHH:MM:SS` form without an explicit suffix. For common particulate
files, `P2` is PM2.5 and `P1` is PM10.

Documentation:

- [Default cadence](https://forum.sensor.community/t/frequency-of-measurements/265)
- [Configurability and synchronization](https://forum.sensor.community/t/are-all-sensor-community-sensors-synchronized/2479)
- [Archive timezone and PM fields](https://forum.sensor.community/t/time-zone-information-of-archived-measurements/496)
- [Open-data/attribution statement](https://forum.sensor.community/t/time-series-data/2751)

### Scientific limitations

Sensor.Community is a platform, not one instrument model. The HCMC sensors'
models, outdoor status, coordinates over time, inlet heights, maintenance, and
calibration are unknown. Common low-cost optical sensors such as SDS011 are
sensitive to humidity and aerosol composition; HCMC-specific calibration cannot
be assumed from European studies. Volunteer sensors may relocate while
retaining or changing identifiers.

No distance to HealthyAir can be calculated without verified numeric
coordinates. Temporal overlap is also unknown until archive manifests or
records are inspected.

### AIRPATH suitability

- **Hourly:** conditionally suitable after completeness thresholds, relocation
  checks, model identification, humidity QA, and local calibration assessment.
- **Sub-hourly:** potentially suitable at roughly 2.5-minute/irregular cadence.
- **One-minute:** unsuitable; typical cadence exceeds one minute.

## 4. PurpleAir

Official PurpleAir pages index HCMC city, district, and ward coverage, but this
review did not establish a specific public post-2022 HCMC `sensor_index`,
coordinate, station name, or exact reporting interval. Those require an
authenticated geographic metadata query before historical access.

- [PurpleAir HCMC map](https://map.purpleair.com/vietnam/ho-chi-minh-city)
- [PurpleAir API](https://www.purpleair.com/api)
- [Bounding-box sensor discovery guidance](https://community.purpleair.com/t/finding-large-amounts-of-sensor-indexes-bounding-box-api-call/5688)

Public server history normally consists of two-minute averages. The historical
API accepts coarser averaging windows and one sensor per request. Access requires
an API key and uses a points model. Unix timestamps are UTC; ISO-8601 is also
accepted. Exact interval limits can change and must be taken from the live API
documentation.

PurpleAir's license requires attribution and includes restrictions on
redistribution, derivative use, and API-like resale:
[PurpleAir data license](https://www2.purpleair.com/pages/license).

PurpleAir optical counters offer valuable channel-level QA but require
humidity/aerosol correction. A U.S.-derived correction must not be assumed
valid in HCMC. A published HCMC PurpleAir deployment ended in 2021 and therefore
does not establish post-cutoff continuity:
[HCMC PurpleAir study](https://doi.org/10.4209/aaqr.230186).

No HealthyAir distance or overlap can be assigned to the current HCMC candidates
until sensor IDs, coordinates, and periods are verified.

### AIRPATH suitability

- **Hourly:** conditionally suitable after station discovery and QA.
- **Sub-hourly:** potentially suitable at native two-minute server averages.
- **One-minute:** unsuitable from public historical data.

## 5. Official Vietnam CEM / EnviSoft

The official automatic-monitoring management system is operated by Vietnam's
environmental monitoring authorities. A publicly mirrored HCMC station is:

- **Native/CEM code:** `31390912357075263208060500522`
- **WAQI mirror:** `A476182`
- **Location:** 200 Lý Chính Thắng, District 3
- **PM2.5:** present in current/post-cutoff publications
- **Coordinates, analyzer model, start/end dates, and gaps:** not publicly
  verified in this review

Official system documentation describes instantaneous analyzer input,
five-minute intermediate averages, hourly products, and daily products. It does
not establish the native analyzer cycle or public availability of five-minute
records at this station.

- [CEM EnviSoft description](https://cem.gov.vn/gioi-thieu-chung/phan-mem-quan-ly-du-lieu-quan-trac-tu-dong-envisoft)
- [EnviSoft portal](https://envisoft.cem.gov.vn/)
- [VN Air public information application](https://envisoft.andro.io/)
- [CEM-derived network listing](https://aqicn.org/network/vn-cem/vn/)

EnviSoft presents authenticated historical-management functions; no anonymous,
documented concentration API or bulk CSV export and no explicit open-data
license were found. Public AQI charts do not establish raw concentration access.

Lý Chính Thắng and HealthyAir station 5 are both in District 3 but at different
addresses. Without official coordinates and instrument metadata, distance and
comparability cannot be quantified.

### AIRPATH suitability

- **Hourly:** promising if CEM provides concentration exports and metadata.
- **Sub-hourly:** potentially five-minute, but public availability is unverified.
- **Minute-level:** unknown and cannot be claimed.

## 6. IQAir

IQAir currently lists many HCMC contributors, including government, school,
institutional, commercial, and community monitors. The public station pages do
not provide a durable long-term station-level research archive or verified
coordinates in fetched metadata.

The free platform documents:

- past 48 hours as hourly averages;
- past 30 days as daily averages;
- longer city-level summaries.

Source:
[IQAir historical-data documentation](https://www.iqair.com/support/knowledge-base/how-can-i-access-historical-data-on-the-iqair-platform).

The website uses local-time interval labels. API timestamp format, station
coordinates, long-term access, and storage/redistribution rights depend on the
endpoint and plan. Platform visibility does not grant an open license over all
contributors' observations.

### AIRPATH suitability

- **Hourly:** suitable prospectively or for a rolling current-state evaluation.
- **Sub-hourly/minute:** unsuitable; the documented platform product is hourly.
- **Untouched 2022–present holdout:** unsuitable under publicly documented free
  history.

## 7. WAQI/AQICN and municipal reports

WAQI provides tokenized real-time station snapshots and a historical platform.
The freely downloadable historical files are daily pollutant AQI, not hourly
raw PM2.5 concentration. Hourly/raw history can be requested but fulfillment is
not guaranteed. Terms require attribution to WAQI and the original provider and
restrict caching, redistribution, and official use.

- [WAQI API](https://aqicn.org/api/)
- [Historical platform](https://aqicn.org/data-platform/register/)
- [Data request form](https://aqicn.org/data-platform/query/)
- [Terms](https://aqicn.org/data-platform/tos/)

For the U.S. Consulate, AirNow should be used as the primary source. For CEM,
an official export is preferable to a transformed WAQI feed. Other HCMC feeds
need original-provider, instrument, coordinate, and history verification.

HCMC municipal monitoring pages establish that post-2022 campaigns occurred,
but periodic campaign reports are not continuous station time series. They are
unsuitable for hourly or arrival-time validation.

## 8. Resolution-specific AIRPATH assessment

AIRPATH's eventual query is conceptually `PM2.5(X, T)`, where `X` is a location
and `T` is estimated traveler arrival time. A monitoring source validates only
the temporal and spatial support it actually observes.

| Validation claim | Required observations | Feasible candidates | What cannot be claimed |
|---|---|---|---|
| Hourly monitored-station forecasting | Exact hourly PM2.5 timestamps, units, timezone, station continuity, and sufficient post-2022 records | AirNow strongest; OpenAQ as duplicate access route; CEM conditional; Sensor.Community/PurpleAir after aggregation and QA | Road-level or minute-level accuracy |
| 5–30 minute monitored-location forecasting | Genuine sub-hourly observations with clock synchronization, completeness rules, calibration, and stable coordinates | Sensor.Community conditional; PurpleAir conditional; CEM five-minute data if officially released | Exact arbitrary-minute truth from hourly products |
| 1–2 minute monitored-location forecasting | Genuine one-/two-minute observations and validated instrument response | PurpleAir supports two-minute, not one-minute, history; no verified one-minute candidate | One-minute accuracy |
| Road-segment arrival-time validation | Spatially representative road/mobile observations synchronized to traversal/traffic timestamps | None of the inventoried fixed-station sources alone | Direct road-level measurement or segment exposure validation |

Sub-hourly data should remain at native timestamps during QA. Aggregating genuine
two-/three-/five-minute observations to 10-, 15-, 30-, or 60-minute intervals is
scientifically different from interpolating hourly values. Any binning protocol
must predefine coverage thresholds and interval semantics.

## Recommendation

### Priority 1 — AirNow U.S. Consulate (**A**)

Use as the first feasibility target for a genuinely later **hourly** external
evaluation. Before acquisition, confirm:

1. authoritative station/AQSID and coordinates;
2. exact first and last post-2022 timestamps;
3. hourly completeness and invalid-value codes;
4. UTC begin-hour conversion to HealthyAir's documented/verified timezone;
5. PM2.5 units and preliminary-data caveats;
6. publication and attribution requirements.

It provides temporal continuation and stronger instrumentation, but not
HealthyAir station continuity or road-level validation.

### Priority 2 — Sensor.Community (**B, conditional**)

Perform a metadata/archive feasibility probe for IDs 96485, 34142, and 96463
only after approval. Establish sensor model, coordinates over time, outdoor
status, exact dates, gaps, cadence, humidity fields, and relocation history.
This is the strongest open candidate for genuine sub-hourly observations, but
not one-minute truth.

### Priority 3 — CEM and PurpleAir (**A/B conditional**)

- Request an official CEM concentration export and station metadata for
  Lý Chính Thắng; do not scrape AQI charts.
- Use an authenticated PurpleAir bounding-box metadata query only after
  licensing review, then assess individual sensor histories and local
  calibration suitability.

### Current/demo only — IQAir and WAQI (**C**)

Use for prospective/current-state demonstrations or source discovery, not as a
retrospective untouched long-term validation set under current public access.

### Unsuitable — periodic reports (**D**)

Campaign reports cannot support continuous hourly, sub-hourly, or arrival-time
forecast validation.

## Decision for the next step

No candidate should be merged into HealthyAir automatically. The next authorized
step should be a narrowly scoped acquisition audit—not model training—starting
with AirNow station identification and completeness metadata. Newer observations
should remain an external dataset with independent provenance. Distribution
shift from instrument type, site environment, season, policy, traffic, and
calendar period must be quantified before interpreting forecasting error.

