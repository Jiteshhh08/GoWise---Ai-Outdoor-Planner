from fastapi import FastAPI, HTTPException, Request, status

from .schemas import HealthResponse, RecommendationRequest, RecommendationResponse

APP_VERSION = "0.1.0"

app = FastAPI(
    title="GoWise Outdoor Planner API",
    description="Evidence-grounded outdoor activity recommendations.",
    version=APP_VERSION,
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
    return await service.recommend(payload.question)
