/** Capacitor native shell hooks (no-op on web). */
export async function initCapacitorShell(): Promise<void> {
  if (!import.meta.env.VITE_CAPACITOR) return

  try {
    const { Capacitor } = await import('@capacitor/core')
    if (!Capacitor.isNativePlatform()) return

    const { StatusBar, Style } = await import('@capacitor/status-bar')
    await StatusBar.setStyle({ style: Style.Dark })
    await StatusBar.setBackgroundColor({ color: '#0B1F33' })

    const { SplashScreen } = await import('@capacitor/splash-screen')
    await SplashScreen.hide()
  } catch {
    // Plugins optional during vitest / SSR-less dev
  }
}

export async function isNativeApp(): Promise<boolean> {
  if (!import.meta.env.VITE_CAPACITOR) return false
  try {
    const { Capacitor } = await import('@capacitor/core')
    return Capacitor.isNativePlatform()
  } catch {
    return false
  }
}
