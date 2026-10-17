from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.store import store
from app.db.database import get_db
from app.db.models import Objective
from app.phases.phase4.objective_parser import parse_objective
from app.phases.phase4.objective_matcher import validate_objective_match
from app.schemas.phase4_schema import (
    ObjectiveRequest,
    Phase4AnalysisResponse,
    Phase4ConfirmResponse,
)


router = APIRouter(
    prefix="/api/phase4",
    tags=["Phase 4 - Objective Understanding"],
)


# ============================================================
# SESSION HELPER
# ============================================================

def _get_session(dataset_id: str):
    try:
        return store.get(dataset_id)

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail="Dataset session not found.",
        ) from exc


# ============================================================
# COLUMN RESPONSE HELPERS
# ============================================================

def _column_to_response(column):

    if isinstance(column, dict):

        name = (
            column.get("column")
            or column.get("name")
            or column.get("column_name")
        )

        reason = (
            column.get("reason")
            or column.get("evidence")
            or column.get("explanation")
            or column.get("why_relevant")
            or ""
        )

        confidence = column.get("confidence")

        evidence = column.get("evidence")

        role = column.get(
            "role",
            "detection_feature",
        )

        return {
            "column": name,
            "role": role,
            "reason": reason,
            "confidence": confidence,
            "evidence": evidence,
        }

    return {
        "column": str(column),
        "role": "detection_feature",
        "reason": "",
        "confidence": None,
        "evidence": None,
    }


def _normalize_columns(columns):

    normalized = []

    for column in columns or []:

        if not column:
            continue

        item = _column_to_response(
            column
        )

        if not item.get("column"):
            continue

        normalized.append(item)

    return normalized


def _column_names(columns):

    return [
        str(item.get("column"))
        for item in columns or []
        if item.get("column")
    ]


# ============================================================
# COLUMN PROFILE RESOLUTION
# ============================================================

def _get_column_profiles(session):

    profiles = (
        getattr(
            session,
            "column_profiles",
            None,
        )
        or getattr(
            session,
            "profiles",
            None,
        )
    )

    if isinstance(
        profiles,
        dict,
    ) and profiles:

        return profiles

    summary = getattr(
        session,
        "summary",
        {},
    ) or {}

    column_details = summary.get(
        "column_details",
        {},
    )

    if isinstance(
        column_details,
        dict,
    ):

        return column_details

    return {}


# ============================================================
# OBJECTIVE UNDERSTANDING
# ============================================================

def _build_objective_understanding(
    *,
    original_objective,
    validated_objective,
    interpreted_objective,
    anomaly_type,
    anomaly_type_confidence,
    anomaly_type_reason,
    target_columns,
    reference_columns,
    context_columns,
):

    return {
        "original_objective":
            original_objective,

        "interpreted_objective":
            interpreted_objective,

        "anomaly_type":
            anomaly_type,

        "anomaly_type_confidence":
            anomaly_type_confidence,

        "anomaly_type_reason":
            anomaly_type_reason,

        "comparison_scope":
            (
                validated_objective.get(
                    "comparison_scope"
                )
                or "none"
            ),

        "comparison_scope_confidence":
            validated_objective.get(
                "comparison_scope_confidence"
            ),

        "comparison_scope_reason":
            (
                validated_objective.get(
                    "comparison_scope_reason"
                )
                or ""
            ),

        "detection_behavior":
            (
                validated_objective.get(
                    "detection_behavior"
                )
                or ""
            ),

        "detection_behavior_reason":
            (
                validated_objective.get(
                    "detection_behavior_reason"
                )
                or ""
            ),

        "temporal_requirement":
            (
                validated_objective.get(
                    "temporal_requirement"
                )
                or "unclear"
            ),

        "temporal_requirement_reason":
            (
                validated_objective.get(
                    "temporal_requirement_reason"
                )
                or ""
            ),

        # Existing semantic fields.
        "target_columns":
            target_columns,

        "reference_columns":
            reference_columns,

        "context_columns":
            context_columns,

        "attributes_involved":
            _normalize_columns(
                validated_objective.get(
                    "attributes_involved",
                    [],
                )
            ),

        # ----------------------------------------------------
        # EXISTING DYNAMIC VALIDATION
        # ----------------------------------------------------

        "attribute_selection_valid":
            bool(
                validated_objective.get(
                    "attribute_selection_valid",
                    True,
                )
            ),

        "missing_attributes":
            list(
                validated_objective.get(
                    "missing_attributes",
                    [],
                )
                or []
            ),

        "assumptions":
            (
                validated_objective.get(
                    "assumptions",
                    [],
                )
                or []
            ),

        "warnings":
            (
                validated_objective.get(
                    "warnings",
                    [],
                )
                or []
            ),
    }


# ============================================================
# DATABASE PERSISTENCE HELPERS
# ============================================================

def _save_objective(
    db: Session,
    *,
    dataset_id: str,
    objective: dict,
    confirmed: bool,
) -> Objective:
    """
    Persist the current Phase 4 objective interpretation
    into OBJECTIVES.

    Analyze creates/updates the objective with confirmed=False.
    Confirm updates the same latest objective to confirmed=True.
    """

    anomaly_scope = (
        objective.get("anomaly_scope")
        or objective.get("comparison_scope")
        or "none"
    )

    target_columns = _column_names(
        objective.get("target_columns", [])
    )

    attributes_involved = _column_names(
        objective.get("attributes_involved", [])
    )

    existing = (
        db.query(Objective)
        .filter(
            Objective.dataset_id == dataset_id
        )
        .order_by(
            Objective.objective_id.desc()
        )
        .first()
    )

    if existing is None:

        existing = Objective(
            dataset_id=dataset_id,
            original_objective=str(
                objective.get(
                    "original_objective",
                    "",
                )
            ),
            interpreted_objective=str(
                objective.get(
                    "interpreted_objective",
                    "",
                )
            ),
            anomaly_type=str(
                objective.get(
                    "anomaly_type",
                    "point",
                )
            ),
            anomaly_scope=str(
                anomaly_scope
            ),
            target_columns=target_columns,
            attributes_involved=attributes_involved,
            confirmed=confirmed,
        )

        db.add(existing)

    else:

        existing.original_objective = str(
            objective.get(
                "original_objective",
                existing.original_objective,
            )
        )

        existing.interpreted_objective = str(
            objective.get(
                "interpreted_objective",
                existing.interpreted_objective,
            )
        )

        existing.anomaly_type = str(
            objective.get(
                "anomaly_type",
                existing.anomaly_type,
            )
        )

        existing.anomaly_scope = str(
            anomaly_scope
        )

        existing.target_columns = (
            target_columns
        )

        existing.attributes_involved = (
            attributes_involved
        )

        existing.confirmed = confirmed

    db.commit()
    db.refresh(existing)

    return existing


# ============================================================
# PHASE 4 ANALYZE
# ============================================================

@router.post(
    "/{dataset_id}/analyze",
    response_model=Phase4AnalysisResponse,
)
async def analyze_phase4_objective(
    dataset_id: str,
    request: ObjectiveRequest,
    db: Session = Depends(get_db),
):

    session = _get_session(
        dataset_id
    )

    if not getattr(
        session,
        "confirmed",
        False,
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Please complete and confirm the "
                "previous phases before continuing "
                "to Phase 4."
            ),
        )

    selected_columns = getattr(
        session,
        "selected_columns",
        None,
    )

    if not selected_columns:

        raise HTTPException(
            status_code=400,
            detail=(
                "No columns have been selected. "
                "Please complete Phase 2 first."
            ),
        )

    objective = (
        request.objective.strip()
        if request.objective
        else ""
    )

    if not objective:

        raise HTTPException(
            status_code=400,
            detail=(
                "Please enter your detection objective."
            ),
        )

    if len(objective) < 5:

        raise HTTPException(
            status_code=400,
            detail=(
                "Please provide a little more detail "
                "about what you want to detect."
            ),
        )

    # --------------------------------------------------------
    # PHASE 1 PROFILES
    # --------------------------------------------------------

    column_profiles = _get_column_profiles(
        session
    )

    # --------------------------------------------------------
    # PHASE 3 STATISTICS
    # --------------------------------------------------------

    phase3_statistics = (
        getattr(
            session,
            "statistical_analysis",
            None,
        )
        or getattr(
            session,
            "statistics",
            None,
        )
        or {}
    )

    # --------------------------------------------------------
    # COMPLETE DATASET COLUMN LIST
    # --------------------------------------------------------

    dataset_columns = [
        str(column)
        for column in session.dataframe.columns
    ]

    # --------------------------------------------------------
    # OBJECTIVE PARSING
    # --------------------------------------------------------

    try:

        parsed_objective = parse_objective(
            objective=objective,
            selected_columns=selected_columns,
            available_columns=dataset_columns,
            column_profiles=column_profiles,
            phase3_statistics=phase3_statistics,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to understand the objective "
                f"using the language model: {str(exc)}"
            ),
        ) from exc

    if not parsed_objective:

        raise HTTPException(
            status_code=502,
            detail=(
                "The language model returned an "
                "empty objective interpretation."
            ),
        )

    # --------------------------------------------------------
    # DETERMINISTIC VALIDATION
    # --------------------------------------------------------

    try:

        validated_objective = validate_objective_match(
            interpretation=parsed_objective,
            selected_columns=selected_columns,
            column_profiles=column_profiles,
            phase3_statistics=phase3_statistics,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to validate the objective "
                f"interpretation: {str(exc)}"
            ),
        ) from exc

    if not validated_objective:

        raise HTTPException(
            status_code=500,
            detail=(
                "Objective validation returned "
                "an empty result."
            ),
        )

    interpreted_objective = (
        validated_objective.get(
            "interpreted_objective"
        )
        or objective
    )

    anomaly_type = (
        validated_objective.get(
            "anomaly_type"
        )
        or "point"
    )

    anomaly_type_confidence = (
        validated_objective.get(
            "anomaly_type_confidence"
        )
    )

    anomaly_type_reason = (
        validated_objective.get(
            "anomaly_type_reason"
        )
        or ""
    )

    normalized_detection_columns = (
        _normalize_columns(
            validated_objective.get(
                "target_columns",
                [],
            )
        )
    )

    normalized_reference_columns = (
        _normalize_columns(
            validated_objective.get(
                "reference_columns",
                [],
            )
        )
    )

    normalized_context_columns = (
        _normalize_columns(
            validated_objective.get(
                "context_columns",
                [],
            )
        )
    )

    objective_understanding = (
        _build_objective_understanding(
            original_objective=objective,
            validated_objective=validated_objective,
            interpreted_objective=interpreted_objective,
            anomaly_type=anomaly_type,
            anomaly_type_confidence=anomaly_type_confidence,
            anomaly_type_reason=anomaly_type_reason,
            target_columns=normalized_detection_columns,
            reference_columns=normalized_reference_columns,
            context_columns=normalized_context_columns,
        )
    )

    # --------------------------------------------------------
    # STORE CURRENT PHASE 4 STATE
    # --------------------------------------------------------

    session.phase4_objective = (
        objective_understanding
    )

    session.phase4_recommendations = []

    session.phase4_analyzed = True

    # Every new objective analysis must be confirmed again.
    session.phase4_confirmed = False

    # --------------------------------------------------------
    # SAVE OBJECTIVE TO DATABASE
    # --------------------------------------------------------

    try:

        _save_objective(
            db=db,
            dataset_id=dataset_id,
            objective=objective_understanding,
            confirmed=False,
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Objective analysis completed, but "
                "the result could not be saved to the "
                f"database: {exc}"
            ),
        ) from exc

    return {
        "dataset_id": dataset_id,

        "objective":
            objective_understanding,

        "recommendations": [],

        "confirmed": False,
    }


# ============================================================
# PHASE 4 CONFIRM
# ============================================================

@router.post(
    "/{dataset_id}/confirm",
    response_model=Phase4ConfirmResponse,
)
async def confirm_phase4_objective(
    dataset_id: str,
    db: Session = Depends(get_db),
):

    session = _get_session(
        dataset_id
    )

    if not getattr(
        session,
        "phase4_analyzed",
        False,
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Please analyze your objective "
                "before confirming Phase 4."
            ),
        )

    phase4_objective = getattr(
        session,
        "phase4_objective",
        None,
    )

    if not phase4_objective:

        raise HTTPException(
            status_code=400,
            detail=(
                "No Phase 4 objective interpretation "
                "is available."
            ),
        )

    # --------------------------------------------------------
    # HARD BACKEND GATE
    # --------------------------------------------------------

    if not phase4_objective.get(
        "attribute_selection_valid",
        True,
    ):

        missing = phase4_objective.get(
            "missing_attributes",
            [],
        )

        missing_text = (
            ", ".join(
                str(column)
                for column in missing
            )
            if missing
            else "one or more required attributes"
        )

        raise HTTPException(
            status_code=409,
            detail=(
                "Phase 4 cannot be confirmed because "
                "the following objective-required "
                "attribute(s) are missing from the "
                "confirmed Phase 2 selection: "
                f"{missing_text}. "
                "Please return to Phase 2, select the "
                "required attribute(s), confirm the "
                "selection, complete Phase 3 preprocessing "
                "and statistical analysis, then return "
                "to Phase 4."
            ),
        )

    session.phase4_confirmed = True

    # --------------------------------------------------------
    # UPDATE OBJECTIVE CONFIRMATION IN DATABASE
    # --------------------------------------------------------

    try:

        _save_objective(
            db=db,
            dataset_id=dataset_id,
            objective=phase4_objective,
            confirmed=True,
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Phase 4 was confirmed, but the "
                "confirmation could not be saved to the "
                f"database: {exc}"
            ),
        ) from exc

    return {
        "dataset_id":
            dataset_id,

        "confirmed":
            True,

        "objective":
            phase4_objective,

        "recommendations": [],
    }


# ============================================================
# GET PHASE 4 OBJECTIVE
# ============================================================

@router.get(
    "/{dataset_id}"
)
async def get_phase4_objective(
    dataset_id: str,
):

    session = _get_session(
        dataset_id
    )

    phase4_objective = getattr(
        session,
        "phase4_objective",
        None,
    )

    if not phase4_objective:

        raise HTTPException(
            status_code=404,
            detail=(
                "Phase 4 objective has not "
                "been analyzed yet."
            ),
        )

    return {
        "dataset_id":
            dataset_id,

        "objective":
            phase4_objective,

        "recommendations":
            getattr(
                session,
                "phase4_recommendations",
                [],
            )
            or [],

        "confirmed":
            getattr(
                session,
                "phase4_confirmed",
                False,
            ),
    }