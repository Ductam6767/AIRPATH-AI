# AIRPATH-AI Milestone 3B — road network and segment ETA foundation

## Scope

This milestone builds only the bounded road/route/ETA bridge needed for future
`PM2.5(X, T)` calls. It does **not** query PM2.5, calculate exposure, optimize
routes, recommend a route, estimate traffic, or build a web application.

## A–B. Pilot network size and graph representation

The network is restricted to the Milestone 3A convex hull of HealthyAir stations
2–6 (approximately 54.9 km²). It contains **63,013 OSM vertices**
and **142,930 directed segment records** before selecting a mode.

| mode      |   nodes |   directed_edges |
|:----------|--------:|-----------------:|
| walking   |   62922 |           142738 |
| motorbike |   57836 |           122455 |

Nodes are OSM road vertices. Directed edges are consecutive OSM way-node
segments and retain geometry, haversine length, `highway` type, way ID, name,
surface, maxspeed text when available, OSM direction, and walking/motorbike
traversability. The graph is not collapsed to one route polyline.

## Data source and reproducibility

- Source: [OpenStreetMap](https://www.openstreetmap.org), © OpenStreetMap
  contributors, ODbL 1.0.
- Retrieval: bounded Overpass QL query through `https://overpass-api.de/api/interpreter`.
- OSM database timestamp: **2026-08-20T07:56:51Z**.
- Retrieval timestamp: **2026-08-20T07:58:17.442705+00:00**.
- CRS: **WGS84 geographic coordinates, EPSG:4326**.
- Retained ways: **19,460**.
- Reproducible query and polygon are saved in
  `data/processed/road_network/metadata.json`.

Only segments whose endpoints and midpoint lie in the validated polygon are
retained. General and mode-specific `access`, `foot`, `vehicle`,
`motor_vehicle`, and `motorcycle` restrictions are applied. Vehicle oneway
direction is respected for motorbikes; ordinary vehicle oneway tags do not
restrict walking unless a specific pedestrian-direction tag says so.

## C. Supported road types

| mode      | road_type      |   directed_edges |
|:----------|:---------------|-----------------:|
| walking   | footway        |             9674 |
| walking   | living_street  |               12 |
| walking   | path           |             1036 |
| walking   | pedestrian     |              358 |
| walking   | primary        |             6426 |
| walking   | primary_link   |             1000 |
| walking   | residential    |            39794 |
| walking   | secondary      |             5998 |
| walking   | secondary_link |              348 |
| walking   | service        |            66422 |
| walking   | steps          |               98 |
| walking   | tertiary       |            11218 |
| walking   | tertiary_link  |              312 |
| walking   | unclassified   |               42 |
| motorbike | living_street  |               12 |
| motorbike | primary        |             3503 |
| motorbike | primary_link   |              567 |
| motorbike | residential    |            39300 |
| motorbike | secondary      |             4393 |
| motorbike | secondary_link |              188 |
| motorbike | service        |            65203 |
| motorbike | tertiary       |             9057 |
| motorbike | tertiary_link  |              177 |
| motorbike | trunk          |               13 |
| motorbike | unclassified   |               42 |

Walking excludes motorways/trunks and honors explicit pedestrian prohibitions.
Motorbike excludes footways, paths, pedestrian ways, cycleways, and steps and
honors explicit motorcycle/motor-vehicle prohibitions. OSM tagging is incomplete,
so “allowed” means not clearly prohibited by the retained tags; it is not a
guarantee of current legal or physical access.

## D–E. Baseline travel-time assumptions

| Mode | Configurable default | Interpretation |
|---|---:|---|
| Walking | **5 km/h** | Constant ordinary walking baseline |
| Motorbike | **25 km/h** | Constant urban research-prototype baseline |

For each edge, `duration = length / mode_speed`. These assumptions are explicit
in `DEFAULT_MODE_SPEED_KMH` and can be overridden per call. They do not use live
traffic, signals, intersection delay, congestion, slope, or user behavior and
must not be presented as real-world ETA accuracy.

## F. Candidate-route generation

`generate_candidate_routes()` snaps supported endpoints to the nearest
mode-traversable nodes and applies a deterministic loopless Yen-style K-shortest
path algorithm. Edge cost is constant-speed travel time; with one fixed speed
per mode this is equivalent to distance ranking. `K=5` is used. No air-quality
value enters generation or ranking.

## G. Example candidates

The reproducible example travels from station 6 (A) to station 5 (B), with both
coordinates inside the pilot polygon.

| route_id    | mode      |   edge_count |   total_distance_m |   total_travel_time_seconds |   origin_snap_distance_m |   destination_snap_distance_m |
|:------------|:----------|-------------:|-------------------:|----------------------------:|-------------------------:|------------------------------:|
| walking-1   | walking   |          126 |            3696.15 |                    2661.22  |                   21.262 |                        86.689 |
| walking-2   | walking   |          125 |            3696.46 |                    2661.45  |                   21.262 |                        86.689 |
| walking-3   | walking   |          125 |            3697.45 |                    2662.16  |                   21.262 |                        86.689 |
| walking-4   | walking   |          124 |            3697.76 |                    2662.39  |                   21.262 |                        86.689 |
| walking-5   | walking   |          125 |            3699.21 |                    2663.43  |                   21.262 |                        86.689 |
| motorbike-1 | motorbike |          141 |            3705.55 |                     533.6   |                   21.262 |                        86.689 |
| motorbike-2 | motorbike |          133 |            3705.84 |                     533.641 |                   21.262 |                        86.689 |
| motorbike-3 | motorbike |          138 |            3708.75 |                     534.06  |                   21.262 |                        86.689 |
| motorbike-4 | motorbike |          130 |            3709.03 |                     534.101 |                   21.262 |                        86.689 |
| motorbike-5 | motorbike |          140 |            3709.28 |                     534.136 |                   21.262 |                        86.689 |

The five alternatives can differ only slightly because OSM contains parallel
carriageways and dense short vertices. They are algorithmic alternatives, not
claims of five materially distinct traveler choices.

## H. Segment-level ETA example

Departure is **2026-08-20T08:00:00+07:00**. The following rows show
the first eight and final two segments of motorbike route 1:

|   segment_index | edge_id       |   start_node |    end_node |   segment_duration_seconds |   cumulative_elapsed_seconds | target_arrival_timestamp            | estimated_arrival_timestamp         |   representative_latitude |   representative_longitude |
|----------------:|:--------------|-------------:|------------:|---------------------------:|-----------------------------:|:------------------------------------|:------------------------------------|--------------------------:|---------------------------:|
|               1 | 242307853:0:f |   2498079018 |  2498079025 |                    1.69948 |                      1.69948 | 2026-08-20T08:00:00.849741709+07:00 | 2026-08-20T08:00:01.699483418+07:00 |                   10.7802 |                    106.659 |
|               2 | 32577686:2:f  |   2498079025 |  5772557724 |                    2.59963 |                      4.29911 | 2026-08-20T08:00:02.999297271+07:00 | 2026-08-20T08:00:04.299111124+07:00 |                   10.7802 |                    106.659 |
|               3 | 32577686:3:f  |   5772557724 |  5772557748 |                    4.69147 |                      8.99058 | 2026-08-20T08:00:06.644845485+07:00 | 2026-08-20T08:00:08.990579846+07:00 |                   10.78   |                    106.66  |
|               4 | 32577686:4:f  |   5772557748 |  2498079023 |                   11.6837  |                     20.6743  | 2026-08-20T08:00:14.832441495+07:00 | 2026-08-20T08:00:20.674303145+07:00 |                   10.7797 |                    106.66  |
|               5 | 609435506:2:f |   2498079023 |  2498079024 |                    1.51812 |                     22.1924  | 2026-08-20T08:00:21.433364923+07:00 | 2026-08-20T08:00:22.192426702+07:00 |                   10.7795 |                    106.66  |
|               6 | 242307850:7:r |   2498079024 |  2498079026 |                    1.84271 |                     24.0351  | 2026-08-20T08:00:23.113781978+07:00 | 2026-08-20T08:00:24.035137255+07:00 |                   10.7795 |                    106.66  |
|               7 | 242307850:6:r |   2498079026 |  5772557711 |                    4.38868 |                     28.4238  | 2026-08-20T08:00:26.229476693+07:00 | 2026-08-20T08:00:28.423816131+07:00 |                   10.7797 |                    106.661 |
|               8 | 242307850:5:r |   5772557711 | 11306427663 |                    3.55943 |                     31.9832  | 2026-08-20T08:00:30.203530176+07:00 | 2026-08-20T08:00:31.983244221+07:00 |                   10.7798 |                    106.661 |
|             140 | 244791434:1:f |   2520636903 |  2520636901 |                    4.96064 |                    529.148   | 2026-08-20T08:08:46.667601411+07:00 | 2026-08-20T08:08:49.147923189+07:00 |                   10.7766 |                    106.687 |
|             141 | 244791433:1:f |   2520636901 |  2520636899 |                    4.45195 |                    533.6     | 2026-08-20T08:08:51.373898781+07:00 | 2026-08-20T08:08:53.599874373+07:00 |                   10.7767 |                    106.687 |

For each segment:

- `entry_timestamp` is arrival at its start node;
- `target_arrival_timestamp` is estimated passage at its geometry midpoint;
- `estimated_arrival_timestamp` is arrival at its end node;
- `cumulative_elapsed_seconds` is measured through the segment end.

All route/segment records are saved under `data/processed/road_network/`.

## I. Validation

`tests/test_road_network_eta.py` verifies:

- pilot-boundary rejection;
- mode and oneway filtering;
- network serialization;
- five distinct connected route edge sequences;
- ordered edges and consistent geometry;
- non-negative durations;
- monotonic elapsed times and timestamps;
- route total time equals the segment-duration sum;
- walking and motorbike produce different baseline ETAs;
- unsupported car mode is rejected.

The real OSM station-6-to-station-5 example also produces five routes for each
supported mode. This is an implementation sanity check, not validation against
observed journeys.

## J. Known limitations

1. OSM is volunteered and changes over time; tags can be incomplete or stale.
2. Turn-restriction relations and conditional/time-dependent access are not yet
   interpreted.
3. Endpoints are snapped to road nodes; connector walking/riding time is
   reported as snap distance but not added to route duration.
4. Constant speeds omit traffic, signals, turns, slope, surface effects, and
   intersection delay.
5. K-shortest alternatives may overlap heavily and are not diversity-optimized.
6. Every OSM shape vertex is a graph node, so routes contain many short segments.
7. The network boundary is a scientific-support boundary, not an administrative
   service area or guarantee of spatial PM2.5 accuracy.
8. Exact second-level ETAs do not imply minute-level PM2.5 observations or
   predictions; current HealthyAir support remains hourly.

## K. Route-to-spatial interface

`spatial_target_records(segment_etas)` returns one record per ordered segment:

```python
{
    "route_id": ...,
    "segment_index": ...,
    "edge_id": ...,
    "latitude": representative_midpoint_latitude,
    "longitude": representative_midpoint_longitude,
    "target_time": estimated_midpoint_passage_timestamp,
}
```

These fields are structurally compatible with:

```python
estimate_pm25(latitude, longitude, target_time, station_values)
```

Milestone 3B deliberately does not call that function and does not source
`station_values`.

## L. Recommended next milestone

The next milestone should integrate **forecasted station values at each segment
target time** with the existing spatial estimator and quantify compounded
forecast-plus-spatial error. Exposure aggregation or route recommendation should
begin only after its temporal alignment, uncertainty propagation, and pilot-area
boundary behavior are validated.
