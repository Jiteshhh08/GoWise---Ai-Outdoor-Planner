import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from ..config import settings
from .cache import TTLCache, rounded_coordinate
from .http import ProviderError, request_json

PROVIDER_NAME = "Overpass API / OpenStreetMap"
cache: TTLCache["OSMSearchResult"] = TTLCache(settings.cache_ttl_seconds, settings.cache_max_entries)

VENUE_FILTERS = (
    'nwr(around:{radius},{lat},{lon})["leisure"~"^(park|garden|track|pitch|sports_centre|stadium|golf_course|nature_reserve|recreation_ground)$"];',
    'nwr(around:{radius},{lat},{lon})["sport"~"^(running|cycling|tennis|golf|cricket|soccer|football)$"];',
    'nwr(around:{radius},{lat},{lon})["highway"~"^(path|footway|track|bridleway|cycleway)$"];',
    'nwr(around:{radius},{lat},{lon})["route"="bicycle"];',
    'nwr(around:{radius},{lat},{lon})["tourism"~"^(viewpoint|picnic_site)$"];',
    'nwr(around:{radius},{lat},{lon})["amenity"="events_venue"];',
    'nwr(around:{radius},{lat},{lon})["natural"~"^(peak|waterfall|beach|heath|wood)$"];',
)
CONTEXT_FILTERS = (
    'nwr(around:{radius},{lat},{lon})["highway"~"^(motorway|trunk|primary|secondary)$"];',
    'nwr(around:{radius},{lat},{lon})["landuse"~"^(industrial|forest|grass|meadow)$"];',
    'nwr(around:{radius},{lat},{lon})["natural"~"^(wood|water|wetland)$"];',
    'nwr(around:{radius},{lat},{lon})["water"];',
    'nwr(around:{radius},{lat},{lon})["leisure"="park"];',
)


@dataclass(frozen=True)
class OSMFeature:
    feature_id: str
    feature_type: str
    tags: dict[str, str]
    latitude: float | None
    longitude: float | None
    source_url: str


@dataclass(frozen=True)
class OSMSearchResult:
    features: list[OSMFeature]
    fetched_at: str
    source_url: str


def build_query(latitude: float, longitude: float, radius_km: float) -> str:
    radius_meters = round(radius_km * 1000)
    lat = f"{latitude:.6f}"
    lon = f"{longitude:.6f}"
    filters = [line.format(radius=radius_meters, lat=lat, lon=lon) for line in (*VENUE_FILTERS, *CONTEXT_FILTERS)]
    return (
        "[out:json][timeout:25][maxsize:33554432];\n(\n"
        + "\n".join(filters)
        + f"\n);\nout center tags qt {settings.max_overpass_features};"
    )


class OverpassPlaces:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def search(self, latitude: float, longitude: float, radius_km: float) -> OSMSearchResult:
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("Coordinates are outside the WGS84 bounds.")
        if not (0.1 <= radius_km <= settings.max_search_radius_km):
            raise ValueError(f"Search radius must be between 0.1 and {settings.max_search_radius_km:g} km.")

        cache_key = hashlib.sha256(
            f"{rounded_coordinate(latitude)}|{rounded_coordinate(longitude)}|{radius_km:.1f}".encode()
        ).hexdigest()
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        query = build_query(latitude, longitude, radius_km)
        payload = await request_json(
            self.client,
            PROVIDER_NAME,
            "POST",
            settings.overpass_url,
            data={"data": query},
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
            raise ProviderError(PROVIDER_NAME, "returned an unexpected response shape")

        features: list[OSMFeature] = []
        for element in payload["elements"][: settings.max_overpass_features]:
            if not isinstance(element, dict) or element.get("type") not in {"node", "way", "relation"}:
                continue
            element_id = element.get("id")
            if element_id is None:
                continue
            lat_value = element.get("lat")
            lon_value = element.get("lon")
            if isinstance(element.get("center"), dict):
                lat_value = element["center"].get("lat", lat_value)
                lon_value = element["center"].get("lon", lon_value)
            try:
                lat = float(lat_value) if lat_value is not None else None
                lon = float(lon_value) if lon_value is not None else None
            except (TypeError, ValueError):
                lat = lon = None
            if lat is not None and lon is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180):
                lat = lon = None
            tags = element.get("tags") if isinstance(element.get("tags"), dict) else {}
            tags = {str(key): str(value) for key, value in tags.items()}
            feature_type = str(element["type"])
            osm_url = f"https://www.openstreetmap.org/{feature_type}/{element_id}"
            features.append(
                OSMFeature(
                    feature_id=f"{feature_type}/{element_id}",
                    feature_type=feature_type,
                    tags=tags,
                    latitude=lat,
                    longitude=lon,
                    source_url=osm_url,
                )
            )

        result = OSMSearchResult(
            features=features,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source_url=settings.overpass_url,
        )
        cache.set(cache_key, result)
        return result
