import asyncio
import unittest
from datetime import datetime, timedelta, timezone

import httpx

from app.model.query_extraction import ParsedOutdoorQuery
from app.providers.geocoding import GeocodedPlace
from app.providers.http import ProviderError
from app.providers.meteo import AIR_QUALITY_NAME, WEATHER_NAME
from app.providers.osm import OSMFeature, OSMSearchResult
from app.services.recommendations import RecommendationService


class FakeModel:
    async def generate(self, messages, max_new_tokens=None):
        return "{}"


class FakeExtractor:
    def __init__(self, query):
        self.query = query

    async def extract(self, question):
        return self.query


class RecommendationPipelineTests(unittest.TestCase):
    def setUp(self):
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        self.start = now + timedelta(days=1)
        self.query = ParsedOutdoorQuery(
            activity="running", location_label="Powai, Mumbai", radius_km=5,
            start_time=self.start, end_time=self.start + timedelta(hours=2),
            timezone="Asia/Kolkata", profile_flags=[], warnings=[],
        )
        self.venue = OSMFeature("way/7", "way", {"leisure": "park", "name": "Mapped Park"}, 19.1, 72.9, "https://www.openstreetmap.org/way/7")
        self.place = GeocodedPlace("Powai, Mumbai", 19.1, 72.9, None, "relation", 7, "https://www.openstreetmap.org/relation/7", now, 0.8)
        self.client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))
        self.service = RecommendationService(self.client, FakeModel())  # type: ignore[arg-type]
        self.service.extractor = FakeExtractor(self.query)  # type: ignore[assignment]

    def tearDown(self):
        asyncio.run(self.client.aclose())

    def test_live_data_path_returns_ranked_evidence_and_provider_sources(self):
        async def geocode(*args, **kwargs):
            return [self.place]

        async def osm_search(*args, **kwargs):
            return OSMSearchResult([self.venue], datetime.now(timezone.utc).isoformat(), "https://overpass-api.de/api/interpreter")

        async def weather(points):
            hourly = [{"time": self.start + timedelta(hours=offset), "values": {
                "temperature_2m": 20 + offset, "apparent_temperature": 20 + offset,
                "precipitation_probability": 5, "precipitation": 0, "wind_speed_10m": 8,
                "wind_direction_10m": 90, "uv_index": 2,
            }} for offset in range(3)]
            return [{"hourly": hourly, "daily": [], "hourly_units": {"temperature_2m": "°C"},
                     "fetched_at": datetime.now(timezone.utc), "source": WEATHER_NAME,
                     "source_url": "https://api.open-meteo.com/v1/forecast", "latitude": 19.1, "longitude": 72.9}]

        async def air(points):
            return [{"hourly": [], "hourly_units": {}, "fetched_at": datetime.now(timezone.utc),
                     "source": AIR_QUALITY_NAME, "source_url": "https://air-quality-api.open-meteo.com/v1/air-quality",
                     "latitude": 19.1, "longitude": 72.9}]

        self.service.geocoder.search = geocode  # type: ignore[method-assign]
        self.service.places.search = osm_search  # type: ignore[method-assign]
        self.service.forecast.fetch_many = weather  # type: ignore[method-assign]
        self.service.air_quality.fetch_many = air  # type: ignore[method-assign]

        result = asyncio.run(self.service.recommend("Run at Powai tomorrow morning"))

        self.assertEqual(result.status, "partial")
        self.assertEqual(result.recommendation.name, "Mapped Park")
        self.assertEqual(result.recommendation.time, self.start)
        self.assertGreaterEqual(result.coverage, 0.6)
        self.assertTrue(any(item.source == WEATHER_NAME for item in result.evidence))
        self.assertTrue(any(item.source == "Overpass API / OpenStreetMap" for item in result.evidence))
        self.assertTrue(result.evidence_summary)
        self.assertEqual(result.data_sources[0].name, "Nominatim")

    def test_provider_failures_do_not_return_a_fabricated_recommendation(self):
        async def geocode(*args, **kwargs):
            return [self.place]

        async def osm_search(*args, **kwargs):
            return OSMSearchResult([self.venue], datetime.now(timezone.utc).isoformat(), "https://overpass-api.de/api/interpreter")

        async def failed(*args, **kwargs):
            raise ProviderError("Open-Meteo", "unavailable")

        self.service.geocoder.search = geocode  # type: ignore[method-assign]
        self.service.places.search = osm_search  # type: ignore[method-assign]
        self.service.forecast.fetch_many = failed  # type: ignore[method-assign]
        self.service.air_quality.fetch_many = failed  # type: ignore[method-assign]

        result = asyncio.run(self.service.recommend("Run at Powai tomorrow morning"))

        self.assertEqual(result.status, "data_unavailable")
        self.assertIsNone(result.recommendation)
        self.assertTrue(any("Weather data is unavailable" in item for item in result.warnings))


if __name__ == "__main__":
    unittest.main()
