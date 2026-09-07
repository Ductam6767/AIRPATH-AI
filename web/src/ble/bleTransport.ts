import type { AssistPayload } from '../maneuver/types'

/** Minimal Web Bluetooth typing (Chrome Android). */
interface BluetoothRemoteGATT {
  requestDevice(options: {
    filters: { services: string[] }[]
    optionalServices?: string[]
  }): Promise<{ name?: string; gatt?: { connect(): Promise<BluetoothGattServer> } }>
}

interface BluetoothGattServer {
  getPrimaryService(uuid: string): Promise<{
    getCharacteristic(uuid: string): Promise<{ writeValue(data: BufferSource): Promise<void> }>
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

/** Send assist JSON to ESP32 (Web Bluetooth) or simulate for dev / APK without pairing. */
export async function sendAssistPayload(
  payload: AssistPayload,
  options?: { preferBluetooth?: boolean },
): Promise<void> {
  state = { ...state, lastPayload: payload, lastError: null }

  const preferBt = options?.preferBluetooth ?? false
  const nav = typeof navigator !== 'undefined' ? navigator : undefined
  const bt = nav && 'bluetooth' in nav ? (nav as Navigator & { bluetooth: BluetoothRemoteGATT }).bluetooth : undefined

  if (preferBt && bt) {
    try {
      // One-shot write per payload; full GATT session caching is left for Đ's firmware loop.
      const device = await bt.requestDevice({
        filters: [{ services: [AIRPATH_BLE_SERVICE] }],
        optionalServices: [AIRPATH_BLE_SERVICE],
      })
      const server = await device.gatt?.connect()
      const service = await server?.getPrimaryService(AIRPATH_BLE_SERVICE)
      const tx = await service?.getCharacteristic(AIRPATH_BLE_TX_CHAR)
      const enc = new TextEncoder()
      await tx?.writeValue(enc.encode(encodePayload(payload)))
      state = {
        ...state,
        status: 'web_bluetooth',
        deviceName: device.name ?? 'BLE device',
      }
      emit()
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

  state = { ...state, status: 'simulated', deviceName: null }
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('airpath_last_assist', encodePayload(payload))
  }
  if (import.meta.env.DEV) {
    console.info('[AIRPATH assist]', payload)
  }
  emit()
}

export function resetBleTransport(): void {
  state = {
    status: 'idle',
    lastPayload: null,
    lastError: null,
    deviceName: null,
  }
  emit()
}
