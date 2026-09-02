from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ObjectiveRequest(BaseModel):
    objective: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Natural-language anomaly detection objective.",
    )


class ObjectiveColumn(BaseModel):
    column: str
    role: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = ""


class ObjectiveUnderstanding(BaseModel):
    original_objective: str

    interpreted_objective: str

    anomaly_type: str
    anomaly_type_confidence: float = Field(ge=0.0, le=1.0)
    anomaly_type_reason: str

    comparison_scope: str
    comparison_scope_confidence: float = Field(ge=0.0, le=1.0)
    comparison_scope_reason: str

    detection_behavior: str
    detection_behavior_reason: str

    temporal_requirement: str
    temporal_requirement_reason: str

    target_columns: list[ObjectiveColumn] = Field(default_factory=list)
    reference_columns: list[ObjectiveColumn] = Field(default_factory=list)
    context_columns: list[ObjectiveColumn] = Field(default_factory=list)

    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ScoreDetail(BaseModel):
    factor: str
    score: float
    maximum: float
    reason: str


class ModelRecommendation(BaseModel):
    rank: int
    model: str

    statistical_score: float
    statistical_maximum: float = 70.0

    objective_score: float
    objective_maximum: float = 30.0

    final_score: float
    final_maximum: float = 100.0

    recommendation_reason: str

    statistical_details: list[ScoreDetail] = Field(default_factory=list)
    objective_details: list[ScoreDetail] = Field(default_factory=list)


class Phase4AnalysisResponse(BaseModel):
    dataset_id: str
    objective: ObjectiveUnderstanding

    recommendations: list[ModelRecommendation]

    confirmed: bool = False


class Phase4ConfirmResponse(BaseModel):
    dataset_id: str
    confirmed: bool
    objective: ObjectiveUnderstanding
    recommendations: list[ModelRecommendation]