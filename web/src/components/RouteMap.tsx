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
import type { RouteRecord, Scenario } from '../types'
import { COLORS } from '../constants'
import { safeGeometry } from '../utils/labels'
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

interface RouteMapProps {
  scenario: Scenario | null
  routes: RouteRecord[]
  selectedRouteId: string | null
  onSelectRoute: (routeId: string) => void
}

function FitRoutes({
  routes,
  scenario,
}: {
  routes: RouteRecord[]
  scenario: Scenario | null
}) {
  const map = useMap()
  useEffect(() => {
    const points: [number, number][] = []
    for (const route of routes) {
      points.push(...safeGeometry(route.geometry))
    }
    if (scenario) {
      points.push([scenario.origin.latitude, scenario.origin.longitude])
      points.push([scenario.destination.latitude, scenario.destination.longitude])
    }
    if (points.length === 0) {
      map.setView([10.78, 106.66], 12)
      return
    }
    const bounds = L.latLngBounds(points.map(([lat, lon]) => L.latLng(lat, lon)))
    map.fitBounds(bounds.pad(0.12))
  }, [map, routes, scenario])
  return null
}

function lineStyle(
  route: RouteRecord,
  selectedRouteId: string | null,
): { color: string; weight: number; opacity: number } {
  const selected = route.route_id === selectedRouteId
  if (route.is_fastest) {
    return {
      color: COLORS.sky,
      weight: selected ? 7 : 5,
      opacity: selected ? 0.95 : 0.75,
    }
  }
  if (selected) {
    return { color: COLORS.eco, weight: 7, opacity: 0.95 }
  }
  return { color: COLORS.altMuted, weight: 4, opacity: 0.55 }
}

export function RouteMap({
  scenario,
  routes,
  selectedRouteId,
  onSelectRoute,
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
        {/* Carto Positron — public demo tiles, no API key */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <FitRoutes routes={routes} scenario={scenario} />
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
            />
          )
        })}
        {scenario ? (
          <>
            <Marker
              position={[scenario.origin.latitude, scenario.origin.longitude]}
              icon={originIcon}
            >
              <Popup>Origin · {scenario.origin.label}</Popup>
            </Marker>
            <Marker
              position={[
                scenario.destination.latitude,
                scenario.destination.longitude,
              ]}
              icon={destinationIcon}
            >
              <Popup>Destination · {scenario.destination.label}</Popup>
            </Marker>
          </>
        ) : null}
      </MapContainer>
      <div className="map-legend" aria-hidden="true">
        <span>
          <i style={{ background: COLORS.sky }} /> Fastest
        </span>
        <span>
          <i style={{ background: COLORS.eco }} /> Selected alternative
        </span>
        <span>
          <i style={{ background: COLORS.altMuted }} /> Other alternatives
        </span>
      </div>
    </div>
  )
}
