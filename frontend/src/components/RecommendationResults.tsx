import { useEffect, useMemo, useRef, useState } from 'react'
import { CircleAlert, Clock3, ExternalLink, MapPin, ShieldAlert, Sparkles, Wind } from 'lucide-react'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import type { EvidenceRecord, RecommendationOption, RecommendationResponse } from '../types/recommendations'

const pin = L.divIcon({ className: 'gowise-pin', html: '<span></span>', iconSize: [24, 32], iconAnchor: [12, 30], popupAnchor: [0, -27] })
const selectedPin = L.divIcon({ className: 'gowise-pin gowise-pin-selected', html: '<span></span>', iconSize: [28, 36], iconAnchor: [14, 34], popupAnchor: [0, -30] })

function validPoint(option: RecommendationOption | null | undefined): option is RecommendationOption & { latitude: number; longitude: number } {
  return typeof option?.latitude === 'number' && Number.isFinite(option.latitude)
    && typeof option.longitude === 'number' && Number.isFinite(option.longitude)
    && Math.abs(option.latitude) <= 90 && Math.abs(option.longitude) <= 180
}

function MapBounds({ points, selected }: { points: Array<RecommendationOption & { latitude: number; longitude: number }>; selected?: RecommendationOption & { latitude: number; longitude: number } }) {
  const map = useMap()
  const previousSignature = useRef('')
  const signature = points.map(point => `${point.latitude},${point.longitude}`).join('|')
  useEffect(() => {
    if (signature !== previousSignature.current) {
      previousSignature.current = signature
      if (points.length > 1) map.fitBounds(points.map(point => [point.latitude, point.longitude]), { padding: [38, 38], maxZoom: 14 })
      else if (points[0]) map.setView([points[0].latitude, points[0].longitude], 14)
    } else if (selected) {
      map.flyTo([selected.latitude, selected.longitude], Math.max(map.getZoom(), 14), { duration: 0.45 })
    }
  }, [map, points, selected, signature])
  return null
}

function formatDateTime(value?: string) {
  if (!value) return 'Time not provided'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(date)
}

function prettyLabel(value?: string) {
  return (value || 'Outdoor plan').replaceAll('_', ' ').replace(/\b\w/g, character => character.toUpperCase())
}

function OptionCard({ option, rank, primary, selected, onSelect }: { option: RecommendationOption; rank: number; primary?: boolean; selected: boolean; onSelect: () => void }) {
  const score = typeof option.suitability_score === 'number' ? option.suitability_score : null
  return <article className={`recommendation-card${primary ? ' recommendation-primary' : ''}${selected ? ' recommendation-selected' : ''}`}>
    <div className="recommendation-card-top"><span className="rank-label">{primary ? 'BEST MATCH' : `OPTION 0${rank}`}</span><div className="recommendation-actions">{score !== null && <span className="heuristic-score"><b>{Math.round(score)}</b><small>/ 100 · heuristic</small></span>}{validPoint(option) && <button className="map-focus-button" type="button" aria-pressed={selected} onClick={onSelect}>{selected ? 'On map' : 'Show on map'}</button>}</div></div>
    <h3>{option.name || 'Outdoor location'}</h3>
    <p className="option-time"><Clock3 size={14} />{formatDateTime(option.time)}</p>
    {option.explanation && <p className="option-explanation">{option.explanation}</p>}
    {!!option.score_factors?.length && <div className="score-factors">{option.score_factors.map((factor, index) => <span key={`${factor.name || factor.label || 'factor'}-${index}`} title={factor.explanation}>{prettyLabel(factor.label || factor.name)}{factor.value !== undefined && factor.value !== null ? ` · ${factor.value}` : ''}</span>)}</div>}
  </article>
}

function EvidenceItem({ record }: { record: EvidenceRecord }) {
  const observedFor = formatDateTime(record.observed_for)
  const fetched = record.fetched_at ? new Date(record.fetched_at) : null
  return <li className="evidence-row">
    <div className="evidence-value"><strong>{record.value === null || record.value === undefined ? 'Unavailable' : `${record.value}${record.unit ? ` ${record.unit}` : ''}`}</strong><span>{record.claim || 'Provider data'}</span></div>
    <div className="evidence-meta"><span>{record.source || 'Source unavailable'}</span><span>For {observedFor}</span>{fetched && !Number.isNaN(fetched.getTime()) && <span>Fetched {new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(fetched)}</span>}{record.source_url && <a href={record.source_url} target="_blank" rel="noreferrer" aria-label={`Open ${record.source || 'data'} source`}><ExternalLink size={13} /></a>}</div>
  </li>
}

export default function RecommendationResults({ data }: { data: RecommendationResponse }) {
  const recommendation = data.recommendation || null
  const allOptions = useMemo(() => [recommendation, ...(data.alternatives || [])].filter((option): option is RecommendationOption => !!option), [recommendation, data.alternatives])
  const options = useMemo(() => allOptions.filter(validPoint), [allOptions])
  const [activeOption, setActiveOption] = useState<RecommendationOption | undefined>(recommendation || undefined)
  useEffect(() => setActiveOption(recommendation || undefined), [recommendation])
  const activePoint = options.find(option => option === activeOption) || options[0]
  const center = options.length ? [options[0].latitude, options[0].longitude] as [number, number] : [20, 0] as [number, number]
  const coverage = typeof data.coverage === 'number' ? Math.max(0, Math.min(100, data.coverage <= 1 ? data.coverage * 100 : data.coverage)) : null
  const hasAdvice = !!(data.advice?.carry?.length || data.advice?.watch_for?.length || data.advice?.avoid_if?.length)

  if (!recommendation) return <div className="planner-response" aria-live="polite">
    <div className="clarification-card"><span className="clarification-icon"><CircleAlert size={19} /></span><div><span className="section-kicker">{data.status === 'data_unavailable' ? 'LIVE DATA UNAVAILABLE' : data.status === 'unsupported_activity' ? 'ACTIVITY NOT SUPPORTED' : 'A LITTLE MORE TO GO ON'}</span><h3>{data.status === 'no_results' ? 'No mapped options came back' : data.status === 'data_unavailable' ? 'No evidence-backed plan yet' : data.status === 'unsupported_activity' ? 'Try one of the supported activities' : 'Can you narrow it down?'}</h3><p>{data.clarification_question || data.warnings?.[0] || (data.status === 'no_results' ? 'Try a nearby area or a different activity.' : 'Add a place and a time window so the planner can compare live conditions.')}</p></div></div>
    {!!data.warnings?.length && <WarningList warnings={data.warnings} />}
  </div>

  return <section className="planner-response" aria-label="Outdoor recommendations" aria-live="polite">
    <div className="results-heading"><div><span className="section-kicker"><Sparkles size={13} /> YOUR OUTDOOR PLAN</span><h2>{prettyLabel(data.interpreted_query?.activity)}<span>{data.interpreted_query?.location_label ? ` around ${data.interpreted_query.location_label}` : ''}</span></h2><p className="results-window">{formatDateTime(data.interpreted_query?.start_time)}{data.interpreted_query?.end_time ? ` – ${formatDateTime(data.interpreted_query.end_time)}` : ''}</p>{!!data.interpreted_query?.profile_flags?.length && <div className="interpreted-profiles"><span>Considered:</span>{data.interpreted_query.profile_flags.map(flag => <span className="interpreted-profile" key={flag}>{prettyLabel(flag)}</span>)}</div>}</div>{coverage !== null && <div className="coverage-badge"><span>DATA COVERAGE</span><strong>{Math.round(coverage)}%</strong></div>}</div>
    {data.status === 'partial' && <div className="partial-banner"><CircleAlert size={15} /> Some sources did not return data. Check the warnings before deciding.</div>}
    {!!data.warnings?.length && <WarningList warnings={data.warnings} />}
    <div className="result-grid">
      <div className="result-left">
        <div className="map-frame">
          {options.length ? <MapContainer center={center} zoom={12} scrollWheelZoom={false} className="recommendation-map">
            <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <MapBounds points={options} selected={activePoint} />
            {options.map((option, index) => <Marker key={option.place_id ?? `${option.latitude}-${option.longitude}-${index}`} position={[option.latitude, option.longitude]} icon={option === activePoint ? selectedPin : pin} eventHandlers={{ click: () => setActiveOption(option) }}><Popup><strong>{option.name || 'Outdoor location'}</strong><br />{formatDateTime(option.time)}</Popup></Marker>)}
          </MapContainer> : <div className="map-unavailable"><MapPin size={22} /><strong>Map coordinates unavailable</strong><span>The API did not return verified coordinates for these options.</span></div>}
          <span className="map-label"><MapPin size={13} /> PLACES IN YOUR PLAN</span>
        </div>
        <div className="options-heading"><h3>Places & times</h3><span>{(data.alternatives?.length || 0) + 1} {((data.alternatives?.length || 0) + 1) === 1 ? 'option' : 'options'}</span></div>
        <div className="options-list"><OptionCard option={recommendation} rank={1} primary selected={activeOption === recommendation} onSelect={() => setActiveOption(recommendation)} />{(data.alternatives || []).map((option, index) => <OptionCard key={option.place_id ?? `${option.name}-${index}`} option={option} rank={index + 2} selected={activeOption === option} onSelect={() => setActiveOption(option)} />)}</div>
      </div>
      <aside className="evidence-panel">
        <div className="evidence-panel-heading"><div><span className="section-kicker">WHY THIS PLAN</span><h3>Conditions & evidence</h3></div><span className="evidence-count">{data.evidence?.length || 0}</span></div>
        {!!data.evidence?.length ? <ul className="evidence-list">{data.evidence.map((record, index) => <EvidenceItem key={`${record.claim || 'evidence'}-${index}`} record={record} />)}</ul> : <div className="evidence-empty"><Wind size={18} /><span>Evidence details were not included in this response.</span></div>}
        {hasAdvice && <div className="advice-block"><h4><ShieldAlert size={15} /> Practical notes</h4>{data.advice?.carry?.length ? <p><b>Bring:</b> {data.advice.carry.join(', ')}</p> : null}{data.advice?.watch_for?.length ? <p><b>Watch for:</b> {data.advice.watch_for.join(', ')}</p> : null}{data.advice?.avoid_if?.length ? <p><b>Consider another time if:</b> {data.advice.avoid_if.join(', ')}</p> : null}<small>General planning information, not medical advice.</small></div>}
        {!!data.data_sources?.length && <div className="source-block"><span className="section-kicker">DATA SOURCES</span><ul>{data.data_sources.map((source, index) => { const label = typeof source === 'string' ? source : source.name || source.source || 'Data provider'; const url = typeof source === 'string' ? undefined : source.url || source.source_url; return <li key={`${label}-${index}`}>{url ? <a href={url} target="_blank" rel="noreferrer">{label}<ExternalLink size={12} /></a> : label}</li> })}</ul></div>}
        <div className="traffic-note"><Wind size={14} /><span>Road proximity is a map-based proxy. Live traffic data is unavailable.</span></div>
        <p className="osm-credit">© OpenStreetMap contributors</p>
      </aside>
    </div>
  </section>
}

function WarningList({ warnings }: { warnings: string[] }) {
  return <ul className="warning-list">{warnings.map((warning, index) => <li key={`${warning}-${index}`}><CircleAlert size={14} />{warning}</li>)}</ul>
}
