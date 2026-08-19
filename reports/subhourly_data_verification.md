# Sensor.Community HCMC sub-hourly data verification

Review date: 2026-08-19.

## Decision

**Not yet directly verified.**

There is credible third-party evidence that three Ho Chi Minh City feeds were
attributed to Sensor.Community. Sensor.Community itself documents genuine
sub-hourly PM2.5 observations and a programmatically accessible historical
archive. However, under this verification's small-request constraint, the HCMC
feed identifiers could not be resolved to first-party Sensor.Community archive
files or current API records.

Consequently, this review cannot verify:

- numeric sensor coordinates;
- exact earliest and latest observation timestamps;
- actual station-specific sampling intervals;
- PM2.5 values and timestamps in the historical files;
- station-specific continuity or suitability for external validation.

No observation dataset was downloaded.

## Checks performed

1. Reviewed Sensor.Community's official live API, archive index, cadence,
   timestamp, PM-field, and licensing documentation.
2. Reviewed WAQI/AirNet station inventory and validation pages that attribute
   HCMC feeds to Sensor.Community.
3. Queried only the three small first-party live sensor endpoints.
4. Inspected archive directory metadata and issued lightweight metadata/HEAD
   probes for common particulate-sensor file types near the third-party
   “last seen” dates.
5. Did not download the multi-gigabyte monthly archive files or scan the full
   historical database.

## 1. Evidence that HCMC feeds exist

WAQI/AirNet identifies the following feeds as “Citizen Science project
sensor.community”:

| Provider identifier shown by WAQI | HCMC location shown by WAQI | WAQI recency label on review date | First-party status |
|---:|---|---|---|
| 96485 | Alley 165 Nguyễn Thái Bình, District 1 | 220 days ago, approximately 2026-01-11 | Not resolved |
| 34142 | Ngô Quang Thắm road, Long Thới Commune, Nhà Bè | 277 days ago, approximately 2025-11-15 | Not resolved |
| 96463 | Ký Con Street, Nguyễn Thái Bình Ward, District 1 | 320 days ago, approximately 2025-10-03 | Not resolved |

Sources:

- [WAQI/AirNet Vietnam inventory](https://aqicn.org/station/country/vn/vietnam/vn/)
- [Ký Con station page](https://aqicn.org/station/vietnam-ph%C6%B0%E1%BB%9Dng-b%E1%BA%BFn-th%C3%A0nh-ky-con-street/)
- [Ký Con validation page](https://aqicn.org/station/validation/@564976/)

The Ký Con validation page explicitly calls the station:

> Citizen Science project sensor.community 96463

and gives the HCMC street address. These are WAQI records, not first-party
Sensor.Community metadata. The numeric values may be upstream/provider
identifiers, but this review could not prove that they are the particulate
component IDs used in Sensor.Community archive filenames.

The approximate dates above are arithmetic conversions of relative WAQI labels,
not original measurement timestamps. They must not be treated as exact first or
last observations.

## 2. Direct first-party API result

The official recent-data endpoint pattern is:

```text
https://data.sensor.community/airrohr/v1/sensor/{sensor_id}/
```

Results during this review:

| Queried identifier | Response |
|---:|---|
| 96485 | `[]` |
| 34142 | `[]` |
| 96463 | `[]` |

Endpoints:

- [96485](https://data.sensor.community/airrohr/v1/sensor/96485/)
- [34142](https://data.sensor.community/airrohr/v1/sensor/34142/)
- [96463](https://data.sensor.community/airrohr/v1/sensor/96463/)

An empty result is consistent with an offline sensor because this API represents
recent data. It does not prove that no historical data exist. It also means the
current first-party endpoint cannot provide coordinates, sensor model, PM2.5
values, or timestamps for these identifiers.

## 3. Coordinates

**No numeric coordinates were directly verified.**

WAQI supplies textual addresses, but no numeric coordinates were exposed in the
fetched station metadata. Geocoding an address would locate the address, not
prove the monitor's recorded coordinate. Because the first-party API responses
were empty, their `location.latitude`, `location.longitude`, indoor/outdoor
status, altitude, and exact-location flag could not be checked.

The feeds therefore cannot yet be spatially matched to HealthyAir stations.

## 4. Native observation interval

Sensor.Community documents a default firmware interval of **145 seconds plus
transmission time**, approximately 2.4–2.5 minutes:

- [Default measurement frequency](https://forum.sensor.community/t/frequency-of-measurements/265)
- [Upload-frequency guidance](https://forum.sensor.community/t/how-often-should-i-send-data-to-https-api-sensor-community-v1-push-sensor-data/785)
- [Synchronization and configurable cadence](https://forum.sensor.community/t/are-all-sensor-community-sensors-synchronized/2479)

This is genuine sub-hourly platform behavior, not interpolation. But it is a
default, not a guarantee:

- operators can change the interval;
- sensors are not synchronized;
- transmission delays vary;
- outages create irregular timestamp gaps;
- the API's `sampling_rate` field is often null.

Therefore the **actual intervals of the three HCMC feeds remain unverified**.
They must be calculated from their original historical timestamps if files are
located.

## 5. Earliest and latest historical observations

**Unknown for all three HCMC candidates.**

Sensor.Community exposes browsable daily sensor-specific files and monthly
archives:

- [Historical archive](https://archive.sensor.community/)
- [Monthly archive index](https://archive.sensor.community/csv_per_month/)

Daily files normally follow a pattern such as:

```text
YYYY-MM-DD_sensor-type_sensor-ID.csv
YYYY-MM-DD_sensor-type_sensor-ID.csv.gz
```

Lightweight probes for IDs 96485, 34142, and 96463, using common particulate
sensor types near the approximate WAQI recency dates, did not locate matching
files. This does **not** prove absence because:

- the WAQI provider ID may differ from the Sensor.Community archive component
  ID;
- the relative date may be rounded;
- the particulate sensor type is unknown;
- the station may have changed component IDs or location;
- only narrow metadata probes were permitted.

The monthly sensor-type archives are multi-gigabyte files. They were not
downloaded.

## 6. PM2.5 concentration values and timestamp semantics

At the platform level, Sensor.Community particulate archives provide:

- `timestamp`: archived in UTC, commonly serialized as
  `YYYY-MM-DDTHH:MM:SS` without an explicit timezone suffix;
- `P2`: PM2.5 concentration;
- `P1`: PM10 concentration.

Source:
[archive timezone and PM field definitions](https://forum.sensor.community/t/time-zone-information-of-archived-measurements/496).

Sensor.Community's API documentation also identifies `P2` as PM2.5 and exposes
sensor model and location objects:
[API field documentation](https://api-sensor-community.bessarabov.com/).

These facts verify that the **platform can provide timestamped PM2.5
concentrations**. They do not verify that the three HCMC identifiers have
retrievable records in that schema. No HCMC observation row was read in this
review.

## 7. Programmatic historical access

**Yes at platform level; unresolved for the candidate identifiers.**

The archive is accessible over HTTP without requiring a model-data merge. Daily
files can be retrieved by date, sensor type, and archive sensor ID, while
monthly archives are grouped by sensor type.

A research acquisition can be automated once all of the following are known:

1. first-party particulate component ID;
2. sensor model/archive filename prefix;
3. stable coordinates and location history;
4. desired date bounds.

Those mappings are currently missing for the three WAQI-attributed HCMC feeds.

## 8. Continuity

**Insufficient evidence to assess continuity.**

No valid candidate time series was obtained, so this review cannot calculate:

- observation count;
- median or modal time difference;
- interval distribution;
- daily/hourly coverage;
- longest gap;
- relocation periods;
- proportion of expected sub-hourly or hourly bins meeting completeness rules.

The WAQI “last seen” labels show, at most, that the feeds were recognized after
2022-06-21. They provide no evidence of continuous operation between that date
and the last report.

The sensors are currently absent from the recent first-party API. Volunteer
low-cost sensors can lose power/network access, move, or stop reporting.
Continuity cannot be assumed.

## 9. Licensing and prototype use

Sensor.Community describes itself as an open environmental data network and its
website links a “DB Contents License”:

- [Sensor.Community](https://sensor.community/en/)
- [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/)
- [Database Contents License (DbCL) 1.0](https://opendatacommons.org/licenses/dbcl/1-0/)

Community guidance states that archive data may be used with source attribution:
[open-data attribution statement](https://forum.sensor.community/t/time-series-data/2751).

For a research prototype, the conservative requirements are:

- attribute Sensor.Community and record archive URLs/access dates;
- retain provenance and original identifiers;
- document transformations and quality-control decisions;
- review ODbL attribution/share-alike and DbCL content terms before publishing a
  redistributed or derived database;
- do not imply that low-cost observations are regulatory/reference measurements.

The exact license notice attached to any acquired archive product should be
captured at acquisition time rather than relying only on this feasibility
summary.

## Final verification result

| Requested item | Result |
|---|---|
| HCMC PM2.5 sensors exist | **Partially verified:** three HCMC feeds are attributed to Sensor.Community by WAQI, but not resolved to active first-party records |
| Sensor IDs | **Candidate provider IDs:** 96485, 34142, 96463; first-party archive component mapping unverified |
| Coordinates | **Not verified** |
| Native interval | **Platform default ~145 seconds plus transmission; candidate-specific cadence not verified** |
| Earliest/latest observations | **Not verified** |
| Programmatic history | **Available platform-wide; candidate retrieval mapping unresolved** |
| PM2.5 values and timestamps | **Documented platform schema (`P2`, UTC timestamp); no HCMC row directly verified** |
| Continuity | **Not verifiable; insufficient evidence** |
| Research-prototype terms | **Open-data use appears feasible with attribution and ODbL/DbCL review** |

### Conclusion

This review does **not** establish a usable Sensor.Community HCMC external
validation dataset. It establishes only that:

1. WAQI recognized HCMC feeds attributed to Sensor.Community;
2. Sensor.Community supports genuine sub-hourly PM2.5 observations and
   programmatic archives in general.

Before AIRPATH treats Sensor.Community as Data V2, a first-party mapping from
each HCMC feed to its particulate archive component ID is required. Without that
mapping, coordinates, exact period, actual cadence, PM2.5 rows, and continuity
cannot be verified under the no-large-download constraint.

