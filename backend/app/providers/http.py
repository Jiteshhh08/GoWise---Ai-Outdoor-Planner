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
    timeout: float | httpx.Timeout | None = None,
    max_retries: int | None = None,
) -> Any:
    last_error: Exception | None = None
    retries = settings.max_retries if max_retries is None else max_retries
    for attempt in range(retries + 1):
        try:
            response = await client.request(method, url, params=params, data=data, headers=headers, timeout=timeout)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < retries:
                    retry_after = response.headers.get("Retry-After", "")
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        delay = 0.5 * (2**attempt)
                    await asyncio.sleep(max(0.1, min(delay, 3.0)))
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
            if attempt < retries:
                await asyncio.sleep(min(0.5 * (2**attempt), 2.0))

    if last_error:
        raise ProviderError(provider, f"request failed after bounded retries ({type(last_error).__name__})") from last_error
    raise ProviderError(provider, "request failed after bounded retries")
