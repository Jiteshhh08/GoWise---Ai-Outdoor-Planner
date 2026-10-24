from dataclasses import dataclass, field
from math import atan2, cos, radians, sin, sqrt
from typing import Any

from ..schemas import ScoreFactor
from .activities import ACTIVITY_RULES, classify_venue

WEIGHTS = {"activity_fit": 0.25, "weather": 0.40, "air_quality": 0.20, "daylight": 0.05, "geospatial_context": 0.10}
GREEN_FEATURES = (
    ("leisure", "park"), ("leisure", "garden"), ("landuse", "forest"),
    ("landuse", "grass"), ("landuse", "meadow"), ("natural", "wood"),
)
ROAD_CLASSES = {"motorway", "trunk", "primary", "secondary"}
INDUSTRIAL_FEATURE = ("landuse", "industrial")


@dataclass(frozen=True)
class GeoFeature:
    feature_id: str
    tags: dict[str, str]
    latitude: float | None
    longitude: float | None
    source_url: str


@dataclass
class CandidateEvaluation:
    suitability_score: float
    coverage: float
    score_factors: list[ScoreFactor]
    warnings: list[str] = field(default_factory=list)
    context_flags: list[str] = field(default_factory=list)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0088
    delta_latitude = radians(lat2 - lat1)
    delta_longitude = radians(lon2 - lon1)
    a = sin(delta_latitude / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(delta_longitude / 2) ** 2
    return 2 * earth_radius_km * atan2(sqrt(a), sqrt(1 - a))


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    y = sin(radians(lon2 - lon1)) * cos(radians(lat2))
    x = cos(radians(lat1)) * sin(radians(lat2)) - sin(radians(lat1)) * cos(radians(lat2)) * cos(radians(lon2 - lon1))
    return (atan2(y, x) * 180 / 3.141592653589793 + 360) % 360


def angular_difference_degrees(left: float, right: float) -> float:
    return abs((left - right + 180) % 360 - 180)


def _weather_score(activity: str, values: dict[str, Any]) -> tuple[float | None, str | None]:
    rule = ACTIVITY_RULES[activity]
    component_scores: list[tuple[float, str]] = []
    details: list[str] = []

    temperature = _number(values.get("apparent_temperature"))
    if temperature is None:
        temperature = _number(values.get("temperature_2m"))
    if temperature is not None:
        lower, upper = rule.comfortable_temperature_c
        if lower <= temperature <= upper:
            score = 100.0
        elif temperature < lower:
            score = max(0.0, 100 - (lower - temperature) * 5)
        else:
            score = max(0.0, 100 - (temperature - upper) * 5)
        component_scores.append((score, "temperature"))
        details.append(f"{temperature:g} °C apparent/air temperature")

    rain_probability = _number(values.get("precipitation_probability"))
    precipitation = _number(values.get("precipitation"))
    if rain_probability is not None:
        probability = min(100, max(0, rain_probability))
        rain_score = 100 if probability <= 10 else 85 if probability <= 25 else 55 if probability <= rule.max_precipitation_probability else 20
        component_scores.append((float(rain_score), "precipitation probability"))
        details.append(f"{probability:g}% precipitation probability")
    elif precipitation is not None:
        rain_score = 100 if precipitation <= 0.1 else 75 if precipitation <= 1 else 40 if precipitation <= 3 else 15
        component_scores.append((float(rain_score), "precipitation"))
        details.append(f"{precipitation:g} mm precipitation")

    wind = _number(values.get("wind_speed_10m"))
    if wind is not None:
        wind_score = 100 if wind <= rule.max_wind_kmh else max(0, 100 - (wind - rule.max_wind_kmh) * 4)
        component_scores.append((wind_score, "wind speed"))
        details.append(f"{wind:g} km/h wind")

    uv_index = _number(values.get("uv_index"))
    if uv_index is not None:
        uv_score = 100 if uv_index <= 5 else max(25, 100 - (uv_index - 5) * 12)
        component_scores.append((uv_score, "UV index"))
        details.append(f"UV index {uv_index:g}")

    if not component_scores:
        return None, None
    return sum(score for score, _ in component_scores) / len(component_scores), "; ".join(details)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _air_quality_score(values: dict[str, Any]) -> tuple[float | None, str | None, str | None]:
    for key, label in (("european_aqi", "European AQI"), ("us_aqi", "US AQI")):
        value = _number(values.get(key))
        if value is not None:
            score = 100 if value <= 20 else 85 if value <= 50 else 60 if value <= 100 else 30 if value <= 150 else 10
            return float(score), f"{label} {value:g}", label
    pm25 = _number(values.get("pm2_5"))
    if pm25 is not None:
        score = 100 if pm25 <= 5 else 85 if pm25 <= 15 else 55 if pm25 <= 50 else 20
        return float(score), f"PM2.5 {pm25:g} µg/m³", "PM2.5"
    return None, None, None


def _context_features(features: list[GeoFeature], key: str, values: set[str]) -> list[GeoFeature]:
    return [feature for feature in features if feature.tags.get(key, "").casefold() in values]


def _has_green(tags: dict[str, str]) -> bool:
    return any(tags.get(key, "").casefold() == value for key, value in GREEN_FEATURES)


def _context_factor(venue: GeoFeature, features: list[GeoFeature]) -> tuple[float | None, str | None, dict[str, float]]:
    if venue.latitude is None or venue.longitude is None:
        return None, None, {}
    measured: list[float] = []
    details: list[str] = []
    distances: dict[str, float] = {}
    roads = _context_features(features, "highway", ROAD_CLASSES)
    road_distances = [
        haversine_km(venue.latitude, venue.longitude, feature.latitude, feature.longitude)
        for feature in roads if feature.latitude is not None and feature.longitude is not None
    ]
    if road_distances:
        nearest_road = min(road_distances)
        distances["nearest_major_road_km"] = nearest_road
        measured.append(20 if nearest_road <= 0.05 else 40 if nearest_road <= 0.15 else 65 if nearest_road <= 0.4 else 85)
        details.append(f"mapped major road about {nearest_road:.2f} km away (proximity proxy)")

    green = [feature for feature in features if _has_green(feature.tags)]
    green_distances = [
        haversine_km(venue.latitude, venue.longitude, feature.latitude, feature.longitude)
        for feature in green if feature.latitude is not None and feature.longitude is not None
    ]
    if green_distances:
        nearest_green = min(green_distances)
        distances["nearest_mapped_green_km"] = nearest_green
        measured.append(95 if nearest_green <= 0.25 else 80 if nearest_green <= 1 else 55)
        details.append(f"mapped green feature about {nearest_green:.2f} km away")

    if not measured:
        return None, None, distances
    return sum(measured) / len(measured), "; ".join(details), distances


def _context_warnings(
    venue: GeoFeature,
    features: list[GeoFeature],
    wind_direction_from: float | None,
) -> list[str]:
    if venue.latitude is None or venue.longitude is None or wind_direction_from is None:
        return []
    warnings: list[str] = []
    sources = [
        feature for feature in features
        if feature.tags.get("landuse", "").casefold() == INDUSTRIAL_FEATURE[1]
        or feature.tags.get("highway", "").casefold() in ROAD_CLASSES
    ]
    for feature in sources:
        if feature.latitude is None or feature.longitude is None:
            continue
        distance = haversine_km(venue.latitude, venue.longitude, feature.latitude, feature.longitude)
        bearing = bearing_degrees(venue.latitude, venue.longitude, feature.latitude, feature.longitude)
        if distance <= 3 and angular_difference_degrees(bearing, wind_direction_from) <= 45:
            label = "industrial land use" if feature.tags.get("landuse", "").casefold() == "industrial" else "major road"
            warnings.append(
                f"Mapped {label} lies {distance:.1f} km within the forecast wind-from sector; this is context only, not a pollution measurement."
            )
            break
    return warnings


def score_candidate_time(
    activity: str,
    venue: GeoFeature,
    when: Any,
    weather_hour: dict[str, Any] | None,
    air_quality_hour: dict[str, Any] | None,
    context_features: list[GeoFeature],
    sunrise: Any = None,
    sunset: Any = None,
) -> CandidateEvaluation:
    if activity not in ACTIVITY_RULES:
        raise ValueError(f"Unsupported activity: {activity}")
    if not classify_venue(activity, venue.tags):
        raise ValueError("Venue does not match the requested activity tags.")

    factors: list[ScoreFactor] = []
    available_weight = 0.0
    weighted_sum = 0.0

    def add_factor(name: str, label: str, score: float | None, value: Any, explanation: str | None = None) -> None:
        nonlocal available_weight, weighted_sum
        weight = WEIGHTS[name]
        factors.append(ScoreFactor(
            name=name,
            label=label,
            value=value,
            score=score,
            weight=weight,
            explanation=explanation,
            available=score is not None,
        ))
        if score is not None:
            available_weight += weight
            weighted_sum += score * weight

    add_factor("activity_fit", "Activity fit", 100, venue.tags.get("sport") or venue.tags.get("leisure") or "mapped OSM tags", "Matched using the provider's OSM tags.")

    weather_values = weather_hour.get("values", {}) if isinstance(weather_hour, dict) else {}
    weather_score, weather_detail = _weather_score(activity, weather_values)
    add_factor("weather", "Weather", weather_score, weather_detail, "Heuristic based on forecast fields that were available for this hour.")

    air_values = air_quality_hour.get("values", {}) if isinstance(air_quality_hour, dict) else {}
    air_score, air_detail, air_label = _air_quality_score(air_values)
    add_factor("air_quality", "Air quality", air_score, air_detail, f"Forecast index/pollutant: {air_label}." if air_label else None)

    daylight_score: float | None = None
    daylight_value: str | None = None
    if sunrise is not None and sunset is not None and hasattr(when, "timestamp"):
        try:
            start_seconds = when.timestamp()
            sunrise_seconds = sunrise.timestamp()
            sunset_seconds = sunset.timestamp()
            if sunrise_seconds <= start_seconds <= sunset_seconds:
                daylight_score, daylight_value = 100, "daylight"
            elif min(abs(start_seconds - sunrise_seconds), abs(start_seconds - sunset_seconds)) <= 1800:
                daylight_score, daylight_value = 75, "near sunrise/sunset"
            else:
                daylight_score, daylight_value = 35, "darkness"
        except (AttributeError, OSError, OverflowError):
            pass
    add_factor("daylight", "Daylight", daylight_score, daylight_value, "Compared with provider sunrise and sunset times.")

    context_score, context_detail, context_distances = _context_factor(venue, context_features)
    add_factor("geospatial_context", "Mapped context", context_score, context_detail, "Road proximity is a proxy, not live traffic.")

    if available_weight <= 0:
        score = 0.0
    else:
        score = weighted_sum / available_weight
    weather_direction = _number(weather_values.get("wind_direction_10m"))
    warnings = _context_warnings(venue, context_features, weather_direction)
    if weather_score is None:
        warnings.append("Weather data is unavailable for this time; no weather value was substituted.")
    if air_score is None:
        warnings.append("Air-quality data is unavailable for this time; no pollutant value was substituted.")
    if daylight_score is None:
        warnings.append("Sunrise/sunset data is unavailable for this time.")

    return CandidateEvaluation(
        suitability_score=round(max(0.0, min(100.0, score)), 1),
        coverage=round(available_weight, 3),
        score_factors=factors,
        warnings=warnings,
        context_flags=[f"{key}: {value:.2f} km" for key, value in context_distances.items()],
    )
