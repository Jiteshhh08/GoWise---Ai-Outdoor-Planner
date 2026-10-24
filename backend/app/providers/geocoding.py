import asyncio
import hashlib
import threading
import time
from dataclasses import dataclass

import httpx

from ..config import settings
from .cache import TTLCache
from .http import ProviderError, request_json

PROVIDER_NAME = "Nominatim"
cache: TTLCache[list["GeocodedPlace"]] = TTLCache(
    settings.geocode_cache_ttl_seconds,
    settings.cache_max_entries,
)
_rate_lock = threading.Lock()
_next_allowed_at = 0.0


@dataclass(frozen=True)
class GeocodedPlace:
    label: str
    latitude: float
    longitude: float
    bounding_box: tuple[float, float, float, float] | None
    osm_type: str | None
    osm_id: int | None
    source_url: str


async def _wait_for_nominatim_slot() -> None:
    global _next_allowed_at
    with _rate_lock:
        now = time.monotonic()
        request_at = max(now, _next_allowed_at)
        _next_allowed_at = request_at + 1.0
    wait_seconds = request_at - now
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)


class NominatimGeocoder:
    def __init__(self, client: httpx.AsyncClient, user_agent: str | None = None) -> None:
        self.client = client
        self.user_agent = user_agent or settings.nominatim_user_agent

    async def search(self, query: str, limit: int = 3) -> list[GeocodedPlace]:
        normalized = " ".join(query.split())
        if not normalized:
            return []
        safe_limit = max(1, min(limit, 5))
        digest = hashlib.sha256(f"{normalized.casefold()}|{safe_limit}".encode()).hexdigest()
        cached = cache.get(digest)
        if cached is not None:
            return cached

        await _wait_for_nominatim_slot()
        payload = await request_json(
            self.client,
            PROVIDER_NAME,
            "GET",
            settings.nominatim_url,
            params={"q": normalized, "format": "jsonv2", "limit": safe_limit, "addressdetails": 1},
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
        )
        if not isinstance(payload, list):
            raise ProviderError(PROVIDER_NAME, "returned an unexpected response shape")

        places: list[GeocodedPlace] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                latitude = float(item["lat"])
                longitude = float(item["lon"])
            except (KeyError, TypeError, ValueError):
                continue
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                continue
            raw_box = item.get("boundingbox")
            bounds = None
            if isinstance(raw_box, list) and len(raw_box) == 4:
                try:
                    bounds = tuple(float(value) for value in raw_box)  # type: ignore[assignment]
                except (TypeError, ValueError):
                    bounds = None
            osm_type = str(item["osm_type"]) if item.get("osm_type") else None
            try:
                osm_id = int(item["osm_id"]) if item.get("osm_id") is not None else None
            except (TypeError, ValueError):
                osm_id = None
            source_url = item.get("osm_url")
            if not source_url and osm_type in {"node", "way", "relation"} and osm_id is not None:
                source_url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
            places.append(
                GeocodedPlace(
                    label=str(item.get("display_name") or normalized),
                    latitude=latitude,
                    longitude=longitude,
                    bounding_box=bounds,
                    osm_type=osm_type,
                    osm_id=osm_id,
                    source_url=str(source_url or "https://www.openstreetmap.org/"),
                )
            )

        cache.set(digest, places)
        return places
