# What remains after the Pro-tier mobile app

The **in-repo app is complete** for a school demo: Android Capacitor shell, EN/VI UI, frozen route comparison, offline bundled pack fallback, maneuver speed ladder, BLE JSON contract, N-run trial log + CSV export.

This file lists work **you finish locally** (or with a cheaper Cursor plan). Do **not** retrain XGBoost or change Gap numbers.

## Must do on your computer (cannot finish in the cloud)

1. **Install Android Studio** (JDK 17) and open `web/android`.
2. **Build APK:**
   ```bash
   cd web
   npm ci
   npm run cap:sync
   npx cap open android
   ```
   Then **Build → Build APK(s)** and install on a phone.
3. **USB demo video** of: pick OD → Compare routes → Safety assistant **Demo play** → add 1–2 N-run rows → Export CSV.

## Đ — hardware (1–2 days)

- Flash `docs/firmware/esp32_ble_stub.ino` (NimBLE).
- Parse JSON fields `turn`, `distance_m`, `speed_target_kmh`.
- Drive left/right relays + OLED speed.
- Auto-off turn signal after the turn; allow a physical override.
- Pair from the app: **Pair BLE & send** (Web Bluetooth on Chrome Android). Capacitor WebView may need Chrome flags / a Chrome Custom Tab if BLE picker fails — if so, use **Demo play** + `localStorage airpath_last_assist` for the video, and BLE from Chrome browser to the same URL.

## T — poster / stats (half day)

- Fill **N ≥ 10** trials in-app (C vs K), export `airpath_n_luot.csv`.
- Paste the summary table onto the poster.
- Keep frozen science: 19/300, 20/1500, 43/1500, 0.831%.
- Do **not** claim Google Maps live navigation or medical benefit.

## After 20/9 (optional)

- Google Navigation SDK (API key + billing).
- iOS (Mac + Apple Developer).
- Play Store signing keystore.
- Live HealthyAir / sub-hourly buckets (new research, not this demo pack).
