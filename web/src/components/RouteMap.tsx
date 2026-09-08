import { useEffect } from 'react'
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
  html: '<span aria-hidden="true">●</span>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
})

interface RouteMapProps {
  fromPlace: Coordinate | null
  toPlace: Coordinate | null
  routes: RouteRecord[]
  selectedRouteId: string | null
  onSelectRoute: (routeId: string) => void
  progressLatLng?: [number, number] | null
}

function FitRoutes({
  routes,
  fromPlace,
  toPlace,
}: {
  routes: RouteRecord[]
  fromPlace: Coordinate | null
  toPlace: Coordinate | null
}) {
  const map = useMap()
  useEffect(() => {
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
  }, [map, routes, fromPlace, toPlace])
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
}: RouteMapProps) {
  const ordered = [...routes].sort((a, b) => {
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
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitRoutes routes={routes} fromPlace={fromPlace} toPlace={toPlace} />
        {ordered.map((route) => {
          const geometry = safeGeometry(route.geometry)
          if (geometry.length < 2) return null
          const style = lineStyle(route, selectedRouteId)
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
      <div className="map-legend">
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
