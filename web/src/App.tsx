import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  fetchGap1Exhibit,
  fetchRoutes,
  fetchScenarios,
  getDemoDataSource,
} from './api'
import { AIAnalysis } from './components/AIAnalysis'
import { AssistPanel } from './components/AssistPanel'
import { BottomSheet } from './components/BottomSheet'
import { Gap1Research } from './components/Gap1Research'
import { MethodologyDrawer } from './components/MethodologyDrawer'
import {
  mobilityToApiMode,
  type MobilityChoice,
} from './components/ModeToggle'
import { NavigationInstruction } from './components/NavigationInstruction'
import { OnboardingCard, shouldShowOnboarding } from './components/OnboardingCard'
import { RouteCards } from './components/RouteCards'
import { RouteMap } from './components/RouteMap'
import { SearchBar } from './components/SearchBar'
import { StatusBanner } from './components/StatusBanner'
import { TopBar } from './components/TopBar'
import { TrialLogPanel } from './components/TrialLogPanel'
import { TurnSignalStatus } from './components/TurnSignalStatus'
import { WhyThisRoute } from './components/WhyThisRoute'
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
  friendlyApiError,
  lookupPlace,
  parsePlaceKey,
  pickRecommendedRoute,
  scenarioForRequestedEnds,
} from './utils/labels'

type AppFlow = 'plan' | 'compare' | 'navigate' | 'gap1'

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
  const [flow, setFlow] = useState<AppFlow>('plan')
  const [gap1Exhibit, setGap1Exhibit] = useState<Gap1Exhibit | null>(null)
  const [gap1Loading, setGap1Loading] = useState(false)
  const [gap1Error, setGap1Error] = useState<string | null>(null)
  const [labOpen, setLabOpen] = useState(false)
  const [onboardOpen, setOnboardOpen] = useState(
    () =>
      IS_MOBILE_BUILD &&
      import.meta.env.MODE !== 'test' &&
      shouldShowOnboarding(),
  )

  useEffect(() => {
    void isNativeApp().then(setNativeShell)
  }, [])

  const selectedScenario = useMemo(
    () => scenarioForRequestedEnds(scenarios, originKey, destinationKey),
    [scenarios, originKey, destinationKey],
  )
  const fromPlace = useMemo(
    () => lookupPlace(scenarios, originKey),
    [scenarios, originKey],
  )
  const toPlace = useMemo(
    () => lookupPlace(scenarios, destinationKey),
    [scenarios, destinationKey],
  )

  const displayedRoutes: RouteRecord[] = useMemo(() => {
    if (!routesPayload) return []
    return [routesPayload.fastest_route, ...routesPayload.alternatives]
  }, [routesPayload])

  const recommended = useMemo(() => {
    if (!routesPayload) return null
    return pickRecommendedRoute(
      routesPayload.fastest_route,
      routesPayload.alternatives,
    )
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
    const from = parsePlaceKey(originKey)
    const to = parsePlaceKey(destinationKey)
    if (!from || !to || !selectedScenario) {
      setRoutesPayload(null)
      setSelectedRouteId(null)
      return
    }
    setLoadingRoutes(true)
    setError(null)
    try {
      const payload = await fetchRoutes({
        scenarioId: selectedScenario.scenario_id,
        fromLatitude: from.latitude,
        fromLongitude: from.longitude,
        toLatitude: to.latitude,
        toLongitude: to.longitude,
        mode: apiMode,
        deltaMinutes,
        timeWindow,
      })
      setRoutesPayload(payload)
      setDataSource(getDemoDataSource())
      const next = pickRecommendedRoute(payload.fastest_route, payload.alternatives)
      setSelectedRouteId(next.route_id)
      setAssistMode('off')
      resetAssist()
      setFlow((current) => (current === 'navigate' ? current : 'compare'))
    } catch (err) {
      setError(friendlyApiError(err))
      setRoutesPayload(null)
      setSelectedRouteId(null)
    } finally {
      setLoadingRoutes(false)
    }
  }, [
    originKey,
    destinationKey,
    selectedScenario,
    apiMode,
    deltaMinutes,
    timeWindow,
    resetAssist,
  ])

  useEffect(() => {
    if (initialLoading) return
    if (!selectedScenario) {
      setRoutesPayload(null)
      setSelectedRouteId(null)
      return
    }
    void loadRoutes()
  }, [
    selectedScenario?.scenario_id,
    originKey,
    destinationKey,
    apiMode,
    deltaMinutes,
    timeWindow,
    initialLoading,
  ]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleOriginChange = (key: string) => {
    setOriginKey(key)
    if (key && key === destinationKey) {
      setDestinationKey('')
    }
    setError(null)
    setFlow('plan')
  }

  const handleDestinationChange = (key: string) => {
    setDestinationKey(key)
    if (key && key === originKey) {
      setOriginKey('')
    }
    setError(null)
    setFlow('plan')
  }

  const handleSwapEnds = () => {
    setOriginKey(destinationKey)
    setDestinationKey(originKey)
    setError(null)
    setFlow('plan')
  }

  const openGap1 = useCallback(async () => {
    setFlow('gap1')
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

  const startNavigation = () => {
    if (!selectedRoute) return
    setFlow('navigate')
    setAssistMode('demo')
  }

  const endNavigation = () => {
    setFlow('compare')
    setAssistMode('off')
    resetAssist()
  }

  const sheetVariant =
    flow === 'navigate' ? 'nav' : flow === 'compare' ? 'expanded' : 'peek'
  const navigating = flow === 'navigate'

  return (
    <div
      className={[
        'app-shell',
        nativeShell ? 'app-shell--native' : '',
        navigating ? 'app-shell--nav' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <a className="skip-link" href="#route-results">
        {t.skipToRoutes}
      </a>

      {flow === 'gap1' ? (
        <main className="research-panel">
          <TopBar onOpenMore={() => setMethodologyOpen(true)} />
          {gap1Loading ? (
            <StatusBanner tone="loading">{t.gap1Loading}</StatusBanner>
          ) : null}
          {gap1Error ? <StatusBanner tone="error">{gap1Error}</StatusBanner> : null}
          {gap1Exhibit ? (
            <Gap1Research
              exhibit={gap1Exhibit}
              onBack={() => {
                setFlow('compare')
                setGap1Error(null)
              }}
            />
          ) : !gap1Loading && !gap1Error ? (
            <StatusBanner tone="info">{t.gap1Empty}</StatusBanner>
          ) : null}
        </main>
      ) : (
        <>
          {navigating ? null : (
            <TopBar
              onOpenMore={() => {
                setMethodologyOpen(true)
              }}
            />
          )}

          <main className="map-stage" id="route-results">
            {initialLoading ? (
              <StatusBanner tone="loading">{t.loadingScenarios}</StatusBanner>
            ) : null}
            {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}
            {!initialLoading && !error && dataSource === 'bundled' ? (
              <StatusBanner tone="info">{t.bundledNote}</StatusBanner>
            ) : null}
            {!initialLoading && !error && loadingRoutes ? (
              <StatusBanner tone="loading">{t.loadingRoutes}</StatusBanner>
            ) : null}

            <RouteMap
              fromPlace={fromPlace}
              toPlace={toPlace}
              routes={displayedRoutes}
              selectedRouteId={selectedRouteId}
              onSelectRoute={setSelectedRouteId}
              progressLatLng={progressLatLng}
            />
          </main>

          <BottomSheet
            variant={sheetVariant}
            title={navigating ? t.assistTitle : t.chooseRoute}
          >
            {navigating && selectedRoute ? (
              <>
                <NavigationInstruction
                  route={selectedRoute}
                  snapshot={assistSnapshot}
                />
                <TurnSignalStatus snapshot={assistSnapshot} />
                <AssistPanel
                  snapshot={assistSnapshot}
                  assistMode={assistMode}
                  onAssistModeChange={setAssistMode}
                  onReset={resetAssist}
                />
                <button type="button" className="secondary-btn" onClick={endNavigation}>
                  {t.endNav}
                </button>
                <button
                  type="button"
                  className="linkish"
                  onClick={() => setLabOpen((open) => !open)}
                >
                  {t.labTitle}
                </button>
                {labOpen ? <TrialLogPanel /> : null}
              </>
            ) : (
              <>
                <p className="muted small">{t.heroSub}</p>
                <SearchBar
                  scenarios={scenarios}
                  originKey={originKey}
                  destinationKey={destinationKey}
                  mode={mode}
                  mobility={mobility}
                  timeWindow={timeWindow}
                  deltaMinutes={deltaMinutes}
                  loadingRoutes={loadingRoutes}
                  compact={false}
                  onOriginChange={handleOriginChange}
                  onDestinationChange={handleDestinationChange}
                  onSwapEnds={handleSwapEnds}
                  onModeChange={setMode}
                  onMobilityChange={setMobility}
                  onTimeWindowChange={setTimeWindow}
                  onDeltaChange={(value) =>
                    setDeltaMinutes(value as (typeof DELTA_MINUTES)[number])
                  }
                  onFindRoutes={() => {
                    if (!selectedScenario) return
                    setError(null)
                    setFlow('compare')
                    void loadRoutes()
                  }}
                />

                {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}

                {routesPayload ? (
                  <>
                    <RouteCards
                      fastest={routesPayload.fastest_route}
                      alternatives={routesPayload.alternatives}
                      selectedRouteId={selectedRouteId}
                      recommendedRouteId={recommended?.route_id ?? null}
                      onSelectRoute={setSelectedRouteId}
                      compact={flow !== 'compare'}
                    />
                    {selectedRoute ? (
                      <WhyThisRoute
                        route={selectedRoute}
                        deltaMinutes={deltaMinutes}
                      />
                    ) : null}
                    <div className="sheet-actions">
                      <button
                        type="button"
                        className="primary-btn"
                        onClick={startNavigation}
                        disabled={!selectedRoute}
                      >
                        {t.startNav}
                      </button>
                    </div>
                    <button
                      type="button"
                      className="linkish"
                      onClick={() => setMethodologyOpen(true)}
                    >
                      {t.howItWorks}
                    </button>
                    <AIAnalysis
                      onOpenMethodology={() => setMethodologyOpen(true)}
                      onOpenGap1={IS_MOBILE_BUILD ? undefined : () => void openGap1()}
                    />
                    <button
                      type="button"
                      className="linkish"
                      onClick={() => setLabOpen((open) => !open)}
                    >
                      {t.labTitle}
                    </button>
                    {labOpen ? <TrialLogPanel /> : null}
                  </>
                ) : !initialLoading &&
                  !loadingRoutes &&
                  !error &&
                  (!originKey || !destinationKey || selectedScenario) ? (
                  <StatusBanner tone="info">{t.choosePair}</StatusBanner>
                ) : null}
              </>
            )}
          </BottomSheet>
        </>
      )}

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
