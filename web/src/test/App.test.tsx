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

async function choosePlace(
  user: ReturnType<typeof userEvent.setup>,
  field: 'From' | 'To',
  optionName: string,
) {
  await user.selectOptions(screen.getByLabelText(field), optionName)
}

async function chooseDefaultTrip() {
  const user = userEvent.setup()
  await screen.findByLabelText('From')
  await choosePlace(user, 'From', 'Origin 01')
  await choosePlace(user, 'To', 'Destination 01')
  await user.click(screen.getByRole('button', { name: 'Compare routes' }))
  await screen.findByRole('button', { name: /Fastest, 40 minutes/i })
  return user
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

  it('does not auto-select a trip or load routes', async () => {
    stubApi()
    render(<App />)
    expect(await screen.findByText('AIRPATH-AI')).toBeInTheDocument()
    const from = screen.getByLabelText('From')
    const to = screen.getByLabelText('To')
    expect(from).toHaveDisplayValue('Choose origin')
    expect(to).toHaveDisplayValue('Choose destination')
    expect(within(from).getByRole('option', { name: 'Origin 01' })).toBeInTheDocument()
    expect(within(from).getByRole('option', { name: 'Park Gate' })).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /Fastest, 40 minutes/i }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Compare routes' })).toBeDisabled()
  })

  it('lets destination be chosen first and infers the only stored origin', async () => {
    const user = userEvent.setup()
    stubApi()
    render(<App />)
    const to = await screen.findByLabelText('To')
    expect(to).not.toBeDisabled()
    expect(within(to).getByRole('option', { name: 'Destination 01' })).toBeInTheDocument()
    expect(within(to).getByRole('option', { name: 'Market Hall' })).toBeInTheDocument()
    expect(within(to).getByRole('option', { name: 'Park Gate' })).toBeInTheDocument()
    await user.selectOptions(to, 'Destination 01')
    expect(screen.getByLabelText('From')).toHaveDisplayValue('Origin 01')
    expect(to).toHaveDisplayValue('Destination 01')
    expect(
      within(to).queryByRole('option', { name: 'Market Hall' }),
    ).not.toBeInTheDocument()
    expect(
      within(screen.getByLabelText('From')).getByRole('option', { name: 'Park Gate' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /Fastest, 40 minutes/i }),
    ).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Compare routes' }))
    expect(
      await screen.findByRole('button', { name: /Fastest, 40 minutes/i }),
    ).toBeInTheDocument()
  })

  it('fills the only precomputed To after From is chosen and waits for Compare', async () => {
    const user = userEvent.setup()
    stubApi()
    render(<App />)
    const from = await screen.findByLabelText('From')
    const to = screen.getByLabelText('To')
    await user.selectOptions(from, 'Origin 01')
    expect(from).toHaveDisplayValue('Origin 01')
    expect(to).toHaveDisplayValue('Destination 01')
    expect(within(to).getByRole('option', { name: 'Destination 01' })).toBeInTheDocument()
    expect(
      within(to).queryByRole('option', { name: 'Market Hall' }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Compare routes' })).toBeEnabled()
    expect(
      screen.queryByRole('button', { name: /Fastest, 40 minutes/i }),
    ).not.toBeInTheDocument()
    expect(
      screen.getByText(/one stored destination in the demo pack/i),
    ).toBeInTheDocument()
  })

  it('changes From to another stored trip and infers that trip To without drawing yet', async () => {
    const user = userEvent.setup()
    stubApi()
    render(<App />)
    await screen.findByLabelText('From')
    await user.selectOptions(screen.getByLabelText('From'), 'Origin 01')
    expect(screen.getByLabelText('To')).toHaveDisplayValue('Destination 01')
    await user.selectOptions(screen.getByLabelText('From'), 'Park Gate')
    expect(screen.getByLabelText('From')).toHaveDisplayValue('Park Gate')
    expect(screen.getByLabelText('To')).toHaveDisplayValue('Market Hall')
    expect(
      screen.queryByRole('button', { name: /Fastest, 40 minutes/i }),
    ).not.toBeInTheDocument()
  })

  it('swaps From and To without replacing them with another trip', async () => {
    const user = userEvent.setup()
    stubApi()
    render(<App />)
    await screen.findByLabelText('From')
    await choosePlace(user, 'From', 'Origin 01')
    await choosePlace(user, 'To', 'Destination 01')
    await user.click(screen.getByRole('button', { name: 'Compare routes' }))
    await screen.findByRole('button', { name: /Fastest, 40 minutes/i })
    await user.click(screen.getByRole('button', { name: 'Swap origin and destination' }))
    expect(screen.getByLabelText('From')).toHaveDisplayValue('Destination 01')
    expect(screen.getByLabelText('To')).toHaveDisplayValue('Origin 01')
    await user.click(screen.getByRole('button', { name: 'Compare routes' }))
    expect(
      await screen.findByRole('button', { name: /Fastest, 40 minutes/i }),
    ).toBeInTheDocument()
  })

  it('draws the route after Compare is clicked with both ends chosen', async () => {
    const user = userEvent.setup()
    stubApi()
    render(<App />)
    const from = await screen.findByLabelText('From')
    const to = screen.getByLabelText('To')
    await user.selectOptions(from, 'Origin 01')
    expect(
      screen.queryByRole('button', { name: /Fastest, 40 minutes/i }),
    ).not.toBeInTheDocument()
    await user.selectOptions(to, 'Destination 01')
    expect(from).toHaveDisplayValue('Origin 01')
    expect(to).toHaveDisplayValue('Destination 01')
    expect(
      screen.queryByRole('button', { name: /Fastest, 40 minutes/i }),
    ).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Compare routes' }))
    expect(
      await screen.findByRole('button', { name: /Fastest, 40 minutes/i }),
    ).toBeInTheDocument()
  })

  it('omits unmatched To options instead of showing an unmatched-pair error', async () => {
    const user = userEvent.setup()
    stubApi()
    render(<App />)
    await screen.findByLabelText('From')
    await user.selectOptions(screen.getByLabelText('From'), 'Origin 01')
    expect(screen.getByLabelText('To')).toHaveDisplayValue('Destination 01')
    expect(
      within(screen.getByLabelText('To')).queryByRole('option', {
        name: 'Market Hall',
      }),
    ).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('From'), 'Park Gate')
    expect(screen.getByLabelText('From')).toHaveDisplayValue('Park Gate')
    expect(screen.getByLabelText('To')).toHaveDisplayValue('Market Hall')
    expect(screen.queryByText(/No demo route between these two places/i)).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /Fastest, 40 minutes/i }),
    ).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Compare routes' }))
    expect(
      await screen.findByRole('button', { name: /Fastest, 40 minutes/i }),
    ).toBeInTheDocument()
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
      within(screen.getByLabelText('From')).getByRole('option', { name: 'Origin 01' }),
    ).toBeInTheDocument()
    expect(
      within(screen.getByLabelText('To')).getByRole('option', { name: 'Park Gate' }),
    ).toBeInTheDocument()
    await chooseDefaultTrip()
    expect(
      screen.getByRole('button', { name: /Fastest, 40 minutes/i }),
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
  })

  it('does not claim Fastest is also cleanest when a lower-exposure alternative exists', async () => {
    stubApi()
    render(<App />)
    const user = await chooseDefaultTrip()
    expect(
      screen.getByText(
        /this route provides lower PM2.5 exposure while remaining within the applicable travel-time constraint/i,
      ),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Fastest, 40 minutes/i }))
    expect(
      screen.getByText(
        /This is the hurry option: shortest time. Another feasible route has lower predicted exposure/i,
      ),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/also the lowest predicted time-weighted PM2.5/i),
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/Also lowest estimated exposure/i)).not.toBeInTheDocument()
    expect(
      screen.queryByText(/no stored detour beats Fastest by more than 0.5%/i),
    ).not.toBeInTheDocument()
  })

  it('updates delta slider to absolute minute values', async () => {
    stubApi()
    render(<App />)
    await chooseDefaultTrip()

    const slider = screen.getByLabelText(/Maximum additional time/i)
    fireEvent.change(slider, { target: { value: '4' } })

    await waitFor(() => {
      expect(screen.getByText('Allow up to +5 min')).toBeInTheDocument()
    })
  })

  it('selects a route from a card and updates selection state', async () => {
    stubApi()
    render(<App />)
    const user = await chooseDefaultTrip()
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
    await chooseDefaultTrip()
    const slider = screen.getByLabelText(/Maximum additional time/i)
    fireEvent.change(slider, { target: { value: '0' } })

    await waitFor(() => {
      expect(
        screen.getByText(
          'No other feasible route was found within your time limit.',
        ),
      ).toBeInTheDocument()
    })
    expect(
      screen.getByText(
        'Fastest route is also the lowest-exposure feasible option.',
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/no stored detour beats Fastest by more than 0.5%/i),
    ).toBeInTheDocument()
    const list = screen.getByRole('list')
    expect(within(list).getAllByRole('listitem')).toHaveLength(1)
  })

  it('labels higher-exposure alternatives as feasible, not lower', async () => {
    stubApi({ routes: mockRoutesHigherExposure })
    render(<App />)
    await chooseDefaultTrip()
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
        'The other cards are feasible detours within your time limit. They are not lower-exposure than the fastest route on this proxy.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText('Also lowest estimated exposure')).toBeInTheDocument()
    expect(
      screen.getByText(/no stored detour beats Fastest by more than 0.5%/i),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/guaranteeing a cleaner route/i),
    ).not.toBeInTheDocument()
  })

  it('explains in methodology that AIRPATH compares rather than guaranteeing a cleaner route', async () => {
    stubApi()
    render(<App />)
    const user = await chooseDefaultTrip()
    await user.click(screen.getByRole('button', { name: 'How AIRPATH works' }))
    expect(
      await screen.findByText(
        /AIRPATH compares those feasible alternatives rather than guaranteeing a cleaner route/i,
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/16 precomputed origin–destination trips/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/not filtered on exposure reduction or map aesthetics/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/not live A-to-B city search/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/You cannot freely pair any two places/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/pairing limit is demo packaging/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Why Fastest wins on estimated exposure in this demo/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/E = Σ \(PM on each segment × minutes on that segment\)/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/0 of 16 origin–destination pairs/i),
    ).toBeInTheDocument()
  })

  it('starts navigation without leaving the real route data', async () => {
    stubApi()
    render(<App />)
    const user = await chooseDefaultTrip()
    await user.click(screen.getByRole('button', { name: 'Start navigation' }))
    expect(screen.getByText('Turn-signal assist')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'End navigation' })).toBeInTheDocument()
  })

  it('falls back to the bundled demo pack when the API is unavailable', async () => {
    stubApi({ scenariosFail: true })
    render(<App />)
    expect(await screen.findByText(/bundled demo pack/i)).toBeInTheDocument()
    expect(
      within(screen.getByLabelText('From')).getByRole('option', { name: 'Origin 01' }),
    ).toBeInTheDocument()
    expect(screen.queryByText(/demo API is unavailable/i)).not.toBeInTheDocument()
  })
})
