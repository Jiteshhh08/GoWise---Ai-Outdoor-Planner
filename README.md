# GoWise — AI Outdoor Planner

GoWise is a GeoAI Hackathon prototype that recommends **where and when** to do an outdoor activity. It combines a small open-weights language model with live geospatial, weather and air-quality data; it does not answer from model memory alone.

**Challenge:** GeoAI Hackathon 2026, CSRE, IIT Bombay  
**Official problem statement and rules:** https://geosysiot.in/geoai-hackathon/#guidelines  
**Submission deadline:** 24 October 2026, 11:59 PM IST.

## Status

- [ ] Frontend and backend run locally.
- [ ] Ten required activities tested.
- [ ] Live OSM / weather / air-quality requests verified.
- [ ] Open SLM loads locally and is used by the running assistant.
- [ ] Public Hugging Face model repository verified with `from_pretrained(...)`.
- [ ] Public code repository URL added below.
- [ ] Live API endpoint URL added below and tested externally.
- [ ] 4–6 slide presentation completed.

Do not mark an item complete until it has been tested. Replace every submission placeholder before submitting.

The API foundation, provider clients, local Transformers loader, query extractor, deterministic scoring engine, and recommendation pipeline are implemented. The endpoint uses live provider calls at request time and returns no recommendation if forecast weather is unavailable. Model weights are not downloaded in this workspace, and a real end-to-end call against upstream providers has not yet been verified. The API therefore remains unready until its local model loads; it returns HTTP 503 rather than sample recommendations during model startup or when model loading fails.

## Features

- Free-form requests for running/jogging, cycling, golf, cricket, outdoor football/five-a-side, outdoor tennis, hiking/nature walks, picnics/park outings, outdoor events/gatherings, and outdoor photography.
- Live geocoding and outdoor-place discovery.
- Hourly weather, air-quality data where available, and mapped geospatial context.
- Ranked combinations of places and time slots, with alternatives and practical advice.
- A map plus visible supporting evidence, source labels, timestamps, limitations and missing-data warnings.

The scoring pipeline compares multiple tag-matched OSM candidates and hourly forecast times. Scores are heuristic. AQ/model gaps lower coverage and produce warnings; an absent weather forecast prevents a recommendation. Traffic is not live: mapped road proximity is only a proxy.

## Architecture

- Frontend: React + Vite + TypeScript, Leaflet.
- Backend: Python + FastAPI + Pydantic.
- Runtime SLM: default `Qwen/Qwen2.5-1.5B-Instruct`, loaded locally through Hugging Face Transformers. Verify the current model card and licence before release.
- Data: OpenStreetMap through Nominatim and Overpass; Open-Meteo Forecast and Air Quality APIs; optional OSRM route estimates.
- Deployment target: a Hugging Face Docker Space serving both the built frontend and FastAPI on port `7860`.

See `ARCHITECTURE.md` for the API and data flow and `DATA_SOURCES.md` for source/failure policies.

## Requirements

- Python 3.11+ recommended.
- Node.js LTS and npm.
- A machine with enough memory for the selected Transformers model. The first model download can be several GB and first load is slower than subsequent requests.
- A Hugging Face account/token only if you are publishing the required public model repository. Never commit the token.

## Local development

Commands assume the directories described in `ARCHITECTURE.md`; adapt only if the repository already has a different valid structure.

### 1. Configure the backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

Copy the root `.env.example` to `backend/.env` (or configure the same values in your shell). For initial local development you may set `MODEL_ID=Qwen/Qwen2.5-1.5B-Instruct`. The **submission deployment must use the team's public Hugging Face model repository** and meet all rulebook requirements.

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend endpoints:
- `GET http://127.0.0.1:8000/health`
- `POST http://127.0.0.1:8000/api/recommendations`
- API docs during development: `http://127.0.0.1:8000/docs`

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"question":"Where can I go running tomorrow evening near Powai?"}'
```

### 2. Configure the React frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Configure Vite's dev proxy to forward `/api` and `/health` to `http://127.0.0.1:8000`, or use a documented `VITE_API_BASE_URL`. In production, prefer serving `frontend/dist` from FastAPI to keep the API and UI on the same origin.

### 3. Run checks

See `TESTING.md` for unit, API, UI and live-provider checks. Use provider mocks for automated tests; verify at least one real query manually before the demo.

## Environment variables

Keep local secrets in `.env` and deployment secrets in the host's secret settings. Never commit tokens.

| Variable | Purpose |
|---|---|
| `MODEL_ID` | Model repo loaded by Transformers. Development can use upstream Qwen; submission must use the team's public model repo. |
| `HF_TOKEN` | Needed only for authenticated Hugging Face operations, such as publishing. Do not expose to frontend or logs. |
| `PORT` | HTTP port provided by deployment platform; Docker Space defaults to `7860`. |
| `CACHE_TTL_SECONDS` | Cache lifetime for eligible provider responses. |
| `REQUEST_TIMEOUT_SECONDS` | External API request timeout. |
| `MAX_SEARCH_RADIUS_KM` | Hard cap on user-requested search radius. |
| `DEFAULT_SEARCH_RADIUS_KM` | Search distance used when the user leaves radius unspecified. |
| `DEFAULT_TIMEZONE` | Local reference timezone for interpreting relative dates. |

Add all implemented variables to `.env.example` and validate them at startup.

## Data and attribution

- Nominatim: geocoding.
- Overpass API / OpenStreetMap: venues and nearby mapped roads, land use, green areas, water and industrial features.
- Open-Meteo Forecast API: hourly forecast/daylight variables.
- Open-Meteo Air Quality API: available hourly pollutants/indices.
- OSRM, only if enabled: route-time estimate. Do not describe this as live traffic.

Credit OSM as **© OpenStreetMap contributors**. Check `DATA_SOURCES.md` for URLs, limitations and failure behavior. Never fabricate a venue, forecast, AQI, observation, timestamp or travel duration.

## Model and required publication

Default model: `Qwen/Qwen2.5-1.5B-Instruct` (1.5B; the Hugging Face listing currently reports Apache-2.0). Review its current model card/licence before use. No fine-tuning is necessary for the MVP.

The hackathon requires a **public team model repository** on Hugging Face with the required weights or adapter, a model card and an open licence; it must load with `from_pretrained(...)`. An upstream model page by itself is not proof that this deliverable has been completed. Test loading from the team's repository and record the exact model ID below.

- Base model: `Qwen/Qwen2.5-1.5B-Instruct` (verify before submission)
- Team model repository: **TODO — add actual public Hugging Face model URL**
- Live API endpoint: **TODO — add actual deployed `/api/recommendations` URL**
- Source code repository: **TODO — add actual public Git repository URL**
- Presentation (4–6 slides): **TODO — add actual URL or location**
- Coding assistant disclosure: **OpenCode; fill in the exact coding model/provider used**

Never claim a resource is public or online until it has been verified from a clean browser/session.

## Known limitations to disclose

- Road class/proximity is not live traffic. If no actual free/open live traffic feed is available, report live traffic as unavailable and explain the road proxy.
- Wind alignment with nearby mapped industrial/road features is a rough contextual indicator, not a pollutant-dispersion model.
- Open-Meteo air-quality values are modelled forecasts with provider-specific spatial resolution; they are not measurements at the exact park entrance.
- Suitability scores are heuristic and not scientifically validated medical or safety ratings.
- Missing/failed provider data must be shown as unavailable, not treated as safe or replaced with invented data.

## Submission checklist

- [ ] Deployed API responds to an external request and stays reachable during judging.
- [ ] Public model repo has valid licence and model card and loads by `from_pretrained(...)`.
- [ ] Public code repo contains the complete source and setup instructions.
- [ ] This README lists the actual model, data sources, API URL, and coding-tool disclosure.
- [ ] 4–6 slide deck covers problem/approach, architecture, worked example, model/fine-tuning, and limitations.
- [ ] Live demo uses fetched data and a non-hard-coded query.
