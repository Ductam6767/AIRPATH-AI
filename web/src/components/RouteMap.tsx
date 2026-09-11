import { useEffect, useRef } from 'react'
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
import { COLORS } from '../constants'
import {
  angleDiffDeg,
  bearingDeg,
  lerpHeadingDeg,
  pointAlongRoute,
} from '../maneuver/geo'
import { formatCoord, routeCardTitle, safeGeometry } from '../utils/labels'
import 'leaflet/dist/leaflet.css'

const originIcon = L.divIcon({
  className: 'od-marker od-marker--origin',
  html: '<span aria-hidden="true">A</span>',
  iconSize: [28, 28],
  iconAnchor: [14, 14],
})

const destinationIcon = L.divIcon({
  className: 'od-marker od-marker--destination',
  html: '<span aria-hidden="true">B</span>',
  iconSize: [28, 28],
  iconAnchor: [14, 14],
})

const progressIcon = L.divIcon({
  className: 'od-marker od-marker--progress',
  html:
    '<span class="od-marker__pulse" aria-hidden="true"></span><span class="od-marker__chevron" aria-hidden="true"></span>',
  iconSize: [36, 36],
  iconAnchor: [18, 22],
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
      const el = map.getContainer()
      el.style.transform = ''
      el.style.transformOrigin = ''
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

    const ahead = pointAlongRoute(geometry, distanceAlongM + 48)
    if (
      ahead &&
      (Math.abs(ahead[0] - progress[0]) > 1e-7 ||
        Math.abs(ahead[1] - progress[1]) > 1e-7)
    ) {
      const raw = bearingDeg(progress, ahead)
      headingRef.current =
        headingRef.current == null
          ? raw
          : Math.abs(angleDiffDeg(headingRef.current, raw)) < 3
            ? headingRef.current
            : lerpHeadingDeg(headingRef.current, raw, 0.38)
    }

    const heading = headingRef.current ?? 0
    const el = map.getContainer()
    el.style.transformOrigin = `${originX}px ${originY}px`
    el.style.transform = `rotate(${-heading}deg) scale(1.42)`
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

function lineStyle(
  route: RouteRecord,
  selectedRouteId: string | null,
): { color: string; weight: number; opacity: number; dashArray?: string } {
  const selected = route.route_id === selectedRouteId
  if (route.is_fastest) {
    return {
      color: COLORS.sky,
      weight: selected ? 8 : 5,
      opacity: selected ? 0.96 : 0.72,
    }
  }
  if (selected) {
    return { color: COLORS.eco, weight: 8, opacity: 0.96 }
  }
  return { color: COLORS.altMuted, weight: 4, opacity: 0.5, dashArray: '7 8' }
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
    <div className="map-shell" role="region" aria-label="Route map">
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
        {ordered.map((route) => {
          const geometry = safeGeometry(route.geometry)
          if (geometry.length < 2) return null
          const style = lineStyle(route, selectedRouteId)
          if (followActive) {
            style.weight = 10
            style.opacity = 1
            style.dashArray = undefined
          }
          return (
            <Polyline
              key={route.route_id}
              positions={geometry}
              pathOptions={style}
              eventHandlers={{
                click: () => onSelectRoute(route.route_id),
              }}
            >
              <Popup>{routeCardTitle(route)}</Popup>
            </Polyline>
          )
        })}
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
      </MapContainer>
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
          <b className="od-dot od-dot--a">A</b> Origin
        </span>
        <span>
          <b className="od-dot od-dot--b">B</b> Destination
        </span>
      </div>
    </div>
  )
}
