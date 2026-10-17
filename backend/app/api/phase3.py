from __future__ import annotations

import io
import json

import pandas as pd
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.store import store
from app.db.database import get_db
from app.db.models import DatasetColumn, PreprocessingRun
from app.phases.phase3.preprocessing import (
    build_preprocessing_inspection,
    preprocess_dataset,
)
from app.phases.phase3.statistical_analysis import analyze_statistics
from app.schemas.phase3_schema import (
    PreprocessRequest,
    StatisticalAnalysisRequest,
)


router = APIRouter(
    prefix="/api/phase3",
    tags=["Phase 3"],
)


# ============================================================
# SESSION HELPERS
# ============================================================


def _session(dataset_id: str):
    """
    Retrieve the in-memory dataset session.
    """

    try:
        return store.get(dataset_id)

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Dataset session not found.",
        ) from exc


def _validate_columns(
    session,
    columns: list[str],
) -> list[str]:
    """
    Validate requested columns against the original
    dataset and preserve the original dataframe order.
    """

    if not columns:
        raise HTTPException(
            status_code=400,
            detail="Select at least one column.",
        )

    unknown = [
        column
        for column in columns
        if column not in session.dataframe.columns
    ]

    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown columns: {unknown}",
        )

    selected_set = set(columns)

    return [
        column
        for column in session.dataframe.columns
        if column in selected_set
    ]


# ============================================================
# JSON HELPERS
# ============================================================


def _json_safe_value(
    value: Any,
) -> Any:
    """
    Convert a Phase 3 value into a JSON-compatible value.
    """

    if value is None:
        return None

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def _store_imputation_value(
    value: Any,
) -> str | None:
    """
    Convert the Phase 3 imputation value into the
    text field used by DATASET_COLUMNS.
    """

    value = _json_safe_value(value)

    if value is None:
        return None

    if isinstance(
        value,
        (dict, list, tuple),
    ):
        return json.dumps(
            value,
            default=str,
        )

    return str(value)


# ============================================================
# DATABASE PERSISTENCE
# ============================================================


def _save_preprocessing_result(
    db: Session,
    *,
    dataset_id: str,
    result: dict[str, Any],
) -> None:
    """
    Persist the Phase 3 preprocessing result.

    DATASET_COLUMNS:
        - missing_after
        - skewness
        - imputation_method
        - imputation_value

    PREPROCESSING_RUNS:
        - rows_before
        - rows_after
        - missing_before
        - missing_after
        - duplicate_records_before
        - duplicate_records_after
        - duplicates_removed
    """

    before = result.get(
        "before",
        {},
    )

    after = result.get(
        "after",
        {},
    )

    actions = result.get(
        "actions",
        {},
    )

    # --------------------------------------------------------
    # Update DATASET_COLUMNS
    # --------------------------------------------------------

    column_records = (
        db.query(DatasetColumn)
        .filter(
            DatasetColumn.dataset_id
            == dataset_id
        )
        .all()
    )

    for column_record in column_records:

        column_name = (
            column_record.column_name
        )

        action = actions.get(
            column_name
        )

        if action is None:
            continue

        missing_before = int(
            column_record.missing_before
            or 0
        )

        missing_handled = int(
            action.get(
                "missing_values_handled",
                0,
            )
            or 0
        )

        missing_after = max(
            0,
            missing_before
            - missing_handled,
        )

        column_record.missing_after = (
            missing_after
        )

        skewness = action.get(
            "skewness"
        )

        column_record.skewness = (
            float(skewness)
            if skewness is not None
            else None
        )

        column_record.imputation_method = (
            str(action["method"])
            if action.get("method")
            is not None
            else None
        )

        column_record.imputation_value = (
            _store_imputation_value(
                action.get(
                    "filled_value"
                )
            )
        )

    # --------------------------------------------------------
    # Create PREPROCESSING_RUNS record
    # --------------------------------------------------------

    preprocessing_record = PreprocessingRun(
        dataset_id=dataset_id,
        rows_before=int(
            before.get(
                "rows",
                0,
            )
        ),
        rows_after=int(
            after.get(
                "rows",
                0,
            )
        ),
        missing_before=int(
            before.get(
                "missing_values",
                0,
            )
        ),
        missing_after=int(
            after.get(
                "missing_values",
                0,
            )
        ),
        duplicate_records_before=int(
            before.get(
                "duplicate_records",
                0,
            )
        ),
        duplicate_records_after=int(
            after.get(
                "duplicate_records",
                0,
            )
        ),
        duplicates_removed=int(
            result.get(
                "duplicate_records_removed",
                0,
            )
        ),
        statistical_analysis=None,
    )

    db.add(
        preprocessing_record
    )

    db.commit()


def _save_statistical_analysis(
    db: Session,
    *,
    dataset_id: str,
    result: dict[str, Any],
) -> None:
    """
    Store the existing Phase 3 statistical analysis
    inside the latest PREPROCESSING_RUNS record.
    """

    preprocessing_record = (
        db.query(PreprocessingRun)
        .filter(
            PreprocessingRun.dataset_id
            == dataset_id
        )
        .order_by(
            PreprocessingRun.preprocessing_id.desc()
        )
        .first()
    )

    if preprocessing_record is None:
        raise RuntimeError(
            "No preprocessing run exists "
            "for this dataset."
        )

    preprocessing_record.statistical_analysis = (
        result
    )

    db.commit()


# ============================================================
# PREPROCESSING INSPECTION
# ============================================================


@router.get(
    "/{dataset_id}/preprocessing/inspection"
)
def preprocessing_inspection(
    dataset_id: str,
):
    """
    Return the Phase 3 preprocessing inspection.
    """

    session = _session(
        dataset_id
    )

    if not session.selected_columns:
        raise HTTPException(
            status_code=400,
            detail="Select at least one column.",
        )

    return build_preprocessing_inspection(
        session.dataframe,
        session.selected_columns,
        session.summary,
    )


@router.get(
    "/{dataset_id}/preprocessing/inspection/missing/{column_name:path}"
)
def missing_values(
    dataset_id: str,
    column_name: str,
):
    """
    Return missing-value details for one column.
    """

    session = _session(
        dataset_id
    )

    if (
        column_name
        not in session.dataframe.columns
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Column '{column_name}' "
                "not found."
            ),
        )

    result = build_preprocessing_inspection(
        session.dataframe,
        [column_name],
        session.summary,
    )

    item = result["columns"][0]

    return {
        "dataset_id": dataset_id,
        "column": column_name,
        "missing": item["missing"],
        "records": item[
            "missing_records"
        ],
    }


@router.get(
    "/{dataset_id}/preprocessing/inspection/duplicates/{column_name:path}"
)
def duplicate_values(
    dataset_id: str,
    column_name: str,
):
    """
    Return duplicate-value details for one column.
    """

    session = _session(
        dataset_id
    )

    if (
        column_name
        not in session.dataframe.columns
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Column '{column_name}' "
                "not found."
            ),
        )

    result = build_preprocessing_inspection(
        session.dataframe,
        [column_name],
        session.summary,
    )

    item = result["columns"][0]

    return {
        "dataset_id": dataset_id,
        "column": column_name,
        "duplicate_values": item[
            "duplicate_values"
        ],
        "records": item[
            "duplicate_records"
        ],
    }


# ============================================================
# RUN PREPROCESSING
# ============================================================


@router.post(
    "/{dataset_id}/preprocess"
)
def preprocess(
    dataset_id: str,
    request: PreprocessRequest,
    db: Session = Depends(get_db),
):
    """
    Run the existing Phase 3 preprocessing pipeline.

    IMPORTANT:
    The resulting dataframe is stored in
    session.preprocessed_df.

    All downstream statistical and ML branches
    must use this dataframe rather than the raw dataframe.
    """

    session = _session(
        dataset_id
    )

    selected = _validate_columns(
        session,
        request.selected_columns,
    )

    if not session.confirmed:
        raise HTTPException(
            status_code=409,
            detail=(
                "Confirm the column selection first."
            ),
        )

    session.selected_columns = selected

    # --------------------------------------------------------
    # EXISTING PHASE 3 PROCESSING
    # --------------------------------------------------------

    processed_df, result = preprocess_dataset(
        session.dataframe,
        selected,
        session.summary,
    )

    # --------------------------------------------------------
    # STORE THE PROCESSED DATAFRAME
    # --------------------------------------------------------
    #
    # This is the dataframe that must be used by:
    #
    # 1. Existing Phase 3 statistical analysis
    # 2. New statistical branch
    # 3. Existing Phase 4 -> Phase 5 -> Phase 6 ML flow
    #
    # Raw session.dataframe remains unchanged.
    # --------------------------------------------------------

    session.preprocessed_df = (
        processed_df
    )

    session.preprocess_result = result

    session.statistical_result = None

    # --------------------------------------------------------
    # DATABASE PERSISTENCE
    # --------------------------------------------------------

    try:

        _save_preprocessing_result(
            db=db,
            dataset_id=dataset_id,
            result=result,
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Preprocessing completed, "
                "but the result could not be "
                "saved to the database: "
                f"{exc}"
            ),
        ) from exc

    return {
        "dataset_id": dataset_id,
        **result,
    }


# ============================================================
# EXISTING PHASE 3 STATISTICAL ANALYSIS
# ============================================================


@router.post(
    "/{dataset_id}/statistical-analysis"
)
def statistical_analysis(
    dataset_id: str,
    request: StatisticalAnalysisRequest,
    db: Session = Depends(get_db),
):
    """
    Run the existing Phase 3 statistical analysis.

    This endpoint is intentionally preserved so the
    existing Phase 3 functionality continues to work.
    """

    session = _session(
        dataset_id
    )

    if session.preprocessed_df is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Run preprocessing before "
                "statistical analysis."
            ),
        )

    selected = _validate_columns(
        session,
        request.selected_columns,
    )

    session.selected_columns = selected

    # --------------------------------------------------------
    # EXISTING STATISTICAL ANALYSIS
    # --------------------------------------------------------

    result = analyze_statistics(
        session.preprocessed_df,
        selected,
        session.summary,
    )

    session.statistical_result = result

    # --------------------------------------------------------
    # DATABASE PERSISTENCE
    # --------------------------------------------------------

    try:

        _save_statistical_analysis(
            db=db,
            dataset_id=dataset_id,
            result=result,
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Statistical analysis completed, "
                "but the result could not be "
                "saved to the database: "
                f"{exc}"
            ),
        ) from exc

    return {
        "dataset_id": dataset_id,
        **result,
    }


# ============================================================
# GET EXISTING PHASE 3 STATISTICAL ANALYSIS
# ============================================================


@router.get(
    "/{dataset_id}/statistical-analysis"
)
def get_statistical_analysis(
    dataset_id: str,
):
    """
    Retrieve the existing Phase 3 statistical analysis.
    """

    session = _session(
        dataset_id
    )

    if session.statistical_result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Statistical analysis "
                "has not been run."
            ),
        )

    return {
        "dataset_id": dataset_id,
        **session.statistical_result,
    }


# ============================================================
# NEW STATISTICAL APPROACH SELECTION
# ============================================================


@router.get(
    "/{dataset_id}/approach"
)
def get_available_approaches(
    dataset_id: str,
):
    """
    Return the two available anomaly-detection
    approaches after Phase 3 preprocessing.

    The frontend can use this response to display:

        Statistical Approach
            - Univariate
            - Multivariate

        ML Approach
            - Phase 4 -> Phase 5 -> Phase 6
    """

    session = _session(
        dataset_id
    )

    if session.preprocessed_df is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Run preprocessing before "
                "selecting an anomaly-detection "
                "approach."
            ),
        )

    return {
        "dataset_id": dataset_id,
        "preprocessing_completed": True,
        "available_approaches": [
            {
                "id": "statistical",
                "name": "Statistical Approach",
                "description": (
                    "Use statistical anomaly detection "
                    "on the Phase 3 preprocessed dataset."
                ),
                "methods": [
                    {
                        "id": "univariate",
                        "name": "Univariate",
                        "method": "IQR",
                    },
                    {
                        "id": "multivariate",
                        "name": "Multivariate",
                        "method": "Mahalanobis Distance",
                    },
                ],
            },
            {
                "id": "ml",
                "name": "ML Approach",
                "description": (
                    "Continue through objective understanding, "
                    "model recommendation, and ML anomaly detection."
                ),
                "next_phase": 4,
            },
        ],
    }


# ============================================================
# NEW STATISTICAL BRANCH INFORMATION
# ============================================================


@router.get(
    "/{dataset_id}/statistical-branch"
)
def statistical_branch_information(
    dataset_id: str,
):
    """
    Return information required by the frontend when
    entering the new Statistical Approach branch.

    Both statistical methods explicitly use the
    Phase 3 preprocessed dataset.
    """

    session = _session(
        dataset_id
    )

    if session.preprocessed_df is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Run preprocessing before "
                "starting the statistical approach."
            ),
        )

    return {
        "dataset_id": dataset_id,
        "source": "phase3_preprocessed_dataset",
        "selected_columns": (
            session.selected_columns
            or []
        ),
        "total_records": len(
            session.preprocessed_df
        ),
        "methods": [
            {
                "id": "univariate",
                "name": "Univariate",
                "method": "IQR",
                "data_source": (
                    "Phase 3 preprocessed dataset"
                ),
            },
            {
                "id": "multivariate",
                "name": "Multivariate",
                "method": "Mahalanobis Distance",
                "data_source": (
                    "Phase 3 preprocessed dataset"
                ),
                "columns": (
                    session.selected_columns
                    or []
                ),
            },
        ],
    }


# ============================================================
# PREPROCESSED DATASET PREVIEW
# ============================================================


@router.get(
    "/{dataset_id}/preview"
)
def preprocessed_preview(
    dataset_id: str,
    page: int = 1,
    page_size: int = 10,
):
    """
    Return a paginated preview of the Phase 3
    preprocessed dataset.
    """

    session = _session(
        dataset_id
    )

    if session.preprocessed_df is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Preprocessing has not been run."
            ),
        )

    page = max(
        1,
        page,
    )

    page_size = min(
        max(
            1,
            page_size,
        ),
        100,
    )

    total = len(
        session.preprocessed_df
    )

    total_pages = max(
        1,
        (
            total
            + page_size
            - 1
        )
        // page_size,
    )

    page = min(
        page,
        total_pages,
    )

    df = session.preprocessed_df[
        session.selected_columns
    ].iloc[
        (page - 1) * page_size:
        page * page_size
    ]

    rows = []
    columns = [str(column) for column in df.columns]
    for idx, values in zip(df.index, df.itertuples(index=False, name=None)):
        raw_index = idx.item() if hasattr(idx, "item") else idx
        item = {"__index": raw_index}
        for column, value in zip(columns, values):
            if hasattr(value, "isoformat"):
                value = value.isoformat()
            elif hasattr(value, "item"):
                try:
                    value = value.item()
                except Exception:
                    pass
            try:
                missing = bool(value is None or pd.isna(value))
            except (TypeError, ValueError):
                missing = value is None
            item[column] = None if missing else value
        rows.append(item)

    return {
        "dataset_id": dataset_id,
        "page": page,
        "page_size": page_size,
        "total_rows": total,
        "total_pages": total_pages,
        "columns": (
            session.selected_columns
        ),
        "rows": rows,
    }


# ============================================================
# DOWNLOAD PROCESSED DATASET AS CSV
# ============================================================


@router.get(
    "/{dataset_id}/download"
)
def download_processed_dataset(
    dataset_id: str,
):
    """
    Download the exact Phase 3 preprocessed dataset
    as CSV.
    """

    session = _session(
        dataset_id
    )

    if session.preprocessed_df is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Preprocessing has not been run."
            ),
        )

    # --------------------------------------------------------
    # Use the exact Phase 3 processed dataframe.
    # --------------------------------------------------------

    processed_df = (
        session.preprocessed_df
    )

    # --------------------------------------------------------
    # Export selected columns only.
    # --------------------------------------------------------

    if session.selected_columns:

        processed_df = (
            processed_df[
                session.selected_columns
            ]
        )

    # --------------------------------------------------------
    # Create CSV in memory.
    # --------------------------------------------------------

    csv_buffer = io.StringIO()

    processed_df.to_csv(
        csv_buffer,
        index=False,
    )

    csv_buffer.seek(0)

    return StreamingResponse(
        iter(
            [
                csv_buffer.getvalue()
            ]
        ),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; "
                f'filename="processed_dataset_'
                f'{dataset_id}.csv"'
            )
        },
    )