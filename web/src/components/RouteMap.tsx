import { Fragment, useEffect, useRef, useState } from 'react'
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  useMap,
} from 'react-leaflet'
import L from 'leaflet'
import type { Coordinate, RouteRecord } from '../types'
import {
  angleDiffDeg,
  bearingDeg,
  headingAlongRoute,
  lerpHeadingDeg,
  pointAlongRoute,
} from '../maneuver/geo'
import {
  isBridgeIconVisible,
  isCueEmphasized,
  isMapDiagramVisible,
  remainingToCue,
  type PlacedCue,
} from '../maneuver/guidanceCues'
import { guidanceDiagramInner } from '../maneuver/guidanceDiagramSvg'
import { formatCoord, routeCardTitle, safeGeometry } from '../utils/labels'
import { FOLLOW_MAP_SCALE, routeLinePaint } from '../utils/routeLinePaint'
import 'leaflet/dist/leaflet.css'

const originIcon = L.divIcon({
  className: 'od-gmaps-wrap',
  html: '<span class="od-gmaps-start" aria-hidden="true"></span>',
  iconSize: [12, 12],
  iconAnchor: [6, 6],
})

const destinationIcon = L.divIcon({
  className: 'od-gmaps-wrap',
  html:
    '<svg class="od-gmaps-pin" viewBox="0 0 24 36" width="14" height="21" aria-hidden="true"><path fill="#EA4335" stroke="#fff" stroke-width="1.7" d="M12 1.6C6.8 1.6 2.6 5.8 2.6 11c0 7.1 9.4 23 9.4 23s9.4-15.9 9.4-23C21.4 5.8 17.2 1.6 12 1.6z"/><circle cx="12" cy="11" r="3.4" fill="#fff"/></svg>',
  iconSize: [14, 21],
  iconAnchor: [7, 20],
})

const progressIcon = L.divIcon({
  className: 'od-marker od-marker--progress',
  html:
    '<span class="od-marker__pulse" aria-hidden="true"></span><span class="od-marker__chevron" aria-hidden="true"></span>',
  iconSize: [12, 12],
  iconAnchor: [6, 8],
})

interface RouteMapProps {
  fromPlace: Coordinate | null
  toPlace: Coordinate | null
  routes: RouteRecord[]
  selectedRouteId: string | null
  onSelectRoute: (routeId: string) => void
  progressLatLng?: [number, number] | null
  followActive?: boolean
  followGeometry?: [number, number][]
  distanceAlongM?: number
  guidanceCues?: PlacedCue[]
}

function FitRoutes({
  routes,
  fromPlace,
  toPlace,
  disabled = false,
}: {
  routes: RouteRecord[]
  fromPlace: Coordinate | null
  toPlace: Coordinate | null
  disabled?: boolean
}) {
  const map = useMap()
  useEffect(() => {
    if (disabled) return
    const fit = () => {
      map.invalidateSize({ animate: false })
      const points: [number, number][] = []
      for (const route of routes) {
        points.push(...safeGeometry(route.geometry))
      }
      if (fromPlace) {
        points.push([fromPlace.latitude, fromPlace.longitude])
      }
      if (toPlace) {
        points.push([toPlace.latitude, toPlace.longitude])
      }
      if (points.length === 0) {
        map.setView([10.78, 106.66], 12)
        return
      }
      const bounds = L.latLngBounds(points.map(([lat, lon]) => L.latLng(lat, lon)))
      map.fitBounds(bounds.pad(0.12), { animate: false, maxZoom: 16 })
    }
    fit()
    const frame = window.requestAnimationFrame(fit)
    const observer = new ResizeObserver(() => fit())
    observer.observe(map.getContainer())
    return () => {
      window.cancelAnimationFrame(frame)
      observer.disconnect()
    }
  }, [map, routes, fromPlace, toPlace, disabled])
  return null
}

const FOLLOW_ZOOM = 16

function followTargetY(size: L.Point): number {
  const phone = size.x <= 480
  if (!phone) return size.y * 0.5
  const sheet = Math.min(size.y * 0.42, 360)
  const visible = Math.max(140, size.y - sheet)
  return visible * 0.55
}

function FollowProgress({
  progress,
  geometry,
  distanceAlongM,
}: {
  progress: [number, number]
  geometry: [number, number][]
  distanceAlongM: number
}) {
  const map = useMap()
  const sized = useRef(false)
  const headingRef = useRef<number | null>(null)

  useEffect(() => {
    map.invalidateSize({ animate: false })
    sized.current = true
    return () => {
      const world = map.getContainer().closest('.map-rotate-world')
      if (world instanceof HTMLElement) {
        world.style.transform = ''
        world.style.transformOrigin = ''
      }
      headingRef.current = null
    }
  }, [map])

  useEffect(() => {
    const size = map.getSize()
    if (size.x < 40 || size.y < 40) return
    if (!sized.current) {
      map.invalidateSize({ animate: false })
      sized.current = true
    }

    const here = L.latLng(progress[0], progress[1])
    if (map.getZoom() !== FOLLOW_ZOOM) {
      map.setView(here, FOLLOW_ZOOM, { animate: false })
    } else {
      map.panTo(here, { animate: false, noMoveStart: true })
    }

    const originX = size.x / 2
    const originY = followTargetY(size)
    const now = map.latLngToContainerPoint(here)
    const want = L.point(originX, originY)
    const dx = now.x - want.x
    const dy = now.y - want.y
    if (Math.abs(dx) > 1 || Math.abs(dy) > 1) {
      map.panBy([dx, dy], { animate: false, noMoveStart: true })
    }

    const ahead = pointAlongRoute(geometry, distanceAlongM + 55)
    if (
      ahead &&
      (Math.abs(ahead[0] - progress[0]) > 1e-7 ||
        Math.abs(ahead[1] - progress[1]) > 1e-7)
    ) {
      const raw = bearingDeg(progress, ahead)
      headingRef.current =
        headingRef.current == null
          ? raw
          : Math.abs(angleDiffDeg(headingRef.current, raw)) < 2.5
            ? headingRef.current
            : lerpHeadingDeg(headingRef.current, raw, 0.42)
    }

    const heading = headingRef.current ?? 0
    const world = map.getContainer().closest('.map-rotate-world')
    if (world instanceof HTMLElement) {
      world.style.transformOrigin = `${originX}px ${originY}px`
      world.style.transform = `rotate(${-heading}deg) scale(${FOLLOW_MAP_SCALE})`
    }
  }, [map, progress, geometry, distanceAlongM])

  return null
}

function LockMapInteraction({ locked }: { locked: boolean }) {
  const map = useMap()
  useEffect(() => {
    if (locked) {
      map.dragging.disable()
      map.touchZoom.disable()
      map.scrollWheelZoom.disable()
      map.doubleClickZoom.disable()
      map.boxZoom.disable()
      map.keyboard.disable()
    } else {
      map.dragging.enable()
      map.touchZoom.enable()
      map.scrollWheelZoom.enable()
      map.doubleClickZoom.enable()
      map.boxZoom.enable()
      map.keyboard.enable()
    }
  }, [map, locked])
  return null
}

const BRIDGE_PIN_SVG =
  '<svg class="guidance-bridge-pin" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="#0f172a" d="M3 17.5V14c0-4.2 4-6.5 9-6.5s9 2.3 9 6.5v3.5h-2V14c0-2.8-3.1-4.5-7-4.5s-7 1.7-7 4.5v3.5H3z"/><path fill="none" stroke="#f8fafc" stroke-width="1.6" d="M4 18.2h16"/><path fill="none" stroke="#0f766e" stroke-width="1.8" d="M6 18.2V15.4c0-2 2.7-3.2 6-3.2s6 1.2 6 3.2v2.8"/></svg>'

function cueMapIcon(
  cue: PlacedCue,
  heading: number,
  emphasized: boolean,
  variant: 'diagram' | 'bridge-icon',
): L.DivIcon {
  const size = variant === 'diagram' ? (emphasized ? 72 : 58) : 26
  const scale =
    (1 / FOLLOW_MAP_SCALE) * (emphasized && variant === 'diagram' ? 1.1 : 1)
  const inner =
    variant === 'bridge-icon'
      ? BRIDGE_PIN_SVG
      : `<svg viewBox="0 0 120 120" width="${size}" height="${size}" aria-hidden="true">${guidanceDiagramInner(cue, emphasized)}</svg>`
  return L.divIcon({
    className: 'guidance-map-wrap',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div class="guidance-map-pin${emphasized ? ' is-active' : ''}${variant === 'bridge-icon' ? ' guidance-map-pin--bridge' : ''}" style="transform:rotate(${heading}deg) scale(${scale})">${inner}</div>`,
  })
}

function GuidanceOverlays({
  cues,
  geometry,
  distanceAlongM,
}: {
  cues: PlacedCue[]
  geometry: [number, number][]
  distanceAlongM: number
}) {
  const heading = headingAlongRoute(geometry, distanceAlongM)
  const headingKey = Math.round(heading / 2) * 2
  return (
    <>
      {cues.map((cue) => {
        const remaining = remainingToCue(cue.atM, distanceAlongM)
        const showDiagram = isMapDiagramVisible(cue.kind, remaining)
        const showBridge =
          cue.kind === 'bridge' &&
          !showDiagram &&
          isBridgeIconVisible(remaining)
        if (!showDiagram && !showBridge) return null
        const emphasized = isCueEmphasized(cue.kind, remaining)
        const variant = showDiagram ? 'diagram' : 'bridge-icon'
        const pos = pointAlongRoute(geometry, cue.atM) ?? [cue.lat, cue.lng]
        return (
          <Marker
            key={`${cue.id}-${variant}-${headingKey}-${emphasized ? 'on' : 'off'}`}
            position={pos}
            icon={cueMapIcon(cue, heading, emphasized, variant)}
            interactive={false}
            zIndexOffset={showDiagram ? 700 : 500}
          />
        )
      })}
    </>
  )
}

function useMapZoom(): number {
  const map = useMap()
  const [zoom, setZoom] = useState(() => map.getZoom())
  useEffect(() => {
    const sync = () => setZoom(map.getZoom())
    map.on('zoomend', sync)
    sync()
    return () => {
      map.off('zoomend', sync)
    }
  }, [map])
  return zoom
}

function RoutePolylines({
  routes,
  selectedRouteId,
  onSelectRoute,
  followActive,
}: {
  routes: RouteRecord[]
  selectedRouteId: string | null
  onSelectRoute: (routeId: string) => void
  followActive: boolean
}) {
  const zoom = useMapZoom()
  return (
    <>
      {routes.map((route) => {
        const geometry = safeGeometry(route.geometry)
        if (geometry.length < 2) return null
        const paint = routeLinePaint(route, selectedRouteId, followActive, zoom)
        return (
          <Fragment key={route.route_id}>
            <Polyline
              positions={geometry}
              pathOptions={paint.casing}
              eventHandlers={{
                click: () => onSelectRoute(route.route_id),
              }}
            />
            <Polyline
              positions={geometry}
              pathOptions={paint.fill}
              eventHandlers={{
                click: () => onSelectRoute(route.route_id),
              }}
            >
              <Popup>{routeCardTitle(route)}</Popup>
            </Polyline>
          </Fragment>
        )
      })}
    </>
  )
}

export function RouteMap({
  fromPlace,
  toPlace,
  routes,
  selectedRouteId,
  onSelectRoute,
  progressLatLng,
  followActive = false,
  followGeometry = [],
  distanceAlongM = 0,
  guidanceCues = [],
}: RouteMapProps) {
  const visibleRoutes = followActive
    ? routes.filter((route) => route.route_id === selectedRouteId)
    : routes
  const ordered = [...visibleRoutes].sort((a, b) => {
    const aSel = a.route_id === selectedRouteId ? 1 : 0
    const bSel = b.route_id === selectedRouteId ? 1 : 0
    return aSel - bSel
  })

  return (
    <div
      className={`map-shell${followActive ? ' map-shell--follow' : ''}`}
      role="region"
      aria-label="Route map"
    >
      <div className="map-rotate-clip">
        <div className="map-rotate-world">
          <MapContainer
            center={[10.78, 106.66]}
            zoom={12}
            className="route-map"
            scrollWheelZoom
            zoomControl
          >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
          maxNativeZoom={19}
          minZoom={11}
          keepBuffer={6}
          updateWhenZooming={false}
        />
        <LockMapInteraction locked={followActive} />
        <FitRoutes
          routes={routes}
          fromPlace={fromPlace}
          toPlace={toPlace}
          disabled={followActive}
        />
        {followActive && progressLatLng ? (
          <FollowProgress
            progress={progressLatLng}
            geometry={followGeometry}
            distanceAlongM={distanceAlongM}
          />
        ) : null}
        <RoutePolylines
          routes={ordered}
          selectedRouteId={selectedRouteId}
          onSelectRoute={onSelectRoute}
          followActive={followActive}
        />
        {fromPlace ? (
          <Marker
            position={[fromPlace.latitude, fromPlace.longitude]}
            icon={originIcon}
          >
            <Popup>
              <strong>{fromPlace.label}</strong>
              <br />
              <span className="muted">
                {formatCoord(fromPlace.latitude, fromPlace.longitude)}
              </span>
            </Popup>
          </Marker>
        ) : null}
        {toPlace ? (
          <Marker
            position={[toPlace.latitude, toPlace.longitude]}
            icon={destinationIcon}
          >
            <Popup>
              <strong>{toPlace.label}</strong>
              <br />
              <span className="muted">
                {formatCoord(toPlace.latitude, toPlace.longitude)}
              </span>
            </Popup>
          </Marker>
        ) : null}
        {progressLatLng ? (
          <Marker position={progressLatLng} icon={progressIcon}>
            <Popup>Demo / GPS progress</Popup>
          </Marker>
        ) : null}
        {followActive && guidanceCues.length > 0 ? (
          <GuidanceOverlays
            cues={guidanceCues}
            geometry={followGeometry}
            distanceAlongM={distanceAlongM}
          />
        ) : null}
          </MapContainer>
        </div>
      </div>
      <div className={`map-legend${followActive ? ' map-legend--hidden' : ''}`}>
        <span>
          <i className="swatch swatch--fastest" /> Fastest
        </span>
        <span>
          <i className="swatch swatch--selected" /> Selected alternative
        </span>
        <span>
          <i className="swatch swatch--other" /> Other alternatives
        </span>
        <span>
          <i className="od-gmaps-start od-gmaps-start--legend" /> Origin
        </span>
        <span>
          <svg
            className="od-gmaps-pin od-gmaps-pin--legend"
            viewBox="0 0 24 36"
            aria-hidden="true"
          >
            <path
              fill="#EA4335"
              stroke="#fff"
              strokeWidth="1.7"
              d="M12 1.6C6.8 1.6 2.6 5.8 2.6 11c0 7.1 9.4 23 9.4 23s9.4-15.9 9.4-23C21.4 5.8 17.2 1.6 12 1.6z"
            />
            <circle cx="12" cy="11" r="3.4" fill="#fff" />
          </svg>{' '}
          Destination
        </span>
      </div>
    </div>
  )
}
