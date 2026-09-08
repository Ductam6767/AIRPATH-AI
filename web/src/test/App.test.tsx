import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import {
  mockRoutesEmptyAlts,
  mockRoutesHigherExposure,
  mockRoutesWithAlts,
  mockScenarios,
} from './fixtures'

vi.mock('../offline/localDemo', async () => {
  const { mockRoutesWithAlts, mockScenarios } = await import('./fixtures')
  return {
    localFetchScenarios: async () => mockScenarios,
    localFetchRoutes: async () => mockRoutesWithAlts,
  }
})

vi.mock('../components/RouteMap', () => ({
  RouteMap: ({
    routes,
    selectedRouteId,
    onSelectRoute,
  }: {
    routes: { route_id: string }[]
    selectedRouteId: string | null
    onSelectRoute: (id: string) => void
  }) => (
    <div data-testid="mock-map">
      <span data-testid="selected-route">{selectedRouteId}</span>
      {routes.map((route) => (
        <button
          key={route.route_id}
          type="button"
          onClick={() => onSelectRoute(route.route_id)}
        >
          map:{route.route_id}
        </button>
      ))}
    </div>
  ),
}))

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function stubApi(options?: {
  routes?: typeof mockRoutesWithAlts
  scenariosFail?: boolean
}) {
  const routesPayload = options?.routes ?? mockRoutesWithAlts
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/demo/scenarios')) {
        if (options?.scenariosFail) {
          throw new TypeError('Failed to fetch')
        }
        return jsonResponse(mockScenarios)
      }
      if (url.includes('/demo/routes')) {
        if (url.includes('delta_minutes=0')) {
          return jsonResponse(mockRoutesEmptyAlts)
        }
        return jsonResponse(routesPayload)
      }
      return jsonResponse({ detail: 'not found' }, 404)
    }),
  )
}

describe('AIRPATH frontend', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders API route comparison from backend response', async () => {
    stubApi()
    render(<App />)

    expect(await screen.findByText('AIRPATH-AI')).toBeInTheDocument()
    expect(screen.getByText('Health-aware navigation')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Compare routes' }),
    ).toBeInTheDocument()
    expect(
      await screen.findByRole('button', { name: /Fastest, 40 minutes/i }),
    ).toBeInTheDocument()
    expect(screen.getByText('Health-first')).toBeInTheDocument()
    expect(screen.getAllByText(/28% lower predicted exposure/i).length).toBeGreaterThan(0)
    expect(screen.getByText('Lower predicted exposure')).toBeInTheDocument()
    expect(screen.getByText(/Why this route/i)).toBeInTheDocument()
    expect(
      screen.getByText(
        /AIRPATH compares feasible route alternatives rather than guaranteeing a cleaner route/i,
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/time-weighted proxy from hourly data, not a medical risk score/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Origin 01' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Park Gate' })).toBeInTheDocument()
  })

  it('updates delta slider to absolute minute values', async () => {
    stubApi()
    render(<App />)
    await screen.findByRole('button', { name: /Fastest, 40 minutes/i })

    const slider = screen.getByLabelText(/Maximum additional time/i)
    fireEvent.change(slider, { target: { value: '4' } })

    await waitFor(() => {
      expect(screen.getByText('Allow up to +5 min')).toBeInTheDocument()
    })
  })

  it('selects a route from a card and updates selection state', async () => {
    const user = userEvent.setup()
    stubApi()
    render(<App />)
    await screen.findByRole('button', { name: /Fastest, 40 minutes/i })
    expect(screen.getByTestId('selected-route')).toHaveTextContent('walking-2')

    const fastestCard = screen.getByRole('button', {
      name: /Fastest, 40 minutes/i,
    })
    await user.click(fastestCard)
    expect(screen.getByTestId('selected-route')).toHaveTextContent('walking-1')
  })

  it('shows empty-alternatives message without empty cards', async () => {
    stubApi({ routes: mockRoutesEmptyAlts })
    render(<App />)
    await screen.findByRole('button', { name: /Fastest, 40 minutes/i })
    const slider = screen.getByLabelText(/Maximum additional time/i)
    fireEvent.change(slider, { target: { value: '0' } })

    await waitFor(() => {
      expect(
        screen.getByText(
          'No lower-exposure alternative was found within your time limit.',
        ),
      ).toBeInTheDocument()
    })
    expect(
      screen.getByText(
        'Fastest route is also the lowest-exposure feasible option.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByText(/AIRPATH alternative/i)).not.toBeInTheDocument()
    const list = screen.getByRole('list')
    expect(within(list).getAllByRole('listitem')).toHaveLength(1)
  })

  it('labels higher-exposure alternatives as feasible, not lower', async () => {
    stubApi({ routes: mockRoutesHigherExposure })
    render(<App />)
    expect(await screen.findByText(/\+10% higher predicted exposure/i)).toBeInTheDocument()
    expect(screen.getByText('Feasible alternative')).toBeInTheDocument()
    expect(screen.queryByText('Lower predicted exposure')).not.toBeInTheDocument()
    expect(
      screen.getByText(
        'Fastest route is also the lowest-exposure feasible option.',
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        'No lower-exposure alternative was found within your time limit.',
      ),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/guaranteeing a cleaner route/i),
    ).not.toBeInTheDocument()
  })

  it('explains in methodology that AIRPATH compares rather than guaranteeing a cleaner route', async () => {
    const user = userEvent.setup()
    stubApi()
    render(<App />)
    await screen.findByRole('button', { name: /Fastest, 40 minutes/i })
    await user.click(screen.getByRole('button', { name: 'How AIRPATH works' }))
    expect(
      await screen.findByText(
        /AIRPATH compares those feasible alternatives rather than guaranteeing a cleaner route/i,
      ),
    ).toBeInTheDocument()
  })

  it('starts navigation without leaving the real route data', async () => {
    const user = userEvent.setup()
    stubApi()
    render(<App />)
    await screen.findByRole('button', { name: /Fastest, 40 minutes/i })
    await user.click(screen.getByRole('button', { name: 'Start navigation' }))
    expect(screen.getByText('Turn-signal assist')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'End navigation' })).toBeInTheDocument()
  })

  it('shows an API error when scenarios fail on the web build', async () => {
    stubApi({ scenariosFail: true })
    render(<App />)
    expect(
      await screen.findByText(/demo API is unavailable/i),
    ).toBeInTheDocument()
  })
})
