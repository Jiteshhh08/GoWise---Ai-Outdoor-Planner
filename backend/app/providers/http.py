import asyncio
from typing import Any

import httpx

from ..config import settings


class ProviderError(RuntimeError):
    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"{provider}: {message}")


def make_http_client() -> httpx.AsyncClient:
    timeout = httpx.Timeout(settings.request_timeout_seconds, connect=min(5.0, settings.request_timeout_seconds))
    limits = httpx.Limits(max_connections=8, max_keepalive_connections=4, keepalive_expiry=20)
    return httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        follow_redirects=False,
        headers={"User-Agent": settings.nominatim_user_agent},
    )


async def request_json(
    client: httpx.AsyncClient,
    provider: str,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    last_error: Exception | None = None
    for attempt in range(settings.max_retries + 1):
        try:
            response = await client.request(method, url, params=params, data=data, headers=headers)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < settings.max_retries:
                    await asyncio.sleep(min(0.25 * (2**attempt), 1.0))
                    continue
            response.raise_for_status()
            try:
                return response.json()
            except ValueError as error:
                raise ProviderError(provider, "returned invalid JSON") from error
        except ProviderError:
            raise
        except httpx.HTTPStatusError as error:
            code = error.response.status_code
            raise ProviderError(provider, f"request failed with HTTP {code}") from error
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            last_error = error
            if attempt < settings.max_retries:
                await asyncio.sleep(min(0.25 * (2**attempt), 1.0))

    if last_error:
        raise ProviderError(provider, f"request failed after bounded retries ({type(last_error).__name__})") from last_error
    raise ProviderError(provider, "request failed after bounded retries")
