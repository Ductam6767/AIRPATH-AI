import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  distanceToManeuver,
  extractManeuvers,
  lastPassedTurn,
  nextManeuver,
} from '../maneuver/extractManeuvers'
import { cumulativeDistances, distanceM } from '../maneuver/geo'
import { speedStepsAhead, suggestedSpeedKmh } from '../maneuver/speedProfile'
import type { AssistPayload, Maneuver } from '../maneuver/types'
import type { RouteRecord } from '../types'
import { sendAssistPayload } from '../ble/bleTransport'
import { assistPayloadTurn, isCornerConfirm } from '../maneuver/turnSignal'

export type AssistMode = 'off' | 'demo' | 'live'

export interface AssistSnapshot {
  active: boolean
  mode: AssistMode
  distanceAlongM: number
  routeLengthM: number
  next: Maneuver | null
  lastTurn: Maneuver | null
  distanceToNextM: number
  distancePastLastTurnM: number
  speedTargetKmh: number
  speedSteps: number[]
  payload: AssistPayload | null
  cornerConfirm: boolean
}

const DEMO_SPEED_MPS = 4.2 // ~15 km/h walk/demo

function buildSnapshot(
  route: RouteRecord | null,
  distanceAlongM: number,
  mode: AssistMode,
): AssistSnapshot {
  const inactive: AssistSnapshot = {
    active: false,
    mode,
    distanceAlongM: 0,
    routeLengthM: 0,
    next: null,
    lastTurn: null,
    distanceToNextM: 0,
    distancePastLastTurnM: Number.POSITIVE_INFINITY,
    speedTargetKmh: 0,
    speedSteps: [],
    payload: null,
    cornerConfirm: false,
  }
  if (!route || mode === 'off') return inactive

  const geometry = route.geometry
  if (geometry.length < 2) return inactive

  const maneuvers = extractManeuvers(geometry)
  const cum = cumulativeDistances(geometry)
  const routeLengthM = cum[cum.length - 1] ?? 0
  const clamped = Math.min(Math.max(0, distanceAlongM), routeLengthM)
  const next = nextManeuver(maneuvers, clamped)
  const lastTurn = lastPassedTurn(maneuvers, clamped)
  const distTo = next ? distanceToManeuver(next, clamped) : 0
  const distancePastLastTurnM = lastTurn
    ? clamped - lastTurn.distanceFromStartM
    : Number.POSITIVE_INFINITY
  const speedTargetKmh = next ? suggestedSpeedKmh(distTo) : 20
  const speedSteps = next ? speedStepsAhead(distTo) : []
  const turn = next?.turn ?? 'straight'
  const cornerConfirm = isCornerConfirm(
    turn,
    distTo,
    lastTurn?.turn,
    distancePastLastTurnM,
  )
  const payload: AssistPayload = {
    turn: assistPayloadTurn(turn, distTo, lastTurn?.turn, distancePastLastTurnM),
    distance_m: Math.round(distTo),
    speed_target_kmh: speedTargetKmh,
    maneuver_index: next?.index ?? 0,
    instruction: next?.instruction ?? 'Continue',
    ts: Date.now(),
    corner_confirm: cornerConfirm,
  }

  return {
    active: true,
    mode,
    distanceAlongM: clamped,
    routeLengthM,
    next,
    lastTurn,
    distanceToNextM: distTo,
    distancePastLastTurnM,
    speedTargetKmh,
    speedSteps,
    payload,
    cornerConfirm,
  }
}

export function useAssistNavigation(
  selectedRoute: RouteRecord | null,
  mode: AssistMode,
) {
  const [distanceAlongM, setDistanceAlongM] = useState(0)
  const tickRef = useRef<number | null>(null)
  const watchRef = useRef<number | null>(null)

  const snapshot = useMemo(
    () => buildSnapshot(selectedRoute, distanceAlongM, mode),
    [selectedRoute, distanceAlongM, mode],
  )

  const reset = useCallback(() => {
    setDistanceAlongM(0)
  }, [])

  // Demo playback: advance along polyline
  useEffect(() => {
    if (mode !== 'demo' || !selectedRoute) {
      if (tickRef.current) window.clearInterval(tickRef.current)
      tickRef.current = null
      return
    }
    tickRef.current = window.setInterval(() => {
      setDistanceAlongM((d) => {
        const geom = selectedRoute.geometry
        const cum = cumulativeDistances(geom)
        const max = cum[cum.length - 1] ?? 0
        const next = d + DEMO_SPEED_MPS
        return next >= max ? 0 : next
      })
    }, 1000)
    return () => {
      if (tickRef.current) window.clearInterval(tickRef.current)
    }
  }, [mode, selectedRoute])

  // Live: GPS distance to nearest polyline vertex (coarse)
  useEffect(() => {
    if (mode !== 'live' || !selectedRoute) {
      if (watchRef.current) navigator.geolocation.clearWatch(watchRef.current)
      watchRef.current = null
      return
    }
    if (!navigator.geolocation) return

    let cancelled = false
    void (async () => {
      try {
        const { Geolocation } = await import('@capacitor/geolocation')
        await Geolocation.requestPermissions()
      } catch {
        /* web / plugin missing */
      }
      if (cancelled || !navigator.geolocation) return
      watchRef.current = navigator.geolocation.watchPosition(
        (pos) => {
          const { latitude, longitude } = pos.coords
          const geom = selectedRoute.geometry
          const cum = cumulativeDistances(geom)
          let bestIdx = 0
          let bestDist = Infinity
          for (let i = 0; i < geom.length; i += 1) {
            const d = distanceM([latitude, longitude], geom[i]!)
            if (d < bestDist) {
              bestDist = d
              bestIdx = i
            }
          }
          setDistanceAlongM(cum[bestIdx] ?? 0)
        },
        () => {},
        { enableHighAccuracy: true, maximumAge: 2000, timeout: 10000 },
      )
    })()

    return () => {
      cancelled = true
      if (watchRef.current) navigator.geolocation.clearWatch(watchRef.current)
    }
  }, [mode, selectedRoute])

  useEffect(() => {
    if (mode === 'off' || !snapshot.payload) return
    void sendAssistPayload(snapshot.payload).catch(() => {})
  }, [mode, snapshot.payload])

  return { snapshot, reset, setDistanceAlongM }
}
