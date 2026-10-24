from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import settings
from ..engine.activities import ACTIVITY_RULES, classify_venue
from ..engine.scoring import GeoFeature, score_candidate_time
from ..model.local_model import LocalLanguageModel, ModelNotReadyError
from ..model.evidence_explanation import EvidenceExplainer
from ..model.query_extraction import QueryClarification, QueryExtractionError, QueryExtractor
from ..providers.geocoding import GeocodedPlace, NominatimGeocoder
from ..providers.http import ProviderError
from ..providers.meteo import AIR_QUALITY_NAME, WEATHER_NAME, OpenMeteoAirQuality, OpenMeteoForecast
from ..providers.osm import OSMFeature, OSMSearchResult, OverpassPlaces
from ..schemas import (
    Advice,
    DataSource,
    EvidenceRecord,
    InterpretedQuery,
    RecommendationOption,
    RecommendationResponse,
)

OSM_NAME = "Overpass API / OpenStreetMap"


def _utc(value: datetime | None) -> datetime | None:
    return value.astimezone(timezone.utc) if value and value.tzinfo else value


def _feature_name(feature: OSMFeature) -> str:
    return feature.tags.get("name") or feature.tags.get("official_name") or feature.tags.get("leisure", "Mapped outdoor place").replace("_", " ").title()


def _hour_at(hours: list[dict[str, Any]], when: datetime, tolerance_seconds: int = 60) -> dict[str, Any] | None:
    eligible = [hour for hour in hours if isinstance(hour.get("time"), datetime)]
    if not eligible:
        return None
    match = min(eligible, key=lambda hour: abs((hour["time"] - when).total_seconds()))
    return match if abs((match["time"] - when).total_seconds()) <= tolerance_seconds else None


def _units(weather: dict[str, Any] | None, air: dict[str, Any] | None) -> dict[str, str]:
    units: dict[str, str] = {}
    for payload in (weather, air):
        if payload:
            units.update({str(key): str(value) for key, value in payload.get("hourly_units", {}).items()})
    return units


def _result_evidence(
    venue: OSMFeature,
    when: datetime,
    weather_hour: dict[str, Any],
    air_hour: dict[str, Any] | None,
    weather: dict[str, Any],
    air: dict[str, Any] | None,
    osm_result: OSMSearchResult,
) -> list[EvidenceRecord]:
    location = {"latitude": venue.latitude, "longitude": venue.longitude}
    records: list[EvidenceRecord] = []
    tags = venue.tags
    tag_value = tags.get("sport") or tags.get("leisure") or tags.get("tourism") or tags.get("highway")
    if tag_value:
        records.append(EvidenceRecord(
            claim=f"{_feature_name(venue)}: mapped place activity tag", value=tag_value, source=OSM_NAME,
            source_url=venue.source_url, fetched_at=datetime.fromisoformat(osm_result.fetched_at), location=location,
        ))
    for payload, hour, keys in (
        (weather, weather_hour, ("temperature_2m", "apparent_temperature", "precipitation_probability", "precipitation", "weather_code", "wind_speed_10m", "wind_direction_10m", "uv_index")),
        (air, air_hour, ("pm2_5", "pm10", "european_aqi", "us_aqi", "ozone", "nitrogen_dioxide")),
    ):
        if not payload or not hour:
            continue
        values = hour.get("values", {})
        for key in keys:
            value = values.get(key)
            if value is None:
                continue
            records.append(EvidenceRecord(
                claim=f"{_feature_name(venue)}: {key.replace('_', ' ').title()}", value=value,
                unit=_units(weather if payload is weather else None, air if payload is air else None).get(key),
                source=payload["source"], source_url=payload["source_url"],
                observed_for=hour["time"], fetched_at=payload["fetched_at"],
                location={"latitude": payload.get("latitude") or venue.latitude, "longitude": payload.get("longitude") or venue.longitude},
            ))
    return records


class RecommendationService:
    def __init__(self, client: httpx.AsyncClient, model: LocalLanguageModel) -> None:
        self.model = model
        self.extractor = QueryExtractor(model)
        self.explainer = EvidenceExplainer(model)
        self.geocoder = NominatimGeocoder(client)
        self.places = OverpassPlaces(client)
        self.forecast = OpenMeteoForecast(client)
        self.air_quality = OpenMeteoAirQuality(client)

    async def recommend(self, question: str) -> RecommendationResponse:
        try:
            query = await self.extractor.extract(question)
        except ModelNotReadyError:
            raise
        except (QueryExtractionError, ValueError) as error:
            return RecommendationResponse(
                status="data_unavailable",
                clarification_question="I couldn't reliably interpret that request. Please include an activity, a typed place, and an upcoming time window.",
                warnings=[str(error)],
            )
        if isinstance(query, QueryClarification):
            clarification_status = "unsupported_activity" if any("outside the ten configured" in warning for warning in query.warnings) else "needs_clarification"
            return RecommendationResponse(status=clarification_status, clarification_question=query.question, warnings=query.warnings)

        parsed = InterpretedQuery(
            activity=query.activity, location_label=query.location_label, radius_km=query.radius_km,
            start_time=query.start_time, end_time=query.end_time, profile_flags=query.profile_flags,
        )
        warnings = list(query.warnings)
        sources: dict[str, DataSource] = {}
        try:
            geocoded = await self.geocoder.search(query.location_label, limit=3)
        except ProviderError as error:
            return self._unavailable(parsed, warnings, f"Location lookup failed: {error}")
        if not geocoded:
            return RecommendationResponse(status="no_results", interpreted_query=parsed, clarification_question="I couldn't find that place. Could you try a more specific nearby town or area?", warnings=warnings + ["Nominatim returned no matching location."])
        similarly_ranked = (
            len(geocoded) > 1
            and geocoded[0].importance is not None
            and geocoded[1].importance is not None
            and geocoded[0].importance - geocoded[1].importance < 0.05
        )
        if similarly_ranked:
            return RecommendationResponse(status="needs_clarification", interpreted_query=parsed, clarification_question="I found more than one likely match. Could you include the city or region?", warnings=warnings + ["Location results were similarly ranked; no location was selected."])
        place = geocoded[0]
        sources["nominatim"] = DataSource(name="Nominatim", url="https://nominatim.openstreetmap.org/", note="Geocoded the typed place.")
        try:
            osm_result = await self.places.search(place.latitude, place.longitude, query.radius_km)
        except ProviderError as error:
            return self._unavailable(parsed, warnings, f"Mapped-place lookup failed: {error}", sources.values())
        sources["osm"] = DataSource(
            name=OSM_NAME,
            url=osm_result.source_url,
            note=(
                f"Cached map data fetched at {osm_result.fetched_at}; place details may be out of date. © OpenStreetMap contributors"
                if osm_result.stale
                else "© OpenStreetMap contributors"
            ),
        )
        if osm_result.stale:
            warnings.append(
                f"Overpass did not respond; using cached OpenStreetMap features fetched at {osm_result.fetched_at}. Map details may be out of date."
            )
        matched = [feature for feature in osm_result.features if classify_venue(query.activity, feature.tags) and feature.latitude is not None and feature.longitude is not None]
        candidates = _diverse_candidates(matched, place.latitude, place.longitude, settings.max_candidates)
        if not candidates:
            return RecommendationResponse(status="no_results", interpreted_query=parsed, clarification_question="No mapped places with matching activity tags were found in that area. Try a wider nearby area.", data_sources=list(sources.values()), warnings=warnings + ["OSM place matching uses mapped tags; names alone are not treated as proof of suitability."])

        points = [(candidate.latitude, candidate.longitude) for candidate in candidates if candidate.latitude is not None and candidate.longitude is not None]
        weather_payload: list[dict[str, Any]] = []
        air_payload: list[dict[str, Any]] = []
        provider_errors: list[str] = []
        weather_task = self.forecast.fetch_many(points)
        air_task = self.air_quality.fetch_many(points)
        weather_result, air_result = await asyncio.gather(weather_task, air_task, return_exceptions=True)
        if isinstance(weather_result, Exception):
            provider_errors.append(f"Weather data is unavailable: {weather_result}")
        else:
            weather_payload = weather_result
            sources["weather"] = DataSource(name=WEATHER_NAME, url=settings.weather_url, note="Hourly forecast; values are modelled for forecast grid cells.")
        if isinstance(air_result, Exception):
            provider_errors.append(f"Air-quality data is unavailable: {air_result}")
        else:
            air_payload = air_result
            sources["air"] = DataSource(name=AIR_QUALITY_NAME, url=settings.air_quality_url, note="Modelled regional forecast, not a sensor reading at the exact venue.")

        ranked: list[tuple[float, OSMFeature, datetime, dict[str, Any], dict[str, Any] | None, Any, dict[str, Any] | None, dict[str, Any]]] = []
        for index, venue in enumerate(candidates):
            weather = weather_payload[index] if index < len(weather_payload) else None
            air = air_payload[index] if index < len(air_payload) else None
            if not weather:
                continue
            context = [GeoFeature(f.feature_id, f.tags, f.latitude, f.longitude, f.source_url) for f in osm_result.features]
            for epoch in range(int(query.start_time.timestamp() // 3600), int(query.end_time.timestamp() // 3600) + 1):
                when = datetime.fromtimestamp(epoch * 3600, timezone.utc)
                if when < query.start_time or when > query.end_time:
                    continue
                weather_hour = _hour_at(weather["hourly"], when)
                if not weather_hour or not any(value is not None for value in weather_hour.get("values", {}).values()):
                    continue
                air_hour = _hour_at(air["hourly"], when, tolerance_seconds=90 * 60) if air else None
                daylight = next((day for day in weather["daily"] if day.get("sunrise") and day.get("sunset") and day["sunrise"].date() == when.date()), {})
                venue_geo = GeoFeature(venue.feature_id, venue.tags, venue.latitude, venue.longitude, venue.source_url)
                evaluation = score_candidate_time(query.activity, venue_geo, when, weather_hour, air_hour, context, daylight.get("sunrise"), daylight.get("sunset"))
                ranked.append((evaluation.suitability_score, venue, when, weather_hour, air_hour, evaluation, weather, air))
        if not ranked:
            return RecommendationResponse(status="data_unavailable", interpreted_query=parsed, clarification_question="The providers did not return usable hourly weather for the requested window. Try a nearer date or another area.", data_sources=list(sources.values()), warnings=warnings + provider_errors + ["No forecast value was substituted."])

        ranked.sort(key=lambda item: item[0], reverse=True)
        # Prefer distinct places in the alternatives while retaining distinct time slots when only one place exists.
        selected = [ranked[0]]
        seen = {(ranked[0][1].feature_id, ranked[0][2])}
        for item in ranked[1:]:
            if (item[1].feature_id, item[2]) not in seen and (item[1].feature_id not in {row[1].feature_id for row in selected} or len(selected) >= len(candidates)):
                selected.append(item)
                seen.add((item[1].feature_id, item[2]))
            if len(selected) >= 4:
                break
        options: list[RecommendationOption] = []
        for score, venue, when, weather_hour, _air_hour, evaluation, _weather, _air in selected:
            factors = evaluation.score_factors
            weather_factor = next((factor for factor in factors if factor.name == "weather"), None)
            air_factor = next((factor for factor in factors if factor.name == "air_quality"), None)
            explanation_parts = []
            if weather_factor and weather_factor.value:
                explanation_parts.append(f"Forecast: {weather_factor.value}.")
            if air_factor and air_factor.value:
                explanation_parts.append(f"Air quality: {air_factor.value}.")
            explanation_parts.append("Suitability score is a heuristic based on available data.")
            options.append(RecommendationOption(
                place_id=venue.feature_id, name=_feature_name(venue), latitude=venue.latitude, longitude=venue.longitude,
                time=when, suitability_score=score, score_factors=factors,
                explanation=" ".join(explanation_parts),
            ))

        best = selected[0]
        evidence: list[EvidenceRecord] = []
        for _score, venue, when, weather_hour, air_hour, _evaluation, weather, air in selected:
            evidence.extend(_result_evidence(venue, when, weather_hour, air_hour, weather, air, osm_result))
        evidence_summary, explanation_model_ready = await self.explainer.summarize(query.activity, evidence)
        advice = _advice(best[3], best[4], best[6], best[7], query.profile_flags)
        all_warnings = warnings + provider_errors + list(best[5].warnings)
        if not explanation_model_ready:
            all_warnings.append("The local model could not prioritize the evidence; provider facts are shown using the deterministic fallback renderer.")
        if query.profile_flags:
            all_warnings.append("Optional personal context was considered only as a conservative reminder; this is not medical advice and the details are not stored.")
        if len(candidates) == 1:
            all_warnings.append("Only one mapped place matched; time slots were compared at that place.")
        coverage = best[5].coverage
        return RecommendationResponse(
            status="partial" if provider_errors or osm_result.stale or coverage < 0.95 else "ok",
            interpreted_query=parsed, recommendation=options[0], alternatives=options[1:], advice=advice,
            evidence_summary=evidence_summary, evidence=evidence, data_sources=list(sources.values()),
            warnings=list(dict.fromkeys(all_warnings)), coverage=coverage,
        )

    @staticmethod
    def _unavailable(query: InterpretedQuery, warnings: list[str], reason: str, sources: Any = ()) -> RecommendationResponse:
        return RecommendationResponse(status="data_unavailable", interpreted_query=query, clarification_question="Live data needed for this recommendation could not be retrieved. Please try again shortly.", data_sources=list(sources), warnings=warnings + [reason])


def _diverse_candidates(features: list[OSMFeature], latitude: float, longitude: float, limit: int) -> list[OSMFeature]:
    from ..engine.scoring import haversine_km

    remaining = sorted(features, key=lambda item: haversine_km(latitude, longitude, item.latitude, item.longitude))
    selected: list[OSMFeature] = []
    while remaining and len(selected) < limit:
        if not selected:
            chosen = remaining.pop(0)
        else:
            chosen = max(remaining, key=lambda item: min(haversine_km(item.latitude, item.longitude, old.latitude, old.longitude) for old in selected))
            remaining.remove(chosen)
        selected.append(chosen)
    return selected


def _advice(
    weather_hour: dict[str, Any],
    air_hour: dict[str, Any] | None,
    weather: dict[str, Any],
    air: dict[str, Any] | None,
    profile_flags: list[str] | None = None,
) -> Advice:
    values = weather_hour.get("values", {})
    carry: list[str] = []
    watch: list[str] = []
    avoid: list[str] = []
    uv = values.get("uv_index")
    if uv is not None and uv >= 6:
        carry.append("Sun protection; forecast UV index is elevated.")
    rain = values.get("precipitation_probability")
    precipitation = values.get("precipitation")
    if rain is not None and rain >= 40 or precipitation is not None and precipitation > 1:
        carry.append("Rain protection; precipitation is forecast.")
        watch.append("Forecast precipitation may affect outdoor conditions.")
    temperature = values.get("apparent_temperature")
    if temperature is None:
        temperature = values.get("temperature_2m")
    if temperature is not None and temperature >= 32:
        watch.append("Forecast apparent/air temperature is high; consider a cooler time and take breaks.")
    if temperature is not None and temperature >= 38:
        avoid.append("Consider another time if local conditions feel uncomfortable.")
    aq_values = air_hour.get("values", {}) if air_hour else {}
    aqi = aq_values.get("european_aqi") or aq_values.get("us_aqi")
    if aqi is not None and aqi > 100:
        watch.append("The modelled regional air-quality index is elevated; it is not an exact-site sensor reading.")
    profiles = set(profile_flags or [])
    if "asthma" in profiles:
        if aqi is None:
            watch.append("Air-quality data is unavailable for this time; check local conditions before activity.")
        elif aqi > 50:
            watch.append("Asthma was mentioned: the regional air-quality forecast is above 50; consider local guidance and adjust effort to personal needs.")
    if profiles.intersection({"pregnancy", "child", "senior"}) and temperature is not None and temperature >= 30:
        watch.append("Heat is forecast; consider shade, breaks, and water for the group. This is general planning information, not medical advice.")
    if not carry and not watch and not avoid:
        watch.append("Review the live forecast again before leaving; conditions can change.")
    return Advice(carry=carry, watch_for=watch, avoid_if=avoid)
