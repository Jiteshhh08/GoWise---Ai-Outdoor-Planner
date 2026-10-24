import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles

from .model.local_model import LocalLanguageModel, ModelNotReadyError
from .schemas import HealthResponse, RecommendationRequest, RecommendationResponse
from .providers.http import make_http_client
from .services.recommendations import RecommendationService

APP_VERSION = "0.1.0"

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    client = make_http_client()
    model = LocalLanguageModel()
    application.state.model = model
    application.state.provider_client = client
    application.state.recommendation_service = RecommendationService(client, model)

    async def load_model() -> None:
        try:
            await model.load()
            application.state.model_ready = True
        except Exception as error:
            application.state.model_ready = False
            application.state.model_error = type(error).__name__

    loader = asyncio.create_task(load_model())
    try:
        yield
    finally:
        if not loader.done():
            loader.cancel()
        await client.aclose()


app = FastAPI(
    title="GoWise Outdoor Planner API",
    description="Evidence-grounded outdoor activity recommendations.",
    version=APP_VERSION,
    lifespan=lifespan,
)
app.state.model_ready = False
app.state.recommendation_service = None


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health(request: Request) -> HealthResponse:
    model_ready = bool(request.app.state.model_ready)
    return HealthResponse(
        status="ready" if model_ready else "not_ready",
        model_ready=model_ready,
        version=APP_VERSION,
    )


@app.post(
    "/api/recommendations",
    response_model=RecommendationResponse,
    tags=["recommendations"],
)
async def recommendations(
    payload: RecommendationRequest,
    request: Request,
) -> RecommendationResponse:
    service = request.app.state.recommendation_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The recommendation service is not ready yet.",
        )
    try:
        return await service.recommend(payload.question)
    except ModelNotReadyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The local language model is not ready yet.",
        ) from error


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
