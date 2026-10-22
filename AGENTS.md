# AGENTS.md — GoWise project instructions

## Mission
Build **GoWise**, a web assistant that recommends **where and when** a person should do an outdoor activity. This is a GeoAI Hackathon project, not just a weather dashboard. Read `PLAN.md`, `ARCHITECTURE.md`, `DATA_SOURCES.md`, `TESTING.md`, and the official problem statement before changing the implementation.

Official challenge page: https://geosysiot.in/geoai-hackathon/#guidelines
Submission deadline stated in the rulebook: **24 October 2026, 11:59 PM IST**.

## Hard competition constraints
- The running assistant must use a **self-run, open-weights language model with at most 3 billion parameters**.
- Publish the model on Hugging Face as a **public repository** with the required model weights or adapter, model card, and open licence. The model repository must load via `from_pretrained(...)`.
- Fetch weather, air quality, places, and geospatial context live at query time from free/open sources. There is no provided dataset.
- Support at least these ten activities: running/jogging; cycling; golf; cricket; outdoor football/five-a-side; outdoor tennis; hiking/nature walk; picnic/park outing; outdoor event/gathering; outdoor photography.
- Provide a live HTTP API endpoint, complete code repository, short README, and a **4–6 slide presentation**. Keep the deployed endpoint available during judging.
- Disclose all model(s), data sources, and AI coding tools. OpenCode may be used as a coding aid, but disclose the tool and the coding model/provider actually used.
- Never use a large hosted model (GPT-4-class, Claude, Gemini Pro, or similar) inside the running assistant. Never hard-code responses to the example questions or answer from model memory instead of fetched data.
- Credit OpenStreetMap exactly as: **© OpenStreetMap contributors**. Respect the usage policies and rate limits of every provider.

## Default technical direction
- Frontend: React + Vite + TypeScript if the repository can support it without slowing delivery; Tailwind CSS only if already installed or quick to add.
- Map: Leaflet / React Leaflet, with visible OpenStreetMap attribution.
- Backend: Python + FastAPI + Pydantic.
- Runtime model default: `Qwen/Qwen2.5-1.5B-Instruct` (1.5B parameters; Hugging Face currently marks this model Apache-2.0). Verify the model card/licence before publishing. The submission deployment must load the team's public Hugging Face repository, not silently bypass the required repo.
- Model runtime: Hugging Face Transformers `AutoTokenizer` and `AutoModelForCausalLM.from_pretrained(...)`. Load once at process start and reuse it. Do not call hosted inference APIs.
- Initial deployment target: one Hugging Face Docker Space running FastAPI and serving the built React app from the same origin, on port `7860`, unless a concrete blocker makes that impossible.
- Data candidates: Nominatim + Overpass API (OpenStreetMap), Open-Meteo Forecast API, Open-Meteo Air Quality API, and optionally OSRM for route estimates.

## Build rules
1. **Make a working end-to-end path before polishing UI.** The first vertical slice must accept a question, retrieve live data, return a grounded recommendation, and render it in the app.
2. Use deterministic code to validate inputs, fetch data, calculate candidate/time scores, and construct evidence. The SLM extracts query fields and explains the evidence; it must not invent places, forecasts, AQI, route times, or measurements.
3. Explore multiple candidate places and multiple hourly time slots. Do not recommend one candidate just because it appeared first in an API response.
4. All values that support a claim must include a source and timestamp where available. If a field is missing, stale, ambiguous, or unavailable, say so. Never silently fill it with plausible-looking sample values.
5. Distinguish live traffic from a road-class/proximity proxy. Public OSM/OSRM data must not be described as live congestion unless an actual live traffic source is integrated and disclosed.
6. If location or time is materially ambiguous, ask a concise follow-up or state what is missing. Never guess a user's location. Support a typed place name and optionally explicit coordinates.
7. Treat age, asthma, pregnancy, and other personal/health details as optional sensitive inputs. Do not persist them. Give conservative general precautions, do not diagnose or promise safety, and clearly label this as decision support rather than medical advice.
8. Add request timeouts, bounded retries, cache successful public data, and handle each provider's limits. Do not run unbounded Overpass queries or issue one request per venue when a bounded batch is possible.
9. Keep secrets out of source control. Read environment variables from `.env` locally and deployment secrets in the host dashboard. Never print or commit `HF_TOKEN` or API keys.
10. Add tests for core scoring and failure paths. Run lint/type checks/tests after meaningful changes. Fix root causes rather than hiding errors.
11. Keep `PLAN.md` checkboxes current. Update `README.md` and `DATA_SOURCES.md` when implementation changes. Do not claim a deploy, public model repo, API endpoint, or test passed unless it actually did.
12. Do not add unrelated features, user accounts, a database, fine-tuning, or complex agent frameworks before the submission requirements work.

## Quality and presentation
- Default to a clean, responsive interface: question input, quick examples, activity/time interpretation, map with candidate pins, ranked recommendation cards, evidence/source details, and visible warnings.
- Use loading, empty, partial-data, API error, and model-not-ready states.
- Keep suitability scores explainable and label them **heuristic**, not a certified health/safety score.
- Make keyboard navigation, labels, focus states, and mobile layouts usable.
- Include a demo query, but never make a hard-coded answer appear to be a live result. Tests may mock providers; production mode must call real providers.

## Done means
- All 10 required activities are represented in configuration and tested.
- The core request path uses live providers and the model is loaded locally by the backend.
- Recommendation output includes alternatives, time windows, practical advice, evidence, data sources, timestamps, and warnings for missing data.
- Frontend and backend start from documented commands; `/health` and `/api/recommendations` work.
- Public model repo, public source repo, live endpoint URL, and slide deck links are added to `README.md` before submission.
