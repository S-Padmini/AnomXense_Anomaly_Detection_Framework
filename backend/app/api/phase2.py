from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.store import store
from app.db.database import get_db
from app.db.models import DatasetColumn
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
        raise HTTPException(
            status_code=404,
            detail="Dataset session not found.",
        ) from exc


def _update_selected_columns(
    db: Session,
    dataset_id: str,
    selected_columns: list[str],
) -> None:
    """
    Persist the Phase 2 column selection in DATASET_COLUMNS.

    selected = True  -> column selected by the user
    selected = False -> column not selected by the user
    """

    selected_set = {
        str(column)
        for column in selected_columns
    }

    # --------------------------------------------------------
    # First mark every column for this dataset as unselected.
    # --------------------------------------------------------

    db.execute(
        update(DatasetColumn)
        .where(
            DatasetColumn.dataset_id == dataset_id
        )
        .values(selected=False)
    )

    # --------------------------------------------------------
    # Then mark only the selected columns as selected.
    # --------------------------------------------------------

    if selected_set:

        for column_name in selected_set:

            db.execute(
                update(DatasetColumn)
                .where(
                    DatasetColumn.dataset_id == dataset_id,
                    DatasetColumn.column_name == column_name,
                )
                .values(selected=True)
            )

    db.commit()


@router.get("/{dataset_id}/columns")
def available_columns(
    dataset_id: str,
):
    session = _session(dataset_id)

    return {
        "dataset_id": dataset_id,
        "total_columns": len(
            session.dataframe.columns
        ),
        "selected_columns": session.selected_columns,
        "columns": session.summary["column_details"],
    }


@router.get(
    "/{dataset_id}/column/{column_name:path}"
)
def column_details(
    dataset_id: str,
    column_name: str,
):
    session = _session(dataset_id)

    if column_name not in session.dataframe.columns:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Column '{column_name}' "
                f"not found."
            ),
        )

    return {
        "dataset_id": dataset_id,
        "column": column_name,
        "details": describe_column_on_demand(
            session.dataframe,
            session.summary,
            column_name,
        ),
    }


@router.post("/{dataset_id}/selection")
def select_columns(
    dataset_id: str,
    request: ColumnSelectionRequest,
    db: Session = Depends(get_db),
):
    session = _session(dataset_id)

    try:
        selected = validate_selection(
            session.dataframe,
            request.selected_columns,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    # --------------------------------------------------------
    # EXISTING PHASE 2 BEHAVIOR
    # --------------------------------------------------------

    session.selected_columns = selected
    session.confirmed = False
    session.preprocessed_df = None
    session.preprocess_result = None
    session.statistical_result = None

    # --------------------------------------------------------
    # PERSIST SELECTION TO DATABASE
    # --------------------------------------------------------

    try:

        _update_selected_columns(
            db=db,
            dataset_id=dataset_id,
            selected_columns=selected,
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Column selection was updated in the "
                "session, but could not be saved to "
                f"the database: {exc}"
            ),
        ) from exc

    return build_selection_response(
        session.dataframe,
        session.summary,
        selected,
    ) | {
        "dataset_id": dataset_id,
        "confirmed": False,
    }


@router.post("/{dataset_id}/confirm")
def confirm_selection(
    dataset_id: str,
    request: ColumnSelectionRequest,
    db: Session = Depends(get_db),
):
    session = _session(dataset_id)

    try:
        selected = validate_selection(
            session.dataframe,
            request.selected_columns,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not selected:

        raise HTTPException(
            status_code=400,
            detail="Select at least one column.",
        )

    # --------------------------------------------------------
    # EXISTING PHASE 2 BEHAVIOR
    # --------------------------------------------------------

    # Store ONLY the confirmed Phase 2 columns
    session.selected_columns = selected
    session.confirmed = True

    # Clear downstream results because the selection may have changed
    session.preprocessed_df = None
    session.preprocess_result = None
    session.statistical_result = None

    # --------------------------------------------------------
    # PERSIST CONFIRMED SELECTION TO DATABASE
    # --------------------------------------------------------

    try:

        _update_selected_columns(
            db=db,
            dataset_id=dataset_id,
            selected_columns=selected,
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Column selection was confirmed in the "
                "session, but could not be saved to "
                f"the database: {exc}"
            ),
        ) from exc

    return {
        "dataset_id": dataset_id,
        "confirmed": True,
        "selected_columns": selected,
        "selected_count": len(selected),
        "next_actions": [
            "Proceed to Preprocessing",
            "Edit Column Selection",
        ],
    }