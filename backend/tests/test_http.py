import asyncio
import unittest

import httpx

from app.providers.http import ProviderError, request_json


class ProviderHttpTests(unittest.TestCase):
    def test_retries_a_rate_limit_with_a_bounded_attempt_count(self) -> None:
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(429)
            return httpx.Response(200, json={"ok": True})

        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await request_json(client, "Mock provider", "GET", "https://provider.invalid/data")

        self.assertEqual(asyncio.run(run()), {"ok": True})
        self.assertEqual(attempts, 2)

    def test_surfaces_final_http_error_with_provider_name(self) -> None:
        async def run():
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(lambda request: httpx.Response(502))
            ) as client:
                await request_json(client, "Mock provider", "GET", "https://provider.invalid/data")

        with self.assertRaisesRegex(ProviderError, "Mock provider.*HTTP 502"):
            asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
