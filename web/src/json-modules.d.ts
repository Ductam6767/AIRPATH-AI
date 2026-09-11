declare module '@demo-pack/scenarios.json' {
  const value: { scenarios: unknown[] }
  export default value
}

declare module '@demo-pack/routes.json' {
  const value: { routes: unknown[] }
  export default value
}

declare module '@demo-pack/metadata.json' {
  const value: Record<string, unknown>
  export default value
}

declare module '@demo-pack/guidance_cues.json' {
  const value: {
    routes: Record<string, unknown[]>
    trigger_m?: Record<string, number>
  }
  export default value
}
