# AIRPATH-AI Milestone 3B — road network and segment ETA foundation

## Scope

This milestone builds only the bounded road/route/ETA bridge needed for future
`PM2.5(X, T)` calls. It does **not** query PM2.5, calculate exposure, optimize
routes, recommend a route, estimate traffic, or build a web application.

## A–B. Pilot network size and graph representation

The network is restricted to the Milestone 3A convex hull of HealthyAir stations
2–6 (approximately 54.9 km²). It contains **62,463 OSM vertices**
and **141,161 directed segment records** before selecting a mode.

| mode      |   all_mode_nodes |   all_mode_directed_edges |   routing_component_nodes |   routing_component_directed_edges |
|:----------|-----------------:|--------------------------:|--------------------------:|-----------------------------------:|
| walking   |            62401 |                    141036 |                     59738 |                             135964 |
| motorbike |            57252 |                    120668 |                     55037 |                             116955 |

Nodes are OSM road vertices. Directed edges are consecutive OSM way-node
segments and retain geometry, haversine length, `highway` type, way ID, name,
surface, maxspeed text when available, OSM direction, and walking/motorbike
traversability. The graph is not collapsed to one route polyline. Endpoint
snapping uses each mode's largest strongly connected component, preventing
routes from starting on disconnected islands; all retained components remain in
the serialized research graph.

## Data source and reproducibility

- Source: [OpenStreetMap](https://www.openstreetmap.org), © OpenStreetMap
  contributors, ODbL 1.0.
- Retrieval: bounded Overpass QL query through `https://overpass-api.de/api/interpreter`.
- Requested historical snapshot: **2026-08-20T07:56:51Z**.
- Overpass server base timestamp reported with the response:
  **2026-08-20T08:08:01Z**.
- Retrieval timestamp: **2026-08-20T08:09:17.516309+00:00**.
- CRS: **WGS84 geographic coordinates, EPSG:4326**.
- Retained ways: **19,279**.
- Filter profile: **airpath-osm-filter-v2**.
- AOI checksum: `1ce2426ff477c23c62ea665adc61aa3fab0561ca8903adb77a4eba4e943bb3b6`.
- Canonical Overpass-response checksum:
  `cfeb8ec01e2179af75dbb7c0915470f486a46066e3757e6da3d50df17f45f2ab`.
- Reproducible query and polygon are saved in
  `data/processed/road_network/metadata.json`.

The query uses the polygon's enclosing bounding box to avoid missing ways that
cross its boundary; local filtering then retains only segments whose endpoints
and midpoint lie in the validated polygon. General, directional, and
mode-specific `access`, `foot`, `vehicle`, `motor_vehicle`, and `motorcycle`
restrictions are applied. Restricted/end-access and unknown explicit values are
excluded from through-routing. Ways with unevaluated conditional access are
excluded conservatively. Barrier nodes are applied by mode. Vehicle oneway
direction is respected for motorbikes; ordinary vehicle oneway tags do not
restrict walking unless a specific pedestrian-direction tag says so.

## C. Supported road types

| mode      | road_type      |   directed_edges |
|:----------|:---------------|-----------------:|
| walking   | footway        |             9622 |
| walking   | living_street  |               12 |
| walking   | path           |             1028 |
| walking   | pedestrian     |              350 |
| walking   | primary        |             6426 |
| walking   | primary_link   |              992 |
| walking   | residential    |            39610 |
| walking   | secondary      |             5998 |
| walking   | secondary_link |              348 |
| walking   | service        |            65040 |
| walking   | steps          |               98 |
| walking   | tertiary       |            11162 |
| walking   | tertiary_link  |              312 |
| walking   | unclassified   |               38 |
| motorbike | living_street  |               12 |
| motorbike | primary        |             3428 |
| motorbike | primary_link   |              555 |
| motorbike | residential    |            39120 |
| motorbike | secondary      |             4388 |
| motorbike | secondary_link |              188 |
| motorbike | service        |            63767 |
| motorbike | tertiary       |             9009 |
| motorbike | tertiary_link  |              159 |
| motorbike | trunk          |                4 |
| motorbike | unclassified   |               38 |

Walking excludes motorways/trunks and honors explicit pedestrian prohibitions.
Motorbike excludes footways, paths, pedestrian ways, cycleways, and steps and
honors explicit motorcycle/motor-vehicle prohibitions. OSM tagging is incomplete,
so “allowed” means not clearly prohibited by the retained tags; it is not a
guarantee of current legal or physical access. The declared allow-list is a
conservative research profile, not a complete Vietnam legal-access model.

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
| walking-1   | walking   |          121 |            3882.4  |                    2795.33  |                   21.262 |                        88.786 |
| walking-2   | walking   |          120 |            3882.72 |                    2795.56  |                   21.262 |                        88.786 |
| walking-3   | walking   |          120 |            3883.7  |                    2796.27  |                   21.262 |                        88.786 |
| walking-4   | walking   |          119 |            3884.02 |                    2796.49  |                   21.262 |                        88.786 |
| walking-5   | walking   |          121 |            3884.21 |                    2796.63  |                   21.262 |                        88.786 |
| motorbike-1 | motorbike |          133 |            3869.32 |                     557.182 |                   21.262 |                        88.786 |
| motorbike-2 | motorbike |          130 |            3872.51 |                     557.642 |                   21.262 |                        88.786 |
| motorbike-3 | motorbike |          129 |            3877.15 |                     558.309 |                   21.262 |                        88.786 |
| motorbike-4 | motorbike |          126 |            3880.34 |                     558.769 |                   21.262 |                        88.786 |
| motorbike-5 | motorbike |          120 |            3883.7  |                     559.253 |                   21.262 |                        88.786 |

The five alternatives can differ only slightly because OSM contains parallel
carriageways and dense short vertices. They are algorithmic alternatives, not
claims of five materially distinct traveler choices.

## H. Segment-level ETA example

Departure is **2026-08-20T08:00:00+07:00**. The following rows show
the first eight and final two segments of motorbike route 1:

|   segment_index | edge_id        |   start_node |   end_node |   segment_duration_seconds |   cumulative_elapsed_seconds | target_arrival_timestamp            | estimated_arrival_timestamp         |   representative_latitude |   representative_longitude |
|----------------:|:---------------|-------------:|-----------:|---------------------------:|-----------------------------:|:------------------------------------|:------------------------------------|--------------------------:|---------------------------:|
|               1 | 242307850:0:f  |   2498079018 | 2498079021 |                   24.5108  |                      24.5108 | 2026-08-20T08:00:12.255383185+07:00 | 2026-08-20T08:00:24.510766371+07:00 |                   10.7808 |                    106.66  |
|               2 | 242307850:1:f  |   2498079021 |  366433075 |                   10.329   |                      34.8398 | 2026-08-20T08:00:29.675284872+07:00 | 2026-08-20T08:00:34.839803373+07:00 |                   10.7811 |                    106.661 |
|               3 | 1277704606:0:r |    366433075 | 1349033429 |                   12.8773  |                      47.7171 | 2026-08-20T08:00:41.278449392+07:00 | 2026-08-20T08:00:47.717095411+07:00 |                   10.7809 |                    106.661 |
|               4 | 520723335:2:r  |   1349033429 | 4415686093 |                   14.7518  |                      62.4688 | 2026-08-20T08:00:55.092971932+07:00 | 2026-08-20T08:01:02.468848453+07:00 |                   10.7812 |                    106.662 |
|               5 | 520723335:1:r  |   4415686093 | 4415547496 |                   15.0952  |                      77.564  | 2026-08-20T08:01:10.016443017+07:00 | 2026-08-20T08:01:17.564037582+07:00 |                   10.7816 |                    106.663 |
|               6 | 520723335:0:r  |   4415547496 |  366413355 |                   22.2495  |                      99.8136 | 2026-08-20T08:01:28.688800346+07:00 | 2026-08-20T08:01:39.813563110+07:00 |                   10.782  |                    106.664 |
|               7 | 32579174:7:f   |    366413355 |  366382549 |                   11.5462  |                     111.36   | 2026-08-20T08:01:45.586650188+07:00 | 2026-08-20T08:01:51.359737266+07:00 |                   10.7821 |                    106.665 |
|               8 | 32579174:8:f   |    366382549 |  366457844 |                   10.2584  |                     121.618  | 2026-08-20T08:01:56.488932993+07:00 | 2026-08-20T08:02:01.618128720+07:00 |                   10.7817 |                    106.665 |
|             132 | 327048054:16:f |   5778300433 |  411926144 |                    1.42207 |                     548.617  | 2026-08-20T08:09:07.906040021+07:00 | 2026-08-20T08:09:08.617073944+07:00 |                   10.7775 |                    106.688 |
|             133 | 327048054:17:f |    411926144 |  411926143 |                    8.5649  |                     557.182  | 2026-08-20T08:09:12.899526607+07:00 | 2026-08-20T08:09:17.181979270+07:00 |                   10.7773 |                    106.688 |

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
2. Turn-restriction relations are not yet interpreted; ways with relevant
   unevaluated conditional access are excluded rather than guessed.
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
