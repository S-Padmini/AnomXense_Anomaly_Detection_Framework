from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ScoreDetail(BaseModel):
    """
    One score item shown inside the Phase 5
    Statistical or Objective score breakdown.

    Only the test/component name and score are
    required for the Phase 5 UI.
    """

    factor: Optional[str] = None
    name: Optional[str] = None

    score: float = 0.0
    maximum: float = 0.0
    max_score: Optional[float] = None


class ModelRecommendation(BaseModel):
    model: str

    display_name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None

    statistical_score: float = 0.0
    statistical_maximum: float = 70.0
    statistical_max_score: Optional[float] = 70.0

    objective_score: float = 0.0
    objective_maximum: float = 30.0
    objective_max_score: Optional[float] = 30.0

    final_score: float = 0.0
    final_maximum: float = 100.0
    final_max_score: Optional[float] = 100.0

    statistical_details: List[ScoreDetail] = Field(
        default_factory=list
    )

    objective_details: List[ScoreDetail] = Field(
        default_factory=list
    )

    rank: Optional[int] = None


class Phase5Response(BaseModel):
    dataset_id: str

    recommended_model: Optional[ModelRecommendation] = None

    # Only Top 3 models are returned.
    recommendations: List[ModelRecommendation] = Field(
        default_factory=list
    )

    statistical_maximum: float = 70.0
    objective_maximum: float = 30.0
    final_maximum: float = 100.0

    objective: Optional[Any] = None

    generated: bool = True


class Phase5ConfirmResponse(BaseModel):
    dataset_id: str

    confirmed: bool

    recommended_model: Optional[ModelRecommendation] = None

    # Only Top 3 models are returned.
    recommendations: List[ModelRecommendation] = Field(
        default_factory=list
    )

    objective: Optional[Any] = None