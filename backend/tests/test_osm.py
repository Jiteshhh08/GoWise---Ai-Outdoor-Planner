import asyncio
import unittest

import httpx

from app.providers.http import ProviderError
from app.providers.osm import OverpassPlaces, build_query, cache as osm_cache


class OverpassTests(unittest.TestCase):
    def setUp(self) -> None:
        osm_cache._entries.clear()

    def test_query_is_bounded_and_requests_venue_and_context_tags(self) -> None:
        query = build_query(19.1176, 72.9060, 5)

        self.assertIn("[timeout:25]", query)
        self.assertIn("[maxsize:33554432]", query)
        self.assertIn("out center tags qt 1000;", query)
        self.assertIn('"leisure"', query)
        self.assertIn('"highway"', query)
        self.assertIn('"landuse"', query)
        for required_activity_tag in ('"sport"', '"route"="bicycle"', '"tourism"', '"amenity"="events_venue"', '"natural"'):
            self.assertIn(required_activity_tag, query)
        self.assertIn("around:5000,19.117600,72.906000", query)

    def test_search_parses_elements_and_caches_the_response(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"elements": [
                {"type": "node", "id": 9, "lat": 19.1, "lon": 72.9, "tags": {"leisure": "park", "name": "Example Park"}},
                {"type": "way", "id": 10, "center": {"lat": 19.11, "lon": 72.91}, "tags": {"highway": "primary"}},
                {"type": "relation", "id": 11, "tags": {"landuse": "industrial"}},
            ]})

        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                service = OverpassPlaces(client)
                return await service.search(19.1, 72.9, 5), await service.search(19.1, 72.9, 5)

        first, second = asyncio.run(run())

        self.assertEqual(len(requests), 1)
        self.assertEqual(first, second)
        self.assertEqual(first.features[0].feature_id, "node/9")
        self.assertEqual(first.features[1].latitude, 19.11)
        self.assertIsNone(first.features[2].latitude)
        self.assertEqual(first.features[0].tags["name"], "Example Park")

    def test_search_bounds_coordinates_and_radius(self) -> None:
        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"elements": []}))) as client:
                service = OverpassPlaces(client)
                with self.assertRaises(ValueError):
                    await service.search(91, 0, 5)
                with self.assertRaises(ValueError):
                    await service.search(0, 0, 1000)

        asyncio.run(run())

    def test_provider_http_failures_have_provider_context(self) -> None:
        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(400))) as client:
                with self.assertRaisesRegex(ProviderError, "Overpass API / OpenStreetMap.*HTTP 400"):
                    await OverpassPlaces(client).search(19.1, 72.9, 5)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
