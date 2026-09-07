# AIRPATH-AI Mobile App (Capacitor Android)

This guide covers what the **Pro-tier mobile milestone** delivered in-repo and what **you finish locally** (APK on a phone, ESP32 firmware, store listing).

## What is already in the repo

| Feature | Status |
|---------|--------|
| Capacitor Android shell (`web/capacitor.config.ts`) | Ready |
| Mobile build (`npm run build:mobile`) with bundled API URL | Ready |
| Responsive layout + safe-area CSS | Ready |
| PWA manifest (`public/manifest.webmanifest`) | Ready |
| **Mobility modes** UI: Walking / Cycling / E-bike | Ready (API: walking or motorbike ETAs) |
| **Safety assistant** panel | Ready |
| Maneuver extraction from route polyline | Ready |
| Speed ladder 45→40→30→25→20 by distance | Ready |
| BLE JSON transport (simulated + Web Bluetooth) | Ready |
| Unit tests for maneuver/speed logic | Ready |

The app still uses the **frozen demo API** — no live XGBoost/IDW on device.

Default production API (`.env.mobile`):

`https://airpath-ai-dataporsche-u8gd.onrender.com`

---

## What YOU do locally (lower tier / after Pro)

### A. Build & install APK (Android) — ~30–60 min first time

**Requirements:** Node 20+, **Android Studio**, JDK 17.

```bash
cd web
npm ci
npm run build:mobile
npx cap add android    # first time only
npx cap sync android
npx cap open android
```

In Android Studio:

1. Wait for Gradle sync.
2. **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
3. Install `android/app/build/outputs/apk/debug/app-debug.apk` on your phone.

Or: **Run** with USB debugging.

**If API fails on phone:** ensure Render API is up; rebuild with your URL:

```bash
VITE_API_URL=https://YOUR-API.onrender.com npm run build:mobile
npx cap sync android
```

### B. Play Store / release signing — later

- Generate keystore, `signingConfigs` in Gradle — not required for school demo.
- iOS needs Mac + Apple Developer — out of scope for this milestone.

### C. ESP32 firmware (Đ) — 1–2 days

The app sends JSON (one line) via **BLE Nordic UART** service:

```json
{
  "turn": "left",
  "distance_m": 187,
  "speed_target_kmh": 30,
  "maneuver_index": 1,
  "instruction": "In 187 m, turn left",
  "ts": 1690000000000
}
```

**UUIDs (match `web/src/ble/bleTransport.ts`):**

- Service: `6e400001-b5a3-f393-e0a9-e50e24dcca9e`
- TX (phone → ESP32): `6e400002-b5a3-f393-e0a9-e50e24dcca9e`

**Without BLE paired:** open Chrome DevTools → Application → Local Storage → `airpath_last_assist` (simulated mode).

**Đ’s tasks:**

1. ESP32 BLE server with those UUIDs.
2. Parse JSON → drive relay/LED left/right + OLED speed.
3. Auto-off turn signal after maneuver.

### D. N-lượt experiment table (poster) — Đ + T

See competition notes: compare **Có/Không assistant** on a fixed course; fill Excel table for poster.

### E. Google Maps Navigation SDK — future

Replace polyline demo with live maneuvers when you have API key + time **after** 20/9 demo.

---

## App usage (demo script for video)

1. Open app → choose **From / To** → **Walking / Cycling / E-bike**.
2. Set **+δ minutes** → routes load on map.
3. Tap a route card → open **Safety assistant (demo)**.
4. **Demo play** — watch distance + speed ladder update; JSON goes to BLE/sim.
5. **Pair BLE & send** on Chrome Android with ESP32 nearby (optional).

**Say on camera:** frozen PM2.5 pilot + maneuver assistant prototype; not medical advice.

---

## NPM scripts

| Script | Purpose |
|--------|---------|
| `npm run dev` | Browser dev (proxies API) |
| `npm run build` | Web deploy (Render static site) |
| `npm run build:mobile` | Capacitor bundle (`base: ./`, API URL from `.env.mobile`) |
| `npm run cap:sync` | build:mobile + copy to `android/` |
| `npm run cap:open:android` | Open Android Studio |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Blank map tiles on phone | Needs internet; OSM tiles load over HTTPS |
| “Cannot reach API” | Set `VITE_API_URL`, rebuild, `cap sync` |
| Leaflet markers wrong size | Already using divIcon — OK on WebView |
| BLE pair fails | Use **Demo play** + `localStorage`; flash ESP32 UART UUIDs |
| GPS live inaccurate | Expected on coarse polyline snap — use Demo play for video |

---

## Scientific boundaries (do not change for demo)

- Gap numbers: 19/300, 20/1500, 43/1500, 0.831% — unchanged.
- Assistant ≠ Google Maps navigation.
- PM2.5 on routes = model estimate from frozen pack.
