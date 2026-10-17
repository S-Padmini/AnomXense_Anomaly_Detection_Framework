from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.store import store
from app.db.database import get_db
from app.db.models import ModelRecommendation
from app.schemas.phase5_schema import (
    Phase5ConfirmResponse,
    Phase5Response,
)
from app.services.phase5_service import (
    generate_phase5_recommendations,
)


router = APIRouter(
    prefix="/api/phase5",
    tags=["Phase 5"],
)


def _get_session(dataset_id: str):
    try:
        return store.get(dataset_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found.",
        )


def _persist_phase5_result(
    session,
    result,
    db: Session,
    dataset_id: str,
):
    """Persist Phase 5 recommendations into MODEL_RECOMMENDATIONS."""

    try:
        data = (
            result.model_dump()
            if hasattr(result, "model_dump")
            else result.dict()
            if hasattr(result, "dict")
            else result
        )

        recommendations = (
            data.get("recommendations", [])
            if isinstance(data, dict)
            else []
        )

        recommended_model = (
            data.get("recommended_model")
            if isinstance(data, dict)
            else None
        )

        # Preserve existing in-memory Phase 5 behavior.
        session.phase5_recommendations = recommendations
        session.recommendations = recommendations
        session.model_recommendations = recommendations
        session.phase5_recommended_model = recommended_model

        # ---------------------------------------------------------
        # Replace the current persisted Top 3 for this dataset.
        # ---------------------------------------------------------

        existing_rows = (
            db.query(ModelRecommendation)
            .filter(
                ModelRecommendation.dataset_id == dataset_id
            )
            .all()
        )

        for row in existing_rows:
            db.delete(row)

        db.flush()

        for recommendation in recommendations:

            if not isinstance(recommendation, dict):
                continue

            model_name = str(
                recommendation.get("model")
                or recommendation.get("display_name")
                or ""
            ).strip()

            if not model_name:
                continue

            rank = int(
                recommendation.get("rank", 0) or 0
            )

            statistical_score = float(
                recommendation.get(
                    "statistical_score",
                    0.0,
                )
                or 0.0
            )

            objective_score = float(
                recommendation.get(
                    "objective_score",
                    0.0,
                )
                or 0.0
            )

            final_score = float(
                recommendation.get(
                    "final_score",
                    0.0,
                )
                or 0.0
            )

            is_selected = False

            if isinstance(recommended_model, dict):
                selected_name = str(
                    recommended_model.get("model")
                    or ""
                ).strip()

                is_selected = (
                    selected_name == model_name
                )

            db.add(
                ModelRecommendation(
                    dataset_id=dataset_id,
                    rank=rank,
                    model_name=model_name,
                    statistical_score=statistical_score,
                    objective_score=objective_score,
                    final_score=final_score,
                    is_selected=is_selected,
                )
            )

        db.commit()

    except Exception:
        db.rollback()

        # Preserve existing behavior:
        # recommendation generation must not fail because
        # of a storage compatibility problem.
        pass


@router.post(
    "/{dataset_id}/recommend",
    response_model=Phase5Response,
)
def recommend_models(
    dataset_id: str,
    db: Session = Depends(get_db),
):

    session = _get_session(dataset_id)

    if not session.phase4_objective:
        raise HTTPException(
            status_code=400,
            detail=(
                "Phase 4 objective analysis is not available. "
                "Complete Phase 4 before generating model recommendations."
            ),
        )

    if not session.phase4_confirmed:
        raise HTTPException(
            status_code=400,
            detail=(
                "Phase 4 objective must be confirmed "
                "before generating model recommendations."
            ),
        )

    result = generate_phase5_recommendations(
        session=session,
        dataset_id=dataset_id,
    )

    _persist_phase5_result(
        session,
        result,
        db,
        dataset_id,
    )

    return result


@router.get(
    "/{dataset_id}",
    response_model=Phase5Response,
)
def get_phase5(
    dataset_id: str,
    db: Session = Depends(get_db),
):

    session = _get_session(dataset_id)

    if not session.phase4_objective:
        raise HTTPException(
            status_code=400,
            detail="Phase 4 objective analysis is not available.",
        )

    result = generate_phase5_recommendations(
        session=session,
        dataset_id=dataset_id,
    )

    _persist_phase5_result(
        session,
        result,
        db,
        dataset_id,
    )

    return result


@router.post(
    "/{dataset_id}/confirm",
    response_model=Phase5ConfirmResponse,
)
def confirm_phase5(
    dataset_id: str,
    db: Session = Depends(get_db),
):

    session = _get_session(dataset_id)

    if not session.phase4_objective:
        raise HTTPException(
            status_code=400,
            detail="Phase 4 objective analysis is not available.",
        )

    result = generate_phase5_recommendations(
        session=session,
        dataset_id=dataset_id,
    )

    _persist_phase5_result(
        session,
        result,
        db,
        dataset_id,
    )

    recommended_model = (
        result.get("recommended_model")
        if isinstance(result, dict)
        else getattr(result, "recommended_model", None)
    )

    if not recommended_model:
        raise HTTPException(
            status_code=400,
            detail="No model recommendation could be generated.",
        )

    return {
        "dataset_id": dataset_id,
        "confirmed": True,
        "recommended_model": recommended_model,
        "recommendations": (
            result.get("recommendations", [])
            if isinstance(result, dict)
            else getattr(result, "recommendations", [])
        ),
        "objective": (
            result.get("objective")
            if isinstance(result, dict)
            else getattr(result, "objective", None)
        ),
    }