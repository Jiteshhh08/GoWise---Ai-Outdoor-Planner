import asyncio
import unittest

import httpx

from app.providers.geocoding import NominatimGeocoder, cache as geocode_cache


class GeocodingTests(unittest.TestCase):
    def setUp(self) -> None:
        geocode_cache._entries.clear()

    def test_geocoder_identifies_app_and_caches_successful_results(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json=[{
                    "display_name": "Powai, Mumbai, Maharashtra, India",
                    "lat": "19.1176",
                    "lon": "72.9060",
                    "boundingbox": ["19.0", "19.2", "72.8", "73.0"],
                    "osm_type": "relation",
                    "osm_id": 123,
                    "osm_url": "https://www.openstreetmap.org/relation/123",
                }],
            )

        async def run() -> tuple[list, list]:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                service = NominatimGeocoder(client, user_agent="GoWiseTest/1.0 (test contact)")
                first = await service.search("  Powai, Mumbai ")
                second = await service.search("Powai, Mumbai")
                return first, second

        first, second = asyncio.run(run())

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].headers["user-agent"], "GoWiseTest/1.0 (test contact)")
        self.assertEqual(requests[0].url.params["format"], "jsonv2")
        self.assertEqual(first, second)
        self.assertEqual(first[0].latitude, 19.1176)
        self.assertEqual(first[0].osm_id, 123)

    def test_geocoder_returns_empty_for_no_match_without_guessing(self) -> None:
        async def run():
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
            ) as client:
                return await NominatimGeocoder(client).search("Place that is not mapped")

        self.assertEqual(asyncio.run(run()), [])


if __name__ == "__main__":
    unittest.main()
