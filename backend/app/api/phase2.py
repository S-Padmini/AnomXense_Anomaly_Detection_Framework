from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.store import store
from app.phases.phase2.column_selection import (
    build_selection_response,
    describe_column_on_demand,
    validate_selection,
)
from app.schemas.phase2_schema import ColumnSelectionRequest

router = APIRouter(prefix="/api/phase2", tags=["Phase 2"])


def _session(dataset_id: str):
    try:
        return store.get(dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Dataset session not found.") from exc


@router.get("/{dataset_id}/columns")
def available_columns(dataset_id: str):
    session = _session(dataset_id)
    return {
        "dataset_id": dataset_id,
        "total_columns": len(session.dataframe.columns),
        "selected_columns": session.selected_columns,
        "columns": session.summary["column_details"],
    }


@router.get("/{dataset_id}/column/{column_name:path}")
def column_details(dataset_id: str, column_name: str):
    session = _session(dataset_id)
    if column_name not in session.dataframe.columns:
        raise HTTPException(status_code=404, detail=f"Column '{column_name}' not found.")
    return {
        "dataset_id": dataset_id,
        "column": column_name,
        "details": describe_column_on_demand(
            session.dataframe, session.summary, column_name
        ),
    }


@router.post("/{dataset_id}/selection")
def select_columns(dataset_id: str, request: ColumnSelectionRequest):
    session = _session(dataset_id)
    try:
        selected = validate_selection(session.dataframe, request.selected_columns)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session.selected_columns = selected
    session.confirmed = False
    session.preprocessed_df = None
    session.preprocess_result = None
    session.statistical_result = None

    return build_selection_response(
        session.dataframe, session.summary, selected
    ) | {"dataset_id": dataset_id, "confirmed": False}


@router.post("/{dataset_id}/confirm")
def confirm_selection(dataset_id: str):
    session = _session(dataset_id)
    if not session.selected_columns:
        raise HTTPException(status_code=400, detail="Select at least one column.")
    session.confirmed = True
    return {
        "dataset_id": dataset_id,
        "confirmed": True,
        "selected_columns": session.selected_columns,
        "selected_count": len(session.selected_columns),
        "next_actions": ["Proceed to Preprocessing", "Edit Column Selection"],
    }
