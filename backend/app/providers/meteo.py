from datetime import datetime, timezone
from math import isfinite
from typing import Any

import httpx

from ..config import settings
from .cache import TTLCache, rounded_coordinate
from .http import ProviderError, request_json

WEATHER_NAME = "Open-Meteo Forecast API"
AIR_QUALITY_NAME = "Open-Meteo Air Quality API"
WEATHER_VARIABLES = (
    "temperature_2m",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
    "uv_index",
)
AIR_QUALITY_VARIABLES = ("pm2_5", "pm10", "european_aqi", "us_aqi", "ozone", "nitrogen_dioxide")


def coordinate_key(latitude: float, longitude: float) -> tuple[str, str]:
    return rounded_coordinate(latitude), rounded_coordinate(longitude)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if isfinite(number) else None


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _response_locations(payload: Any, expected_count: int, provider: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if payload.get("error"):
            reason = payload.get("reason")
            raise ProviderError(provider, str(reason or "returned an error response"))
        locations = [payload]
    elif isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        locations = payload
    else:
        raise ProviderError(provider, "returned an unexpected response shape")
    if len(locations) != expected_count:
        raise ProviderError(provider, "returned a different number of locations than requested")
    return locations


def _validated_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(points) > settings.max_candidates:
        raise ValueError(f"At most {settings.max_candidates} coordinates may be requested at once.")
    for latitude, longitude in points:
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("Coordinates are outside the WGS84 bounds.")
    return points


def _array_values(raw: Any) -> list[Any]:
    return raw if isinstance(raw, list) else []


class OpenMeteoForecast:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.cache: TTLCache[list[dict[str, Any]]] = TTLCache(settings.cache_ttl_seconds, settings.cache_max_entries)

    async def fetch_many(self, points: list[tuple[float, float]]) -> list[dict[str, Any]]:
        points = _validated_points(points)
        if not points:
            return []
        key = "|".join(f"{rounded_coordinate(lat)},{rounded_coordinate(lon)}" for lat, lon in points)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        payload = await request_json(
            self.client,
            WEATHER_NAME,
            "GET",
            settings.weather_url,
            params={
                "latitude": ",".join(f"{lat:.5f}" for lat, _ in points),
                "longitude": ",".join(f"{lon:.5f}" for _, lon in points),
                "hourly": ",".join(WEATHER_VARIABLES),
                "daily": "sunrise,sunset",
                "timezone": "UTC",
                "forecast_days": 7,
            },
        )
        locations = _response_locations(payload, len(points), WEATHER_NAME)
        fetched_at = datetime.now(timezone.utc)
        results = [self._parse_location(item, fetched_at) for item in locations]
        self.cache.set(key, results)
        return results

    @staticmethod
    def _parse_location(payload: dict[str, Any], fetched_at: datetime) -> dict[str, Any]:
        hourly = payload.get("hourly") if isinstance(payload.get("hourly"), dict) else {}
        times = _array_values(hourly.get("time"))
        hours: list[dict[str, Any]] = []
        for index, raw_time in enumerate(times):
            forecast_time = _time(raw_time)
            if forecast_time is None:
                continue
            values = {
                variable: _number(_array_values(hourly.get(variable))[index])
                if index < len(_array_values(hourly.get(variable))) else None
                for variable in WEATHER_VARIABLES
            }
            hours.append({"time": forecast_time, "values": values})

        daily = payload.get("daily") if isinstance(payload.get("daily"), dict) else {}
        dates = _array_values(daily.get("time"))
        sunrise_values = _array_values(daily.get("sunrise"))
        sunset_values = _array_values(daily.get("sunset"))
        daylight = []
        for index, day in enumerate(dates):
            daylight.append({
                "date": day,
                "sunrise": _time(sunrise_values[index]) if index < len(sunrise_values) else None,
                "sunset": _time(sunset_values[index]) if index < len(sunset_values) else None,
            })

        latitude = _number(payload.get("latitude"))
        longitude = _number(payload.get("longitude"))
        timezone_name = payload.get("timezone") if isinstance(payload.get("timezone"), str) else None
        return {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone_name,
            "hourly_units": payload.get("hourly_units") if isinstance(payload.get("hourly_units"), dict) else {},
            "daily_units": payload.get("daily_units") if isinstance(payload.get("daily_units"), dict) else {},
            "hourly": hours,
            "daily": daylight,
            "fetched_at": fetched_at,
            "source": WEATHER_NAME,
            "source_url": settings.weather_url,
        }


class OpenMeteoAirQuality:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.cache: TTLCache[list[dict[str, Any]]] = TTLCache(settings.cache_ttl_seconds, settings.cache_max_entries)

    async def fetch_many(self, points: list[tuple[float, float]]) -> list[dict[str, Any]]:
        points = _validated_points(points)
        if not points:
            return []
        key = "|".join(f"{rounded_coordinate(lat)},{rounded_coordinate(lon)}" for lat, lon in points)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        payload = await request_json(
            self.client,
            AIR_QUALITY_NAME,
            "GET",
            settings.air_quality_url,
            params={
                "latitude": ",".join(f"{lat:.5f}" for lat, _ in points),
                "longitude": ",".join(f"{lon:.5f}" for _, lon in points),
                "hourly": ",".join(AIR_QUALITY_VARIABLES),
                "timezone": "UTC",
                "forecast_days": 5,
            },
        )
        locations = _response_locations(payload, len(points), AIR_QUALITY_NAME)
        fetched_at = datetime.now(timezone.utc)
        results = [self._parse_location(item, fetched_at) for item in locations]
        self.cache.set(key, results)
        return results

    @staticmethod
    def _parse_location(payload: dict[str, Any], fetched_at: datetime) -> dict[str, Any]:
        hourly = payload.get("hourly") if isinstance(payload.get("hourly"), dict) else {}
        times = _array_values(hourly.get("time"))
        hours: list[dict[str, Any]] = []
        for index, raw_time in enumerate(times):
            forecast_time = _time(raw_time)
            if forecast_time is None:
                continue
            values = {
                variable: _number(_array_values(hourly.get(variable))[index])
                if index < len(_array_values(hourly.get(variable))) else None
                for variable in AIR_QUALITY_VARIABLES
            }
            hours.append({"time": forecast_time, "values": values})

        return {
            "latitude": _number(payload.get("latitude")),
            "longitude": _number(payload.get("longitude")),
            "timezone": payload.get("timezone") if isinstance(payload.get("timezone"), str) else None,
            "hourly_units": payload.get("hourly_units") if isinstance(payload.get("hourly_units"), dict) else {},
            "hourly": hours,
            "fetched_at": fetched_at,
            "source": AIR_QUALITY_NAME,
            "source_url": settings.air_quality_url,
            "resolution_note": "Modelled regional forecast; not a sensor reading at the exact venue.",
        }
