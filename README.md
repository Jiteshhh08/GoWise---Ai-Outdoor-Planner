# GoWise — AI Outdoor Planner

GoWise is a GeoAI Hackathon prototype that recommends **where and when** to do an outdoor activity. It combines a small open-weights language model with live geospatial, weather and air-quality data; it does not answer from model memory alone.

**Challenge:** GeoAI Hackathon 2026, CSRE, IIT Bombay  
**Official problem statement and rules:** https://geosysiot.in/geoai-hackathon/#guidelines  
**Submission deadline:** 24 October 2026, 11:59 PM IST.

## Status

- [ ] Frontend and backend run locally.
- [ ] Ten required activities tested.
- [ ] Live OSM / weather / air-quality requests verified.
- [x] Open SLM is loaded locally in the running Space (`MODEL_ID` readiness visible in the app).
- [x] Public team model repo has a model card, Apache-2.0 license, and full 1.54B weights; the Space reports the team repo loaded.
- [x] Public code repository URL added below.
- [x] Live Gradio API endpoint URL added below and smoke-tested externally (the latest call returned a structured ZeroGPU quota failure, not a live recommendation).
- [x] 4–6 slide presentation completed.

The React production build passes (`npm run build`, 24 October 2026), and the focused scoring suite passed (8 tests). The full backend suite did not complete in this Windows sandbox because an asyncio/socketpair path hung. The deployed Space's Gradio JSON endpoint is reachable, but the latest inference attempt returned a ZeroGPU quota error; this is not a successful recommendation test. The public Space also does not expose the separate FastAPI `/health` and `/api/recommendations` routes.

Do not mark an item complete until it has been tested. Replace every submission placeholder before submitting.

The API foundation, provider clients, local Transformers loader, query extractor, deterministic scoring engine, and recommendation pipeline are implemented. The public team model repository contains the full 1.54B Apache-2.0 weights and a model card; the live Space displays the team model as loaded and resolves a named Monday query to the correct upcoming local window. The Gradio HTTP endpoint returns typed JSON, but the latest inference attempt was blocked by the Space's ZeroGPU run limit; a provider-backed recommendation has not yet been verified. This checkout's separate FastAPI/Docker app still needs a local model load and cold-start check.

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
- Current deployment: Hugging Face Gradio Space with ZeroGPU. Its machine-readable HTTP endpoint is listed below. The separate React + FastAPI Docker target is not currently deployed.

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

Configure Vite's dev proxy to forward `/api` and `/health` to `http://127.0.0.1:8000`, or use a documented `VITE_API_BASE_URL`. FastAPI serves `frontend/dist` from the same origin when the built folder is present.

### Docker / Hugging Face Space

The root `Dockerfile` builds the React app and serves it through FastAPI on port `7860`. For a local container preview:

```bash
docker build -t gowise .
docker run --rm -p 7860:7860 -e MODEL_ID=Qwen/Qwen2.5-1.5B-Instruct gowise
```

The current competition deployment is the Gradio Space linked below. The Docker image remains an alternate deployment path and has not been hosted or cold-start tested. Keep the model repo public and do not bake credentials into the image.

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
| `OVERPASS_TIMEOUT_SECONDS` | Per-request timeout for the Overpass map query (default 30 seconds). |
| `OVERPASS_MAX_RETRIES` | Bounded retry count for Overpass timeouts, network errors, HTTP 429, and server errors. |
| `OVERPASS_STALE_CACHE_SECONDS` | Maximum age for cached OSM features used during an Overpass outage; stale map data is labeled and never substituted with sample values. |
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
- Team model repository: [JiteshJha/gowise-qwen2.5-1.5b-instruct](https://huggingface.co/JiteshJha/gowise-qwen2.5-1.5b-instruct) (public; full 1.54B weights, model card, Apache-2.0 license; Space reports it loaded)
- Gradio Space: [JiteshJha/goWise](https://huggingface.co/spaces/JiteshJha/goWise)
- Live structured Gradio HTTP endpoint: [`recommendation_json`](https://jiteshjha-gowise.hf.space/gradio_api/call/v2/recommendation_json) (queued two-step HTTP/SSE; verify from a separate client before submission)
- Source code repository: [Jiteshhh08/GoWise---Ai-Outdoor-Planner](https://github.com/Jiteshhh08/GoWise---Ai-Outdoor-Planner)
- Presentation (5 slides): [GoWise-GeoAI-Hackathon-2026-Submission.pptx](submission/GoWise-GeoAI-Hackathon-2026-Submission.pptx)
- Coding assistant disclosure: **OpenAI Codex (GPT-6)**. No hosted AI model is used by the running assistant; its configured small model runs locally through Transformers.

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
