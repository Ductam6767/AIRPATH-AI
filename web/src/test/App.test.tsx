import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import {
  mockRoutesEmptyAlts,
  mockRoutesWithAlts,
  mockScenarios,
} from './fixtures'

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
    expect(await screen.findByText('Fastest route')).toBeInTheDocument()
    expect(screen.getByText(/Exposure-aware option 1/i)).toBeInTheDocument()
    expect(screen.getByText(/28% lower predicted exposure/i)).toBeInTheDocument()
    expect(
      screen.getByText(/time-weighted proxy, not a medical risk score/i),
    ).toBeInTheDocument()
  })

  it('updates delta slider to absolute minute values', async () => {
    stubApi()
    render(<App />)
    await screen.findByText('Fastest route')

    const slider = screen.getByLabelText(/How much extra time/i)
    fireEvent.change(slider, { target: { value: '4' } })

    await waitFor(() => {
      expect(screen.getByText('+5 min')).toBeInTheDocument()
      expect(screen.getByText(/Allow up to \+5 min/i)).toBeInTheDocument()
    })
  })

  it('selects a route from a card and updates selection state', async () => {
    const user = userEvent.setup()
    stubApi()
    render(<App />)
    await screen.findByText('Fastest route')
    expect(screen.getByTestId('selected-route')).toHaveTextContent('walking-1')

    const altCard = screen.getByRole('button', {
      name: /Exposure-aware option 1/i,
    })
    await user.click(altCard)
    expect(screen.getByTestId('selected-route')).toHaveTextContent('walking-2')
  })

  it('shows empty-alternatives message without empty cards', async () => {
    stubApi({ routes: mockRoutesEmptyAlts })
    // Force delta 0 path: change slider after load
    render(<App />)
    await screen.findByText('Fastest route')
    const slider = screen.getByLabelText(/How much extra time/i)
    fireEvent.change(slider, { target: { value: '0' } })

    await waitFor(() => {
      expect(
        screen.getByText(/No alternative fits the selected 0-minute limit/i),
      ).toBeInTheDocument()
    })
    expect(screen.queryByText(/Exposure-aware option/i)).not.toBeInTheDocument()
    const list = screen.getByRole('list')
    expect(within(list).getAllByRole('listitem')).toHaveLength(1)
  })

  it('shows a friendly error when the API is unavailable', async () => {
    stubApi({ scenariosFail: true })
    render(<App />)
    expect(
      await screen.findByText(/Cannot reach the AIRPATH demo API/i),
    ).toBeInTheDocument()
  })
})
