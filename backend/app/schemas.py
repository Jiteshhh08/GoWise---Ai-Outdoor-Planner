from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=5, max_length=500)

    @field_validator("question")
    @classmethod
    def question_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Please enter a little more detail.")
        return value


class InterpretedQuery(BaseModel):
    activity: str | None = None
    location_label: str | None = None
    radius_km: float | None = Field(default=None, ge=0.1, le=100)
    start_time: datetime | None = None
    end_time: datetime | None = None
    profile_flags: list[str] = Field(default_factory=list)


class ScoreFactor(BaseModel):
    name: str
    label: str | None = None
    value: int | float | str | None = None
    score: float | None = Field(default=None, ge=0, le=100)
    weight: float | None = Field(default=None, ge=0, le=1)
    explanation: str | None = None
    available: bool = True


class RecommendationOption(BaseModel):
    place_id: str
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    time: datetime
    suitability_score: float = Field(ge=0, le=100)
    score_factors: list[ScoreFactor] = Field(default_factory=list)
    explanation: str


class Advice(BaseModel):
    carry: list[str] = Field(default_factory=list)
    watch_for: list[str] = Field(default_factory=list)
    avoid_if: list[str] = Field(default_factory=list)


class EvidenceRecord(BaseModel):
    claim: str
    value: str | float | int | None
    unit: str | None = None
    source: str
    source_url: str | None = None
    observed_for: datetime | None = None
    fetched_at: datetime | None = None
    location: dict[str, float] | None = None


class DataSource(BaseModel):
    name: str
    url: str | None = None
    note: str | None = None


class RecommendationResponse(BaseModel):
    status: Literal["ok", "partial", "needs_clarification", "no_results"]
    interpreted_query: InterpretedQuery | None = None
    recommendation: RecommendationOption | None = None
    alternatives: list[RecommendationOption] = Field(default_factory=list)
    advice: Advice = Field(default_factory=Advice)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    data_sources: list[DataSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    coverage: float | None = Field(default=None, ge=0, le=1)


class HealthResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    model_ready: bool
    version: str
