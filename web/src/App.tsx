import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchGap1Exhibit, fetchRoutes, fetchScenarios } from './api'
import { DELTA_MINUTES } from './constants'
import { Gap1Research } from './components/Gap1Research'
import { MethodologyDrawer } from './components/MethodologyDrawer'
import { RouteCards } from './components/RouteCards'
import { RouteMap } from './components/RouteMap'
import { Sidebar } from './components/Sidebar'
import { StatusBanner } from './components/StatusBanner'
import type {
  Gap1Exhibit,
  RouteRecord,
  RoutesResponse,
  Scenario,
  TimeWindow,
  TravelMode,
} from './types'
import {
  destinationsForOrigin,
  findScenarioId,
  friendlyApiError,
  scenarioDestKey,
  scenarioOriginKey,
} from './utils/labels'

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [originKey, setOriginKey] = useState('')
  const [destinationKey, setDestinationKey] = useState('')
  const [mode, setMode] = useState<TravelMode>('motorbike')
  const [timeWindow, setTimeWindow] = useState<TimeWindow>('morning_peak')
  const [deltaMinutes, setDeltaMinutes] = useState<(typeof DELTA_MINUTES)[number]>(5)
  const [routesPayload, setRoutesPayload] = useState<RoutesResponse | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const [initialLoading, setInitialLoading] = useState(true)
  const [loadingRoutes, setLoadingRoutes] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [methodologyOpen, setMethodologyOpen] = useState(false)
  const [view, setView] = useState<'demo' | 'gap1'>('demo')
  const [gap1Exhibit, setGap1Exhibit] = useState<Gap1Exhibit | null>(null)
  const [gap1Loading, setGap1Loading] = useState(false)
  const [gap1Error, setGap1Error] = useState<string | null>(null)

  const selectedScenario = useMemo(() => {
    const id = findScenarioId(scenarios, originKey, destinationKey)
    return scenarios.find((s) => s.scenario_id === id) ?? null
  }, [scenarios, originKey, destinationKey])

  const displayedRoutes: RouteRecord[] = useMemo(() => {
    if (!routesPayload) return []
    return [routesPayload.fastest_route, ...routesPayload.alternatives]
  }, [routesPayload])

  useEffect(() => {
    const controller = new AbortController()
    ;(async () => {
      setInitialLoading(true)
      setError(null)
      try {
        const payload = await fetchScenarios(controller.signal)
        const list = payload.scenarios ?? []
        setScenarios(list)
        const opening =
          list.find((scenario) => scenario.opening_example) ?? list[0]
        if (opening) {
          setOriginKey(scenarioOriginKey(opening))
          setDestinationKey(scenarioDestKey(opening))
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
      const payload = await fetchRoutes({ scenarioId, mode, deltaMinutes, timeWindow })
      setRoutesPayload(payload)
      setSelectedRouteId(payload.fastest_route.route_id)
    } catch (err) {
      setError(friendlyApiError(err))
      setRoutesPayload(null)
      setSelectedRouteId(null)
    } finally {
      setLoadingRoutes(false)
    }
  }, [scenarios, originKey, destinationKey, mode, deltaMinutes, timeWindow])

  useEffect(() => {
    if (!selectedScenario || initialLoading) return
    void loadRoutes()
  }, [selectedScenario?.scenario_id, mode, deltaMinutes, timeWindow, initialLoading]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleOriginChange = (key: string) => {
    setOriginKey(key)
    const destinations = destinationsForOrigin(scenarios, key)
    const nextDest = destinations[0]
    setDestinationKey(nextDest?.key ?? '')
  }

  const openGap1 = useCallback(async () => {
    setView('gap1')
    if (gap1Exhibit || gap1Loading) return
    setGap1Loading(true)
    setGap1Error(null)
    try {
      const payload = await fetchGap1Exhibit()
      setGap1Exhibit(payload)
    } catch (err) {
      setGap1Error(friendlyApiError(err))
    } finally {
      setGap1Loading(false)
    }
  }, [gap1Exhibit, gap1Loading])

  return (
    <div className="app-shell">
      <a className="skip-link" href="#route-results">
        Skip to route comparison
      </a>
      <Sidebar
        scenarios={scenarios}
        originKey={originKey}
        destinationKey={destinationKey}
        mode={mode}
        timeWindow={timeWindow}
        deltaMinutes={deltaMinutes}
        loadingRoutes={loadingRoutes}
        onOriginChange={handleOriginChange}
        onDestinationChange={setDestinationKey}
        onModeChange={setMode}
        onTimeWindowChange={setTimeWindow}
        onDeltaChange={(value) =>
          setDeltaMinutes(value as (typeof DELTA_MINUTES)[number])
        }
        onFindRoutes={() => {
          void loadRoutes()
        }}
        onOpenMethodology={() => setMethodologyOpen(true)}
        onOpenGap1={() => {
          void openGap1()
        }}
      />

      <main className="main-panel" id="route-results">
        {view === 'gap1' ? (
          <>
            {gap1Loading ? (
              <StatusBanner tone="loading">Loading Gap 1 exhibit…</StatusBanner>
            ) : null}
            {gap1Error ? <StatusBanner tone="error">{gap1Error}</StatusBanner> : null}
            {gap1Exhibit ? (
              <Gap1Research
                exhibit={gap1Exhibit}
                onBack={() => {
                  setView('demo')
                  setGap1Error(null)
                }}
              />
            ) : !gap1Loading && !gap1Error ? (
              <StatusBanner tone="info">
                Gap 1 exhibit is not loaded yet.
              </StatusBanner>
            ) : null}
          </>
        ) : (
          <>
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
              <RouteCards
                fastest={routesPayload.fastest_route}
                alternatives={routesPayload.alternatives}
                selectedRouteId={selectedRouteId}
                onSelectRoute={setSelectedRouteId}
              />
            ) : !initialLoading && !loadingRoutes && !error ? (
              <StatusBanner tone="info">
                Choose a From/To pair and press Compare routes to compare travel time
                and predicted PM2.5 exposure.
              </StatusBanner>
            ) : null}
          </>
        )}
      </main>

      <MethodologyDrawer
        open={methodologyOpen}
        onClose={() => setMethodologyOpen(false)}
      />
    </div>
  )
}
