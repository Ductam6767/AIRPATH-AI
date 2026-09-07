import type { AssistPayload } from '../maneuver/types'

interface BluetoothRemoteGATT {
  requestDevice(options: {
    filters: { services: string[] }[]
    optionalServices?: string[]
  }): Promise<{
    name?: string
    gatt?: { connect(): Promise<BluetoothGattServer> }
  }>
}

interface BluetoothGattServer {
  getPrimaryService(uuid: string): Promise<{
    getCharacteristic(uuid: string): Promise<{
      writeValue(data: BufferSource): Promise<void>
    }>
  }>
}

export type BleTransportStatus =
  | 'idle'
  | 'simulated'
  | 'web_bluetooth'
  | 'error'

export interface BleTransportState {
  status: BleTransportStatus
  lastPayload: AssistPayload | null
  lastError: string | null
  deviceName: string | null
}

/** Nordic UART-style service UUIDs (common on ESP32 BLE serial examples). */
export const AIRPATH_BLE_SERVICE = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
export const AIRPATH_BLE_TX_CHAR = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'

type Listener = (state: BleTransportState) => void

let state: BleTransportState = {
  status: 'idle',
  lastPayload: null,
  lastError: null,
  deviceName: null,
}

const listeners = new Set<Listener>()

let cachedWrite:
  | ((data: BufferSource) => Promise<void>)
  | null = null

function emit() {
  for (const l of listeners) l({ ...state })
}

export function subscribeBleTransport(listener: Listener): () => void {
  listeners.add(listener)
  listener({ ...state })
  return () => listeners.delete(listener)
}

export function getBleTransportState(): BleTransportState {
  return { ...state }
}

function encodePayload(payload: AssistPayload): string {
  return JSON.stringify(payload)
}

function getBluetooth(): BluetoothRemoteGATT | undefined {
  const nav = typeof navigator !== 'undefined' ? navigator : undefined
  if (nav && 'bluetooth' in nav) {
    return (nav as Navigator & { bluetooth: BluetoothRemoteGATT }).bluetooth
  }
  return undefined
}

export async function pairBleDevice(): Promise<void> {
  const bt = getBluetooth()
  if (!bt) {
    throw new Error('Web Bluetooth is not available in this browser.')
  }
  const device = await bt.requestDevice({
    filters: [{ services: [AIRPATH_BLE_SERVICE] }],
    optionalServices: [AIRPATH_BLE_SERVICE],
  })
  const server = await device.gatt?.connect()
  const service = await server?.getPrimaryService(AIRPATH_BLE_SERVICE)
  const tx = await service?.getCharacteristic(AIRPATH_BLE_TX_CHAR)
  if (!tx) {
    throw new Error('AIRPATH BLE characteristic not found.')
  }
  cachedWrite = (data) => tx.writeValue(data)
  state = {
    ...state,
    status: 'web_bluetooth',
    deviceName: device.name ?? 'AIRPATH-Assist',
    lastError: null,
  }
  emit()
}

async function writePayload(payload: AssistPayload): Promise<void> {
  if (!cachedWrite) {
    throw new Error('BLE not paired.')
  }
  const enc = new TextEncoder()
  await cachedWrite(enc.encode(encodePayload(payload)))
  state = { ...state, lastPayload: payload, status: 'web_bluetooth', lastError: null }
  emit()
}

function simulate(payload: AssistPayload): void {
  state = {
    ...state,
    lastPayload: payload,
    lastError: null,
    status: cachedWrite ? 'web_bluetooth' : 'simulated',
  }
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('airpath_last_assist', encodePayload(payload))
  }
  if (import.meta.env.DEV) {
    console.info('[AIRPATH assist]', payload)
  }
  emit()
}

/** Send assist JSON to a paired ESP32, or simulate when unpaired. */
export async function sendAssistPayload(
  payload: AssistPayload,
  options?: { preferBluetooth?: boolean },
): Promise<void> {
  state = { ...state, lastPayload: payload, lastError: null }

  if (cachedWrite) {
    try {
      await writePayload(payload)
      return
    } catch (err) {
      cachedWrite = null
      state = {
        ...state,
        status: 'error',
        lastError: err instanceof Error ? err.message : String(err),
      }
      emit()
    }
  }

  if (options?.preferBluetooth) {
    try {
      await pairBleDevice()
      await writePayload(payload)
      return
    } catch (err) {
      state = {
        ...state,
        status: 'error',
        lastError: err instanceof Error ? err.message : String(err),
      }
      emit()
      throw err
    }
  }

  simulate(payload)
}

export function resetBleTransport(): void {
  cachedWrite = null
  state = {
    status: 'idle',
    lastPayload: null,
    lastError: null,
    deviceName: null,
  }
  emit()
}
