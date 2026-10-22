# GoWise — architecture

## 1. System shape

Use one source repository with a React frontend and FastAPI backend. In production, build React into static assets and serve them from FastAPI in the same container/origin; this reduces CORS and deployment complexity. Use a Docker-based Hugging Face Space on port `7860` unless a tested alternative is required.

```text
Browser (React + Leaflet)
        |
        | POST /api/recommendations { question }
        v
FastAPI + Pydantic
  |-- SLM query extraction (local Transformers model)
  |-- validation / clarification
  |-- Nominatim geocoding
  |-- Overpass: venues + OSM context
  |-- Open-Meteo: hourly weather + air quality
  |-- optional OSRM: route-time estimate
  |-- candidate x hourly-slot scoring (deterministic code)
  |-- SLM constrained explanation, grounded in scored evidence
  v
Structured response: best option + alternatives + advice + evidence + warnings
```

## 2. Suggested repository layout

```text
.
├── AGENTS.md
├── PLAN.md
├── ARCHITECTURE.md
├── README.md
├── DATA_SOURCES.md
├── TESTING.md
├── frontend/
│   ├── src/
│   │   ├── components/       # Query form, map, ranked cards, evidence panel
│   │   ├── api/              # Typed API client
│   │   ├── pages/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app, health, static build mount
│   │   ├── api/               # Route handlers
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── model_service.py
│   │   │   ├── geocoding.py
│   │   │   ├── places.py
│   │   │   ├── weather.py
│   │   │   ├── air_quality.py
│   │   │   └── routing.py
│   │   ├── engine/             # activity rules, feature extraction, scoring
│   │   ├── prompts/
│   │   └── config.py
│   ├── tests/
│   └── requirements.txt
├── scripts/                   # model repo publish/check scripts, if needed
├── Dockerfile
├── .env.example
└── .gitignore
```

Adjust this to the actual repository if a similar structure already exists. Do not generate empty modules just to match the diagram.

## 3. Request pipeline

1. **Parse:** send the user's free-form question to the local SLM and request structured JSON: activity, place/area, radius, requested time interval, and only the personal details the user actually stated.
2. **Validate:** validate supported activity, time bounds, coordinate/radius bounds, and output schema. If location or time is too ambiguous, return a clarification state. Never infer exact user location from browser metadata.
3. **Geocode:** resolve the place name using Nominatim. Cache successful lookups and obey its current usage policy.
4. **Discover candidates:** query Overpass once per bounded area where possible. Keep venue IDs, names, coordinates, OSM tags and source links. Filter to the appropriate type for the requested activity.
5. **Fetch time-dependent data:** retrieve Open-Meteo hourly weather and air quality for candidate points or a justified representative coordinate. Cache by rounded coordinates and valid time. Record actual fetch timestamps and forecast timestamps separately.
6. **Build local context:** for each venue, calculate distances to selected road classes, industrial/land-use features, water bodies and green areas. Calculate whether mapped potential sources lie in the wind-from sector of the candidate using the forecast wind direction. Treat this as a crude exposure indicator, not a pollutant-dispersion model.
7. **Enumerate venue/time pairs:** compare multiple venues against multiple hourly time slots inside the user-requested interval.
8. **Score deterministically:** activity-specific rules compute a transparent heuristic score and factor breakdown. A missing input is `unknown`, not a fabricated zero or a silently assumed safe value. If a factor is unavailable, disclose it and adjust score coverage consistently.
9. **Explain with the SLM:** provide only the structured facts, score factors and source references to the model. Require a schema-constrained result; reject or sanitize unsupported values. If the model fails, render a deterministic explanation from the same evidence.
10. **Respond:** return the preferred place/time, alternatives, practical precautions, evidence records, sources, warnings, and a coverage/uncertainty indicator.

## 4. Runtime model

- Default candidate: `Qwen/Qwen2.5-1.5B-Instruct` (1.5B parameters; its Hugging Face listing reports Apache-2.0). Recheck the model card and licence before submission.
- Load with Transformers `AutoTokenizer.from_pretrained(MODEL_ID)` and `AutoModelForCausalLM.from_pretrained(MODEL_ID, ...)`; load once per backend process, not per request.
- During local development `MODEL_ID` may point to the upstream base model. For submission, point it at the team's public model repository and verify that repository actually satisfies the rulebook's weights/adapter, model-card, licence and `from_pretrained(...)` requirements.
- Do not use hosted inference APIs or remote proprietary LLMs in the runtime. No fine-tuning is required for the MVP.
- Use short context and output limits, deterministic JSON decoding where practical, explicit timeouts, and a deterministic fallback. Never let the SLM independently invent weather or places.

## 5. API contract

### `GET /health`
Return basic health, application version, and model readiness. Do not expose tokens, full environment variables, or sensitive deployment details.

### `POST /api/recommendations`
Request:

```json
{
  "question": "Where can I go running tomorrow evening near Powai?"
}
```

Successful response shape (values below are **schema examples only**, not live claims):

```json
{
  "status": "ok",
  "interpreted_query": {
    "activity": "running",
    "location_label": "Powai",
    "radius_km": 10,
    "start_time": "ISO-8601 timestamp",
    "end_time": "ISO-8601 timestamp",
    "profile_flags": []
  },
  "recommendation": {
    "place_id": "provider-backed ID",
    "name": "provider-backed name",
    "latitude": 0.0,
    "longitude": 0.0,
    "time": "ISO-8601 timestamp",
    "suitability_score": 0,
    "score_factors": [],
    "explanation": "Evidence-based explanation"
  },
  "alternatives": [],
  "advice": {
    "carry": [],
    "watch_for": [],
    "avoid_if": []
  },
  "evidence": [
    {
      "claim": "temperature at candidate time",
      "value": "provider value and unit",
      "source": "Open-Meteo Forecast API",
      "source_url": "actual endpoint or provider URL",
      "observed_for": "forecast timestamp",
      "fetched_at": "actual fetch timestamp"
    }
  ],
  "data_sources": [],
  "warnings": [],
  "coverage": 0.0
}
```

The API must return actual values, never the placeholders shown in this schema. Use a different status (for example `needs_clarification` or `partial`) when required inputs/data are missing; document HTTP status behavior. Keep the frontend types in sync with Pydantic schemas.

## 6. Geospatial/temporal features

Support at minimum:
- Venue-activity match from live OSM tags and name/tag classification.
- Hourly weather: temperature/apparent temperature where available, precipitation probability/precipitation, wind speed/direction, UV and weather code as appropriate.
- Air-quality fields such as PM2.5/PM10 when the provider supplies them.
- Daylight from forecast sunrise/sunset or a documented open API.
- Green cover/parks, water bodies, industrial land use, and road classes/proximity.
- Wind direction relative to mapped potential pollutant sources.
- Accessibility/route estimate only when routing data is available.

**Traffic limitation:** OSM road class and proximity are not real-time traffic. If no actual free/open live traffic source is added, say `live_traffic: unavailable`, use road class only as a proxy, and disclose this in the response and README. Public OSRM route time must be labelled as an estimate and not live congestion.

## 7. Security, reliability and privacy

- Use a shared HTTP client with timeout, bounded retry/backoff, and a small cache with provider-aware TTL.
- Bound radius, query extent, Overpass response size, number of candidate venues, forecast horizon and model output tokens.
- Do not call external APIs from the frontend directly; keep provider logic in the backend so failures and source metadata are consistent.
- Do not store user questions or health/profile fields unless an explicit need is justified. Avoid request-body logging.
- Keep Hugging Face tokens and any optional credentials in deployment secrets or local `.env`; commit only `.env.example`.
- Render third-party content as text. Validate coordinates and all model-generated structured output.
