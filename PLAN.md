# GoWise — execution plan

**Target:** a credible, demonstrable GeoAI outdoor-planning assistant. Work in the order below; do not start with visual polish.

Official brief: https://geosysiot.in/geoai-hackathon/#guidelines  
**Deadline:** 24 October 2026, 11:59 PM IST.

## Phase 0 — repository and scope
- [x] Inspect the existing repository before changing files; retain working code and package-lock files.
- [x] Create a short task list and agree on a minimal React + FastAPI layout.
- [x] Add `.env.example`, `.gitignore`, dependency manifests, and health endpoint.
- [x] Define Pydantic request/response schemas before building UI.

**Exit check:** frontend and backend start locally; `GET /health` responds.

## Phase 1 — live data, no LLM yet
- [x] Implement Nominatim place-name geocoding with user-agent, timeout, bounded retry, and cache.
- [x] Implement a bounded Overpass query around a resolved coordinate/radius for candidate parks, pitches/courts, trails/paths, and relevant outdoor venues.
- [x] Fetch hourly weather and daylight variables from Open-Meteo Forecast API.
- [x] Fetch hourly PM2.5/PM10 and relevant air-quality variables from Open-Meteo Air Quality API when available.
- [x] Collect OSM context around each candidate: green cover, nearby roads/road class, water bodies, and industrial/land-use features.
- [ ] Add an optional OSRM route estimate only if it can be done reliably within time. Never label it as live traffic.
- [ ] Return a structured data bundle with provider names, source URLs, fetch times, and partial-data warnings.

**Exit check:** one location query returns actual current API responses; provider failure is shown honestly rather than replaced with fake values.

## Phase 2 — deterministic decision engine
- [x] Configure all ten required activities in one activity-rules module.
- [x] Normalize units and align venue data with hourly forecast slots.
- [x] Score multiple venue/time combinations with transparent, configurable rules for activity fit, weather, air quality, daylight, greenery, road exposure, wind-aligned potential sources, and accessibility where available.
- [ ] Version the scoring rules and expose score factors; label score as a heuristic, not a validated medical or safety metric.
- [x] Handle missing AQI/forecast/OSM data by lowering coverage/confidence and explaining the gap; do not invent a substitute measurement.
- [x] Produce ranked alternatives, not just one result.

**Exit check:** deterministic tests verify ranking, time-slot selection, activity constraints, and missing-data behavior without needing a live LLM.

## Phase 3 — SLM integration and grounded response
- [x] Implement a local Transformers loader configured for the open-weights `Qwen/Qwen2.5-1.5B-Instruct` model (model weights and runtime load remain unverified).
- [x] Implement query extraction to a validated JSON object: activity, location, radius, time range, and explicitly stated profile details.
- [x] If required fields are missing/ambiguous, ask for clarification instead of guessing.
- [ ] Publish a public team Hugging Face model repository that meets the rulebook (weights or adapter as required, model card, open licence, and successful `from_pretrained(...)` load). Do not mark this done merely because the upstream base model is public.
- [x] Implement a second, constrained generation step that selects only supplied evidence IDs; validate the IDs and render the explanation deterministically from provider records with a safe fallback.
- [ ] Never call a hosted LLM/inference API in production.

**Exit check:** logs make it clear the model ran locally; outputs do not contain unsupported factual claims.

## Phase 4 — React interface
- [x] Build a responsive question input with a few example prompts.
- [x] Display parsed activity/location/time and a clear missing-information state.
- [x] Display ranked place/time cards and an interactive Leaflet map with candidate pins.
- [x] Show live weather/AQ values only with units, timestamps, and source labels.
- [x] Show practical advice: what to carry, what to watch for, and conditions/times to avoid.
- [x] Show data-source coverage, uncertainty, OpenStreetMap attribution, and route/traffic limitations.
- [x] Implement loading, no-results, timeout, partial-data, and model-unavailable states.

**Exit check:** a user can enter an unseen free-form question and inspect the evidence behind the recommendation.

## Phase 5 — deployment and submission assets
- [x] Build the React app in the Docker image and serve it from FastAPI so frontend and API share one origin.
- [ ] Deploy as a Hugging Face Docker Space (or document a concrete tested alternative); expose `GET /health` and `POST /api/recommendations`.
- [x] Configure model repo ID and deployment environment variables without committing secrets (Space model readiness verified; no secret values committed).
- [ ] Test the public API from a separate network/session and test a cold start. Keep the endpoint available throughout judging.
- [ ] Verify the model repo is public, has an open licence/model card, and loads through `from_pretrained(...)`.
- [x] Update `README.md` with actual code-repo URL, model-repo URL, live endpoint URL, base model, data sources, and AI coding-tool disclosure.
- [x] Prepare a five-slide presentation covering the request flow, architecture, scoring/evidence, and verified/unverified status. Add a real live worked example after provider and model checks pass.
- [ ] Complete `TESTING.md`; run all commands and record what actually passed.

**Exit check:** all mandatory deliverables are real links, not placeholders; one live query works end to end.

## Scope cuts if behind schedule
Cut in this order: decorative animation, user accounts, saved history, elaborate charts, turn-by-turn directions, extra activities beyond the required ten. Do **not** cut: live data, the ten activity configurations, the self-run open SLM, evidence/limitations, public model repo, HTTP API, source attribution, or the 4–6 slide presentation.

## Definition of an honest demo
- Use a query not hard-coded specifically for the presentation.
- Show the provider-backed venue and hourly weather/AQ values that were fetched during the request.
- Show at least one alternative and explain why it scored lower using real fields.
- Explicitly disclose if real-time traffic data is unavailable; do not present road proximity as live congestion.
- Demonstrate a missing-location or upstream-API failure safely.
