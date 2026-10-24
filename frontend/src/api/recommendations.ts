import type { RecommendationResponse } from '../types/recommendations'

export async function requestRecommendation(question: string): Promise<RecommendationResponse> {
  const response = await fetch('/api/recommendations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
    signal: AbortSignal.timeout(90_000),
  })

  const payload: unknown = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
      ? String(payload.detail)
      : `Planner request failed (${response.status}).`
    throw new Error(detail)
  }
  return payload as RecommendationResponse
}
