from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.phases.phase4.recommendation import recommend_models


router = APIRouter(
    prefix="/api/phase5",
    tags=["Phase 5 - Model Recommendation"],
)


class RecommendationRequest(BaseModel):
    dataset_id: str

    statistical_profile: dict[str, Any] = Field(
        default_factory=dict
    )

    interpretation: dict[str, Any] = Field(
        default_factory=dict
    )

    column_profiles: dict[str, dict[str, Any]] = Field(
        default_factory=dict
    )

    top_n: int = Field(
        default=3,
        ge=1,
        le=10,
    )


@router.post("/recommend")
def recommend(req: RecommendationRequest):

    try:

        recommendations = recommend_models(
            statistical_profile=req.statistical_profile,
            interpretation=req.interpretation,
            column_profiles=req.column_profiles,
            top_n=req.top_n,
        )

        return {
            "success": True,

            "dataset_id": req.dataset_id,

            "recommendations": recommendations,

            "recommended_models": recommendations,

            "models": recommendations,

            "count": len(recommendations),

            "message": (
                "Models were ranked using Phase 3 "
                "dataset characteristics and the "
                "Phase 4 detection objective."
            ),
        }

    except KeyError as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid recommendation configuration: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                "Phase 5 recommendation failed: "
                f"{exc}"
            ),
        ) from exc