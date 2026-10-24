export type PlannerHealth = 'checking' | 'ready' | 'model-not-ready' | 'api-unavailable' | 'unknown'

export async function getPlannerHealth(): Promise<PlannerHealth> {
  try {
    const response = await fetch('/health', { signal: AbortSignal.timeout(5_000), cache: 'no-store' })
    if (!response.ok) return 'api-unavailable'
    const health: unknown = await response.json()
    if (typeof health !== 'object' || health === null) return 'unknown'
    if ('model_ready' in health && typeof health.model_ready === 'boolean') {
      return health.model_ready ? 'ready' : 'model-not-ready'
    }
    return 'unknown'
  } catch {
    return 'api-unavailable'
  }
}
