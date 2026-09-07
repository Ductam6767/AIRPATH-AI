import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchRoutes, fetchScenarios } from './api'
import { AssistPanel } from './components/AssistPanel'
import { MethodologyDrawer } from './components/MethodologyDrawer'
import {
  mobilityToApiMode,
  type MobilityChoice,
} from './components/ModeToggle'
import { RouteCards } from './components/RouteCards'
import { RouteMap } from './components/RouteMap'
import { Sidebar } from './components/Sidebar'
import { StatusBanner } from './components/StatusBanner'
import { isNativeApp } from './capacitor/init'
import { DELTA_MINUTES } from './constants'
import {
  type AssistMode,
  useAssistNavigation,
} from './hooks/useAssistNavigation'
import type { RouteRecord, RoutesResponse, Scenario } from './types'
import {
  destinationsForOrigin,
  findScenarioId,
  friendlyApiError,
  uniqueOrigins,
} from './utils/labels'

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [originKey, setOriginKey] = useState('')
  const [destinationKey, setDestinationKey] = useState('')
  const [mobility, setMobility] = useState<MobilityChoice>('walking')
  const mode = mobilityToApiMode(mobility)
  const [deltaMinutes, setDeltaMinutes] = useState<(typeof DELTA_MINUTES)[number]>(3)
  const [routesPayload, setRoutesPayload] = useState<RoutesResponse | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const [assistMode, setAssistMode] = useState<AssistMode>('off')
  const [initialLoading, setInitialLoading] = useState(true)
  const [loadingRoutes, setLoadingRoutes] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [methodologyOpen, setMethodologyOpen] = useState(false)
  const [nativeShell, setNativeShell] = useState(false)

  useEffect(() => {
    void isNativeApp().then(setNativeShell)
  }, [])

  const selectedScenario = useMemo(() => {
    const id = findScenarioId(scenarios, originKey, destinationKey)
    return scenarios.find((s) => s.scenario_id === id) ?? null
  }, [scenarios, originKey, destinationKey])

  const displayedRoutes: RouteRecord[] = useMemo(() => {
    if (!routesPayload) return []
    return [routesPayload.fastest_route, ...routesPayload.alternatives]
  }, [routesPayload])

  const selectedRoute = useMemo(
    () => displayedRoutes.find((r) => r.route_id === selectedRouteId) ?? null,
    [displayedRoutes, selectedRouteId],
  )

  const { snapshot: assistSnapshot, reset: resetAssist } = useAssistNavigation(
    selectedRoute,
    assistMode,
  )

  useEffect(() => {
    const controller = new AbortController()
    ;(async () => {
      setInitialLoading(true)
      setError(null)
      try {
        const payload = await fetchScenarios(controller.signal)
        const list = payload.scenarios ?? []
        setScenarios(list)
        const origins = uniqueOrigins(list)
        const firstOrigin = origins[0]
        if (firstOrigin) {
          setOriginKey(firstOrigin.key)
          const destinations = destinationsForOrigin(list, firstOrigin.key)
          const firstDest = destinations[0]
          if (firstDest) {
            setDestinationKey(firstDest.key)
          }
        }
      } catch (err) {
        if (controller.signal.aborted) return
        setError(friendlyApiError(err))
      } finally {
        if (!controller.signal.aborted) {
          setInitialLoading(false)
        }
      }
    })()
    return () => controller.abort()
  }, [])

  const loadRoutes = useCallback(async () => {
    const scenarioId = findScenarioId(scenarios, originKey, destinationKey)
    if (!scenarioId) {
      setError('That origin and destination combination is not in the demo dataset.')
      setRoutesPayload(null)
      return
    }
    setLoadingRoutes(true)
    setError(null)
    try {
      const payload = await fetchRoutes({ scenarioId, mode, deltaMinutes })
      setRoutesPayload(payload)
      setSelectedRouteId(payload.fastest_route.route_id)
      setAssistMode('off')
      resetAssist()
    } catch (err) {
      setError(friendlyApiError(err))
      setRoutesPayload(null)
      setSelectedRouteId(null)
    } finally {
      setLoadingRoutes(false)
    }
  }, [scenarios, originKey, destinationKey, mode, deltaMinutes, resetAssist])

  useEffect(() => {
    if (!selectedScenario || initialLoading) return
    void loadRoutes()
  }, [selectedScenario?.scenario_id, mode, deltaMinutes, initialLoading]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleOriginChange = (key: string) => {
    setOriginKey(key)
    const destinations = destinationsForOrigin(scenarios, key)
    const nextDest = destinations[0]
    setDestinationKey(nextDest?.key ?? '')
  }

  return (
    <div className={nativeShell ? 'app-shell app-shell--native' : 'app-shell'}>
      <a className="skip-link" href="#route-results">
        Skip to route comparison
      </a>
      <Sidebar
        scenarios={scenarios}
        originKey={originKey}
        destinationKey={destinationKey}
        mobility={mobility}
        deltaMinutes={deltaMinutes}
        loadingRoutes={loadingRoutes}
        onOriginChange={handleOriginChange}
        onDestinationChange={setDestinationKey}
        onMobilityChange={setMobility}
        onDeltaChange={(value) =>
          setDeltaMinutes(value as (typeof DELTA_MINUTES)[number])
        }
        onFindRoutes={() => {
          void loadRoutes()
        }}
        onOpenMethodology={() => setMethodologyOpen(true)}
      />

      <main className="main-panel" id="route-results">
        {initialLoading ? (
          <StatusBanner tone="loading">Loading demo scenarios…</StatusBanner>
        ) : null}

        {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}

        {!initialLoading && !error && loadingRoutes ? (
          <StatusBanner tone="loading">Loading precomputed routes…</StatusBanner>
        ) : null}

        <RouteMap
          scenario={selectedScenario}
          routes={displayedRoutes}
          selectedRouteId={selectedRouteId}
          onSelectRoute={setSelectedRouteId}
        />

        {routesPayload ? (
          <>
            <RouteCards
              fastest={routesPayload.fastest_route}
              alternatives={routesPayload.alternatives}
              selectedRouteId={selectedRouteId}
              onSelectRoute={setSelectedRouteId}
            />
            <AssistPanel
              snapshot={assistSnapshot}
              assistMode={assistMode}
              onAssistModeChange={setAssistMode}
              onReset={resetAssist}
            />
          </>
        ) : !initialLoading && !loadingRoutes && !error ? (
          <StatusBanner tone="info">
            Choose a From/To pair and press Compare routes to compare travel time
            and predicted PM2.5 exposure.
          </StatusBanner>
        ) : null}
      </main>

      <MethodologyDrawer
        open={methodologyOpen}
        onClose={() => setMethodologyOpen(false)}
      />
    </div>
  )
}
