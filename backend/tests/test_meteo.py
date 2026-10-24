import asyncio
import unittest

import httpx

from app.providers.http import ProviderError
from app.providers.meteo import OpenMeteoAirQuality, OpenMeteoForecast


class OpenMeteoTests(unittest.TestCase):
    def test_weather_batch_parses_times_units_and_missing_values(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={
                "latitude": 19.125,
                "longitude": 72.875,
                "timezone": "GMT",
                "hourly": {
                    "time": ["2026-10-24T06:00", "2026-10-24T07:00"],
                    "temperature_2m": [29.5, None],
                    "apparent_temperature": [31.0, 31.2],
                    "precipitation_probability": [10, 20],
                },
                "daily": {"time": ["2026-10-24"], "sunrise": ["2026-10-24T00:30"], "sunset": ["2026-10-24T12:15"]},
            })

        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await OpenMeteoForecast(client).fetch_many([(19.12, 72.90)])

        results = asyncio.run(run())

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url.params["timezone"], "UTC")
        self.assertIn("wind_direction_10m", requests[0].url.params["hourly"])
        forecast = results[0]
        self.assertEqual(forecast["hourly"][0]["time"].isoformat(), "2026-10-24T06:00:00+00:00")
        self.assertEqual(forecast["hourly"][0]["values"]["temperature_2m"], 29.5)
        self.assertIsNone(forecast["hourly"][1]["values"]["temperature_2m"])
        self.assertIsNotNone(forecast["daily"][0]["sunrise"])
        self.assertEqual(forecast["source"], "Open-Meteo Forecast API")

    def test_air_quality_records_missing_pollutants_as_unknown(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "latitude": 19.1,
                "longitude": 72.9,
                "timezone": "GMT",
                "hourly": {"time": ["2026-10-24T06:00"], "pm2_5": [16.2], "pm10": [None], "us_aqi": [44]},
            })

        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await OpenMeteoAirQuality(client).fetch_many([(19.1, 72.9)])

        air = asyncio.run(run())[0]
        self.assertEqual(air["hourly"][0]["values"]["pm2_5"], 16.2)
        self.assertIsNone(air["hourly"][0]["values"]["pm10"])
        self.assertEqual(air["hourly"][0]["values"]["us_aqi"], 44)
        self.assertIn("not a sensor reading", air["resolution_note"])

    def test_provider_error_payload_is_not_misread_as_empty_forecast(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"error": True, "reason": "Invalid hourly parameter"})

        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await OpenMeteoForecast(client).fetch_many([(19.1, 72.9)])

        with self.assertRaisesRegex(ProviderError, "Invalid hourly parameter"):
            asyncio.run(run())

    def test_coordinate_batch_size_is_bounded(self) -> None:
        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))) as client:
                points = [(0.0, 0.0)] * 100
                with self.assertRaises(ValueError):
                    await OpenMeteoForecast(client).fetch_many(points)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
