# GoWise — test plan and demo checks

The system must remain truthful when data or the model is unavailable. Automated tests should use provider mocks and fixed timestamps; at least one separate manual smoke test must use real APIs before submission.

## Latest verification log — 24 October 2026

- `frontend`: `npm run build` passed.
- `backend`: `tests/test_scoring.py` passed (8 tests).
- The full backend pytest suite was attempted but did not complete in this Windows sandbox; the async/socketpair path hung without producing test results. Treat all other backend checks below as unverified.
- The deployed Gradio JSON endpoint returned a ZeroGPU quota error on the last inference attempt. No live provider-backed recommendation has been verified.
- The hosted Gradio Space does not expose the source FastAPI app's exact `/health` and `/api/recommendations` routes.

## 1. Unit tests

### Query parsing and validation
- [ ] Recognizes all ten required activity categories and common synonyms.
- [ ] Extracts stated location, radius and time range into a validated schema.
- [ ] Preserves explicitly stated profile flags (e.g. asthma, child, senior, pregnancy) without inventing a profile.
- [ ] Missing/ambiguous location leads to clarification; does not guess a user's current location.
- [ ] Invalid radius, unsupported activity, malformed timestamps and impossible intervals are rejected safely.
- [ ] Model output with invalid JSON or unsupported values is rejected and falls back safely.

### Activity rules and scoring
- [ ] Each of the ten required activities has a configuration and at least one test.
- [ ] Activity venue classification uses returned OSM tags rather than hard-coded place names.
- [ ] A venue/time pair with demonstrably unsuitable mocked weather ranks below a suitable pair for the relevant activity.
- [ ] The engine evaluates several venues and several hourly slots, not only the first venue or current hour.
- [ ] Wind direction/source bearing calculation handles 0/360-degree wraparound.
- [ ] Missing AQI/forecast/route/context remains `unknown` and is visibly disclosed; no fabricated zero or safe default.
- [ ] Scores are bounded to the documented range, factors sum/normalize consistently, and output labels the score as heuristic.
- [ ] Live traffic is never set to available using only road class or OSRM estimate.
- [ ] A source/context feature without a valid provider ID is not presented as a verified mapped place.

### Evidence and model-grounding
- [ ] Each rendered factual claim maps to a value from a provider response or deterministic calculation whose inputs are included in evidence.
- [ ] Every numeric weather/air-quality value has unit, provider and forecast/observed time where available.
- [ ] Prompt-injection or a user request to invent data does not bypass evidence constraints.
- [ ] If the SLM times out, emits malformed JSON, or is not loaded, the backend returns a clear error or deterministic evidence-based explanation.
- [ ] There is no hosted proprietary LLM API call in the production code path.

## 2. API tests

- [ ] `GET /health` returns expected JSON and model readiness; it does not leak environment variables or tokens.
- [ ] Valid `POST /api/recommendations` returns ranked recommendation, alternatives, time slots, advice, evidence, source list, warnings and coverage.
- [ ] Missing location/time follows the documented clarification behavior.
- [ ] No OSM candidates returns a no-results response instead of a fabricated place.
- [ ] Nominatim, Overpass, Open-Meteo and optional OSRM timeout/429/5xx/malformed-body failures are handled with bounded retries and clear warnings.
- [ ] Partial provider failure produces a partial result only if the scoring policy permits it; otherwise no unsupported recommendation is returned.
- [ ] Request size, search radius, forecast horizon, candidate count, concurrency and model output tokens are bounded.
- [ ] Caching reduces repeated external calls without serving incorrectly keyed locations or stale data as current.

## 3. Frontend checks

- [ ] Query form submits by click and keyboard; busy state prevents confusing duplicate submissions.
- [ ] Map markers correspond to the exact response coordinates and ranked cards.
- [ ] Each recommendation shows its candidate time, activity fit, explanation and supporting evidence.
- [ ] Data-source details, OSM attribution, forecast timestamps, live-traffic limitation and heuristic-score disclaimer are visible.
- [ ] Loading, missing-location, no-results, partial-data, backend-down, model-not-ready and mobile layouts are handled.
- [ ] User-provided personal/health details are not written to local storage, analytics or normal logs.
- [ ] API output is rendered as text; no raw model HTML is trusted.

## 4. Manual real-provider smoke test

Run these using a real browser/API deployment. Use current, returned data; do not prefill a simulated answer.

1. [ ] Ask: `Where can I go running tomorrow evening near Powai?` Verify the selected time is in the actual forecast horizon, and inspect sources.
2. [ ] Ask: `Best time this weekend for a kids' cricket match within 15 km of Whitefield?` Verify child profile caution, cricket-specific venue filtering, and multiple time/place comparisons.
3. [ ] Ask: `I have mild asthma, where's good for a morning walk near Powai in the next two days?` Verify air-quality availability/limitations and conservative advice; do not present medical certainty.
4. [ ] Ask: `Where can I take sunset photos this evening around Bandra?` Verify time and sunset/daylight data.
5. [ ] Ask a query without a place. Verify clarification instead of location guessing.
6. [ ] Temporarily block/mock one provider in a test environment. Verify partial-data warnings or a safe failure, not invented values.
7. [ ] Ask an unseen query not copied from the rulebook. Verify the output is based on a live fetch and not an example-specific hard-coded answer.

## 5. Model repository and deployment gate

- [ ] Public model repo URL opens in a clean browser without login.
- [ ] Model repo contains the required model weights or adapter, correct base-model pointer where applicable, model card describing intended use/changes, and an open licence.
- [ ] Load the model from the team's repo with Transformers `from_pretrained(...)`; do not test only the upstream vendor repository.
- [ ] Verify `MODEL_ID` in the deployed environment points to the team's repo.
- [ ] Deployed assistant runs the model locally; no hidden hosted inference endpoint is called.
- [ ] `GET /health` and `POST /api/recommendations` work from outside the deployment environment.
- [ ] Test a fresh/cold process start and a typical recommendation latency; keep the endpoint ready for the whole judging window.
- [ ] React static assets and API route are both available through the documented public URL.
- [ ] No secrets are present in git history, frontend bundles, server logs or README.

## 6. Submission audit

- [ ] `README.md` has actual code repo, public model repo, API endpoint, base model, data providers, run instructions and coding-tool disclosure.
- [ ] All ten activities are present and tested.
- [ ] Data-source attribution includes `© OpenStreetMap contributors`.
- [ ] Limitations cover traffic feed availability, weather/AQ resolution, heuristic scoring, and model/provider failure behavior.
- [ ] 4–6 slide presentation includes problem/approach, architecture, a worked example, model/fine-tuning status, and limitations.
- [ ] Demo uses an unhardcoded query and can show supporting data.
- [ ] Final submission form/link and instructions are checked on the official hackathon site.
