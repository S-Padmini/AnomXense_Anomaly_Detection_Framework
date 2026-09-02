from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.store import store
from app.phases.phase4.objective_matcher import (
    validate_objective_match,
)
from app.phases.phase4.objective_parser import (
    parse_objective,
)
from app.phases.phase4.recommendation import (
    recommend_models,
)
from app.schemas.phase4_schema import (
    ObjectiveRequest,
    Phase4AnalysisResponse,
    Phase4ConfirmResponse,
)


router = APIRouter(
    prefix="/api/phase4",
    tags=["Phase 4 - Objective Understanding"],
)


def _get_column_profiles(session) -> dict:
    """
    Extract Phase 1 column profiles without assuming one exact
    schema shape.
    """

    summary = session.summary or {}

    profiles = (
        summary.get("column_profiles")
        or summary.get("columns")
        or {}
    )

    if isinstance(profiles, list):
        result = {}

        for item in profiles:
            if not isinstance(item, dict):
                continue

            name = (
                item.get("name")
                or item.get("column")
                or item.get("column_name")
            )

            if name:
                result[str(name)] = item

        return result

    if isinstance(profiles, dict):
        return {
            str(key): value
            for key, value in profiles.items()
            if isinstance(value, dict)
        }

    return {}


def _get_phase3_statistics(session) -> dict:
    result = session.statistical_result

    if isinstance(result, dict):
        return result

    return {}


def _selected_columns(session) -> list[str]:

    columns = list(
        session.selected_columns or []
    )

    if not columns:
        raise HTTPException(
            status_code=400,
            detail=(
                "No columns are selected. Complete Phase 2 "
                "column selection first."
            ),
        )

    if not session.confirmed:
        raise HTTPException(
            status_code=400,
            detail=(
                "Phase 2 column selection has not been confirmed."
            ),
        )

    return columns


def _run_phase4(
    session,
    objective: str,
) -> tuple[dict, list[dict]]:

    selected_columns = _selected_columns(
        session
    )

    column_profiles = _get_column_profiles(
        session
    )

    statistics = _get_phase3_statistics(
        session
    )

    interpretation = parse_objective(
        objective=objective,
        selected_columns=selected_columns,
        column_profiles=column_profiles,
        phase3_statistics=statistics,
    )

    interpretation = validate_objective_match(
        interpretation=interpretation,
        selected_columns=selected_columns,
        column_profiles=column_profiles,
        phase3_statistics=statistics,
    )

    recommendations = recommend_models(
        statistical_profile=statistics,
        interpretation=interpretation,
        column_profiles=column_profiles,
        top_n=3,
    )

    return interpretation, recommendations


@router.post(
    "/{dataset_id}/analyze",
    response_model=Phase4AnalysisResponse,
)
def analyze_objective(
    dataset_id: str,
    payload: ObjectiveRequest,
):

    try:
        session = store.get(dataset_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Dataset session not found or expired.",
        )

    objective = payload.objective.strip()

    if len(objective) < 5:
        raise HTTPException(
            status_code=400,
            detail=(
                "Please provide a meaningful detection objective."
            ),
        )

    try:
        interpretation, recommendations = _run_phase4(
            session,
            objective,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Phase 4 analysis failed: {str(exc)}",
        ) from exc

    # Store the result directly in the existing session.
    session.phase4_objective = interpretation
    session.phase4_recommendations = recommendations
    session.phase4_confirmed = False
    session.touch()

    return {
        "dataset_id": dataset_id,
        "objective": interpretation,
        "recommendations": recommendations,
        "confirmed": False,
    }


@router.post(
    "/{dataset_id}/confirm",
    response_model=Phase4ConfirmResponse,
)
def confirm_phase4(
    dataset_id: str,
):

    try:
        session = store.get(dataset_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Dataset session not found or expired.",
        )

    objective = getattr(
        session,
        "phase4_objective",
        None,
    )

    recommendations = getattr(
        session,
        "phase4_recommendations",
        None,
    )

    if not objective or not recommendations:
        raise HTTPException(
            status_code=400,
            detail=(
                "Phase 4 has not been analyzed yet. "
                "Analyze the detection objective first."
            ),
        )

    session.phase4_confirmed = True
    session.touch()

    return {
        "dataset_id": dataset_id,
        "confirmed": True,
        "objective": objective,
        "recommendations": recommendations,
    }


@router.get(
    "/{dataset_id}",
    response_model=Phase4AnalysisResponse,
)
def get_phase4_result(
    dataset_id: str,
):

    try:
        session = store.get(dataset_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Dataset session not found or expired.",
        )

    objective = getattr(
        session,
        "phase4_objective",
        None,
    )

    recommendations = getattr(
        session,
        "phase4_recommendations",
        None,
    )

    if not objective or not recommendations:
        raise HTTPException(
            status_code=404,
            detail="No Phase 4 result exists for this dataset.",
        )

    return {
        "dataset_id": dataset_id,
        "objective": objective,
        "recommendations": recommendations,
        "confirmed": getattr(
            session,
            "phase4_confirmed",
            False,
        ),
    }

    