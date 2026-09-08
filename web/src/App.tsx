import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  fetchGap1Exhibit,
  fetchRoutes,
  fetchScenarios,
  getDemoDataSource,
} from './api'
import { AssistPanel } from './components/AssistPanel'
import { Gap1Research } from './components/Gap1Research'
import { MethodologyDrawer } from './components/MethodologyDrawer'
import {
  mobilityToApiMode,
  type MobilityChoice,
} from './components/ModeToggle'
import { OnboardingCard, shouldShowOnboarding } from './components/OnboardingCard'
import { RouteCards } from './components/RouteCards'
import { RouteMap } from './components/RouteMap'
import { Sidebar } from './components/Sidebar'
import { StatusBanner } from './components/StatusBanner'
import { TrialLogPanel } from './components/TrialLogPanel'
import { isNativeApp } from './capacitor/init'
import { DELTA_MINUTES, IS_MOBILE_BUILD } from './constants'
import { LanguageProvider, useI18n } from './i18n/LanguageContext'
import {
  type AssistMode,
  useAssistNavigation,
} from './hooks/useAssistNavigation'
import { pointAlongRoute } from './maneuver/geo'
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

function AppInner() {
  const { t } = useI18n()
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [originKey, setOriginKey] = useState('')
  const [destinationKey, setDestinationKey] = useState('')
  const [mode, setMode] = useState<TravelMode>(IS_MOBILE_BUILD ? 'walking' : 'motorbike')
  const [mobility, setMobility] = useState<MobilityChoice>('walking')
  const [timeWindow, setTimeWindow] = useState<TimeWindow>('morning_peak')
  const [deltaMinutes, setDeltaMinutes] = useState<(typeof DELTA_MINUTES)[number]>(
    IS_MOBILE_BUILD ? 3 : 5,
  )
  const apiMode: TravelMode = IS_MOBILE_BUILD ? mobilityToApiMode(mobility) : mode
  const [routesPayload, setRoutesPayload] = useState<RoutesResponse | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const [assistMode, setAssistMode] = useState<AssistMode>('off')
  const [initialLoading, setInitialLoading] = useState(true)
  const [loadingRoutes, setLoadingRoutes] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [methodologyOpen, setMethodologyOpen] = useState(false)
  const [nativeShell, setNativeShell] = useState(false)
  const [dataSource, setDataSource] = useState<'api' | 'bundled'>('api')
  const [view, setView] = useState<'demo' | 'gap1'>('demo')
  const [gap1Exhibit, setGap1Exhibit] = useState<Gap1Exhibit | null>(null)
  const [gap1Loading, setGap1Loading] = useState(false)
  const [gap1Error, setGap1Error] = useState<string | null>(null)
  const [onboardOpen, setOnboardOpen] = useState(
    () =>
      IS_MOBILE_BUILD &&
      import.meta.env.MODE !== 'test' &&
      shouldShowOnboarding(),
  )

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

  const progressLatLng = useMemo(() => {
    if (assistMode === 'off' || !selectedRoute) return null
    return pointAlongRoute(selectedRoute.geometry, assistSnapshot.distanceAlongM)
  }, [assistMode, selectedRoute, assistSnapshot.distanceAlongM])

  useEffect(() => {
    const controller = new AbortController()
    ;(async () => {
      setInitialLoading(true)
      setError(null)
      try {
        const payload = await fetchScenarios(controller.signal)
        const list = payload.scenarios ?? []
        setScenarios(list)
        setDataSource(getDemoDataSource())
        const opening = list.find((scenario) => scenario.opening_example) ?? list[0]
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
      const payload = await fetchRoutes({
        scenarioId,
        mode: apiMode,
        deltaMinutes,
        timeWindow,
      })
      setRoutesPayload(payload)
      setDataSource(getDemoDataSource())
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
  }, [
    scenarios,
    originKey,
    destinationKey,
    apiMode,
    deltaMinutes,
    timeWindow,
    resetAssist,
  ])

  useEffect(() => {
    if (!selectedScenario || initialLoading) return
    void loadRoutes()
  }, [
    selectedScenario?.scenario_id,
    apiMode,
    deltaMinutes,
    timeWindow,
    initialLoading,
  ]) // eslint-disable-line react-hooks/exhaustive-deps

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
    <div className={nativeShell ? 'app-shell app-shell--native' : 'app-shell'}>
      <a className="skip-link" href="#route-results">
        {t.skipToRoutes}
      </a>
      <Sidebar
        scenarios={scenarios}
        originKey={originKey}
        destinationKey={destinationKey}
        mode={mode}
        mobility={mobility}
        timeWindow={timeWindow}
        deltaMinutes={deltaMinutes}
        loadingRoutes={loadingRoutes}
        onOriginChange={handleOriginChange}
        onDestinationChange={setDestinationKey}
        onModeChange={setMode}
        onMobilityChange={setMobility}
        onTimeWindowChange={setTimeWindow}
        onDeltaChange={(value) =>
          setDeltaMinutes(value as (typeof DELTA_MINUTES)[number])
        }
        onFindRoutes={() => {
          void loadRoutes()
        }}
        onOpenMethodology={() => setMethodologyOpen(true)}
        onOpenGap1={IS_MOBILE_BUILD ? undefined : () => void openGap1()}
      />

      <main className="main-panel" id="route-results">
        {!IS_MOBILE_BUILD && view === 'gap1' ? (
          <>
            {gap1Loading ? (
              <StatusBanner tone="loading">{t.gap1Loading}</StatusBanner>
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
              <StatusBanner tone="info">{t.gap1Empty}</StatusBanner>
            ) : null}
          </>
        ) : (
          <>
            {initialLoading ? (
              <StatusBanner tone="loading">{t.loadingScenarios}</StatusBanner>
            ) : null}

            {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}

            {IS_MOBILE_BUILD && !initialLoading && !error && dataSource === 'bundled' ? (
              <StatusBanner tone="info">{t.bundledNote}</StatusBanner>
            ) : null}

            {!initialLoading && !error && loadingRoutes ? (
              <StatusBanner tone="loading">{t.loadingRoutes}</StatusBanner>
            ) : null}

            <RouteMap
              scenario={selectedScenario}
              routes={displayedRoutes}
              selectedRouteId={selectedRouteId}
              onSelectRoute={setSelectedRouteId}
              progressLatLng={IS_MOBILE_BUILD ? progressLatLng : null}
            />

            {routesPayload ? (
              <>
                <RouteCards
                  fastest={routesPayload.fastest_route}
                  alternatives={routesPayload.alternatives}
                  selectedRouteId={selectedRouteId}
                  onSelectRoute={setSelectedRouteId}
                />
                {IS_MOBILE_BUILD ? (
                  <>
                    <AssistPanel
                      snapshot={assistSnapshot}
                      assistMode={assistMode}
                      onAssistModeChange={setAssistMode}
                      onReset={resetAssist}
                    />
                    <TrialLogPanel />
                  </>
                ) : null}
              </>
            ) : !initialLoading && !loadingRoutes && !error ? (
              <StatusBanner tone="info">{t.choosePair}</StatusBanner>
            ) : null}
          </>
        )}
      </main>

      <MethodologyDrawer
        open={methodologyOpen}
        onClose={() => setMethodologyOpen(false)}
      />
      {IS_MOBILE_BUILD ? (
        <OnboardingCard open={onboardOpen} onClose={() => setOnboardOpen(false)} />
      ) : null}
    </div>
  )
}

export default function App() {
  return (
    <LanguageProvider>
      <AppInner />
    </LanguageProvider>
  )
}
