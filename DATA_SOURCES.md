# GoWise — data sources and evidence policy

The hackathon supplies no dataset or server. Fetch data live for each query using free/open sources, disclose every source, and respect current provider terms and limits. These are the intended providers; keep provider URLs configurable so a change does not require a scoring rewrite.

## Source register

| Source | Intended use | Fields / output | Key limits and failure behavior |
|---|---|---|---|
| [Nominatim](https://nominatim.openstreetmap.org/) | Convert user-entered area/place to coordinates. | Place label, latitude/longitude, bounding box when provided, source URL. | Send an identifying User-Agent, cache geocoding results, throttle requests and obey the current public usage policy. On ambiguous/no result, ask the user to clarify; never silently choose a different city. |
| [Overpass API](https://overpass-api.de/api/interpreter) + [OpenStreetMap](https://www.openstreetmap.org/) | Discover candidate parks, pitches/courts, trails/paths and relevant outdoor venues; gather nearby road, green-cover, water and industrial/land-use context. | OSM element ID/type, tags, name where supplied, coordinates/geometry, tags used for classification, distances to context features. | Bound the geographic area, query size and request count. Cache successful results. OSM only contains mapped objects; absence of a mapped feature is not proof that the feature does not exist. Show OSM attribution. |
| [Open-Meteo Forecast API](https://open-meteo.com/en/docs) | Hourly weather forecast for candidate coordinates/times. | Available variables such as temperature/apparent temperature, precipitation probability/amount, weather code, wind speed/direction, UV, sunrise and sunset. | Fetch only needed hourly/daily fields and a bounded horizon. Store forecast-valid time separately from fetch time. Handle missing/out-of-range times as unavailable. |
| [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) | Hourly forecast for pollutants and supported indices. | Available PM2.5, PM10, ozone, nitrogen dioxide, AQI fields or other supported variables, with units as supplied. | Coverage and resolution vary by pollutant/domain; query the exact returned fields and never assume a variable exists. Forecast data is not a sensor measurement at a venue. Disclose the provider/model and forecast-valid time. |
| [OSRM routing](https://project-osrm.org/) — optional | Estimate route distance/time to shortlisted candidates. | Route distance and duration, route status, source endpoint. | Use only if available and allowed by current service policy. Public OSRM route duration is an estimate, **not live congestion**. On error, mark travel time unavailable rather than inventing one. |

The hackathon rulebook also lists OpenAQ, WAQI, OpenWeatherMap, OpenRouteService, Sunrise-Sunset API, Open-Elevation/OpenTopoData, Data.gov.in, CPCB and IMD as possible alternatives. Add any alternative actually used to this table; do not list a service as used when the code never calls it.

## OSM features to inspect

Use tags returned by Overpass rather than relying only on names. Include relevant combinations of:

- **Activity venues:** leisure parks, recreation grounds, pitches/courts and sports tags; golf facilities where mapped; pathways/trails/natural areas when appropriate.
- **Road exposure/access:** nearby `highway` classes, distance to primary/secondary/trunk/motorway roads, and road density in a bounded buffer.
- **Green cover:** parks, forest/wood, grass/green areas and tree/green tags when mapped.
- **Water:** mapped water bodies, waterways and coastlines where applicable.
- **Industrial/context:** `landuse=industrial`, mapped industrial facilities, and other relevant land-use tags.

Record the actual OSM tags and source element IDs used to justify a context statement. Do not infer the existence of a feature merely because its category is missing.

## Weather and wind context

- Use forecast data for the requested hour, not a current reading presented as tomorrow's forecast.
- Use wind direction consistently with the provider's convention (meteorological direction usually means **where wind comes from**; confirm the chosen field's definition). If an industrial/road feature lies upwind within the configured sector, show it as a *potential context flag*, not a claim that it caused a measured pollution value.
- Do not make medical claims or promise that a condition is safe. For explicitly stated asthma, pregnancy, children or older adults, use conservative flags and explain which observed/forecast data caused the warning.
- Use units returned/documented by the provider and normalize them in one service layer.

## Live traffic rule

The initial source set does **not** provide a guaranteed live traffic feed. Road proximity/classification can be used as a disclosed proxy. If the optional OSRM service is used, call the result a route estimate, not live traffic. The API should expose `live_traffic` as unavailable unless a real, free/open live traffic source is added, implemented, tested and disclosed.

## Provenance data contract

Each evidence record should include as many of these fields as applicable:

```json
{
  "claim": "temperature at a shortlisted venue and hour",
  "value": "actual value returned by provider",
  "unit": "provider unit",
  "source": "Open-Meteo Forecast API",
  "source_url": "actual source/API URL used",
  "observed_for": "forecast-valid ISO-8601 timestamp",
  "fetched_at": "fetch ISO-8601 timestamp",
  "location": {"latitude": 0.0, "longitude": 0.0}
}
```

The values above are a schema example only. Runtime output must carry real values. Include source URLs/IDs for OSM features, and distinguish a provider's forecast timestamp from the time your server fetched it.

## Caching and resilience

- Add a short, configurable TTL for weather/air-quality calls keyed by rounded coordinates, timezone and forecast horizon.
- Cache geocoding/place results with provider-aware TTLs; retain an update/fetch timestamp so stale data can be disclosed.
- Set timeouts, bounded retries/backoff, and clear per-provider failure messages.
- Do not treat cache expiry or provider failure as proof that a place/period is safe.
- When one provider fails, use only the remaining real data, reduce coverage/confidence, and display the missing source; if required minimum inputs are absent, ask for a different query or return no recommendation.

## Required disclosure in the UI and README

1. Name each source used for the current response.
2. Credit OSM as **© OpenStreetMap contributors**.
3. Label forecast data as forecast, and include its valid time and fetch time where available.
4. State when air quality, traffic, routing, a feature layer, or a requested time is unavailable.
5. Disclose all models, data sources and AI coding tools actually used.
