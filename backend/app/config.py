import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(PROJECT_ROOT / "backend" / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    model_id: str = os.getenv("MODEL_ID", "Qwen/Qwen2.5-1.5B-Instruct")
    model_device: str = os.getenv("MODEL_DEVICE", "auto")
    model_max_input_tokens: int = int(os.getenv("MODEL_MAX_INPUT_TOKENS", "2048"))
    model_max_output_tokens: int = int(os.getenv("MODEL_MAX_OUTPUT_TOKENS", "256"))
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "12"))
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "900"))
    geocode_cache_ttl_seconds: int = int(os.getenv("GEOCODE_CACHE_TTL_SECONDS", "86400"))
    max_search_radius_km: float = float(os.getenv("MAX_SEARCH_RADIUS_KM", "50"))
    default_search_radius_km: float = float(os.getenv("DEFAULT_SEARCH_RADIUS_KM", "10"))
    max_candidates: int = int(os.getenv("MAX_CANDIDATES", "12"))
    max_overpass_features: int = int(os.getenv("MAX_OVERPASS_FEATURES", "1000"))
    max_retries: int = int(os.getenv("MAX_PROVIDER_RETRIES", "2"))
    cache_max_entries: int = int(os.getenv("CACHE_MAX_ENTRIES", "256"))
    nominatim_url: str = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
    nominatim_user_agent: str = os.getenv(
        "NOMINATIM_USER_AGENT",
        "GoWiseOutdoorPlanner/0.1 (https://github.com/Jiteshhh08/GoWise---Ai-Outdoor-Planner)",
    )
    overpass_url: str = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    weather_url: str = os.getenv("OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
    air_quality_url: str = os.getenv(
        "OPEN_METEO_AIR_QUALITY_URL", "https://air-quality-api.open-meteo.com/v1/air-quality"
    )

    def __post_init__(self) -> None:
        if self.request_timeout_seconds <= 0:
            raise ValueError("REQUEST_TIMEOUT_SECONDS must be positive.")
        if self.cache_ttl_seconds < 0 or self.geocode_cache_ttl_seconds < 0:
            raise ValueError("Cache TTL values cannot be negative.")
        if not (0.1 <= self.max_search_radius_km <= 50):
            raise ValueError("MAX_SEARCH_RADIUS_KM must be between 0.1 and 50.")
        if not (0.1 <= self.default_search_radius_km <= 100):
            raise ValueError("DEFAULT_SEARCH_RADIUS_KM must be between 0.1 and 100.")
        if not (1 <= self.max_candidates <= 50):
            raise ValueError("MAX_CANDIDATES must be between 1 and 50.")
        if self.max_overpass_features < 1 or self.max_retries < 0 or self.cache_max_entries < 1:
            raise ValueError("Provider bounds must use positive values.")
        if self.model_max_input_tokens < 256 or self.model_max_output_tokens < 32:
            raise ValueError("Model token bounds are too small for valid extraction.")


settings = Settings()
