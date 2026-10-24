export type ScoreFactor = {
  name?: string
  label?: string
  value?: number | string | null
  score?: number | null
  weight?: number | null
  explanation?: string
  available?: boolean
}

export type RecommendationOption = {
  place_id?: string | number
  name?: string
  latitude?: number | null
  longitude?: number | null
  time?: string
  suitability_score?: number | null
  score_factors?: ScoreFactor[]
  explanation?: string
}

export type EvidenceRecord = {
  claim?: string
  value?: string | number | null
  unit?: string
  source?: string
  source_url?: string
  observed_for?: string
  fetched_at?: string
  location?: { latitude?: number; longitude?: number }
}

export type DataSource = string | { name?: string; source?: string; url?: string; source_url?: string }

export type RecommendationResponse = {
  status?: 'ok' | 'partial' | 'needs_clarification' | 'no_results' | string
  interpreted_query?: {
    activity?: string
    location_label?: string
    radius_km?: number
    start_time?: string
    end_time?: string
    profile_flags?: string[]
  }
  recommendation?: RecommendationOption | null
  alternatives?: RecommendationOption[]
  advice?: { carry?: string[]; watch_for?: string[]; avoid_if?: string[] }
  evidence?: EvidenceRecord[]
  data_sources?: DataSource[]
  warnings?: string[]
  coverage?: number | null
}
