from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.store import store
from app.phases.phase1.column_analyzer import analyze_dataset
from app.services.llm_descriptions import (
    generate_column_description,
)


router = APIRouter(
    prefix="/api/phase1",
    tags=["Phase 1"],
)


# ============================================================
# DATASET READING
# ============================================================

def _read_dataframe(
    filename: str,
    content: bytes,
) -> pd.DataFrame:

    suffix = Path(
        filename or ""
    ).suffix.lower()

    try:

        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(
                io.BytesIO(content)
            )

        if suffix == ".json":
            return pd.read_json(
                io.BytesIO(content)
            )

        if suffix in {".tsv", ".tab"}:
            return pd.read_csv(
                io.BytesIO(content),
                sep="\t",
                encoding="utf-8-sig",
            )

        return pd.read_csv(
            io.BytesIO(content),
            encoding="utf-8-sig",
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unable to read dataset "
                f"'{filename}': {exc}"
            ),
        ) from exc


# ============================================================
# UNIQUE COLUMN NAMES
# ============================================================

def _unique_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:

    names = []
    seen: dict[str, int] = {}

    for index, raw_name in enumerate(
        df.columns
    ):

        name = (
            str(raw_name).strip()
            or f"column_{index + 1}"
        )

        count = (
            seen.get(name, 0) + 1
        )

        seen[name] = count

        names.append(
            name
            if count == 1
            else f"{name}_{count}"
        )

    result = df.copy()
    result.columns = names

    return result


# ============================================================
# COLUMN INFO — ONLY THESE 5 FIELDS
# ============================================================

def _column_info_only(
    profile: dict,
    column_name: str,
) -> dict:

    return {
        "column_name": column_name,

        "role": profile.get(
            "role",
            "Unknown",
        ),

        "data_type": profile.get(
            "dtype",
            "Unknown",
        ),

        "missing_percentage": profile.get(
            "missing_percentage",
            0,
        ),

        "llm_description": profile.get(
            "description",
            "",
        ),
    }


# ============================================================
# PHASE 1 ANALYZE
# ============================================================

@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
):

    content = await file.read()

    if not content:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    filename = (
        file.filename
        or "dataset.csv"
    )

    df = _unique_columns(
        _read_dataframe(
            filename,
            content,
        )
    )

    if df.empty:

        raise HTTPException(
            status_code=400,
            detail="Dataset contains no rows.",
        )

    if len(df.columns) == 0:

        raise HTTPException(
            status_code=400,
            detail="Dataset contains no columns.",
        )

    summary = analyze_dataset(
        df=df,
        filename=filename,
        file_size=len(content),
    )

    session = store.create(
        filename=filename,
        file_size=len(content),
        dataframe=df,
        summary=summary,
    )

    summary["dataset_id"] = (
        session.dataset_id
    )

    session.summary = summary

    return summary


# ============================================================
# GET DATASET SUMMARY
# ============================================================

@router.get("/{dataset_id}")
def get_summary(
    dataset_id: str,
):

    try:

        return store.get(
            dataset_id
        ).summary

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail="Dataset session not found.",
        ) from exc


# ============================================================
# GET COLUMN DETAILS
#
# IMPORTANT:
# This endpoint intentionally exposes ONLY:
#
# 1. Column Name
# 2. Role
# 3. Data Type
# 4. Missing Value %
# 5. LLM Description
#
# Nothing else is returned here.
# ============================================================

@router.get(
    "/{dataset_id}/column/{column_name:path}"
)
def get_column_details(
    dataset_id: str,
    column_name: str,
):

    try:

        session = store.get(
            dataset_id
        )

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail="Dataset session not found.",
        ) from exc

    if column_name not in session.dataframe.columns:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Column '{column_name}' "
                f"not found."
            ),
        )

    # Get internal profile.
    profile = dict(
        session.summary[
            "column_details"
        ][column_name]
    )

    # Generate/retrieve semantic description.
    try:

        result = generate_column_description(
            profile=profile,
            dataset_summary=session.summary,
        )

        description = result.get(
            "description",
            profile.get(
                "description",
                "",
            ),
        )

    except Exception:

        description = profile.get(
            "description",
            "",
        )

    # --------------------------------------------------------
    # VERY IMPORTANT:
    # DO NOT return the complete profile.
    # --------------------------------------------------------

    details = _column_info_only(
        profile={
            **profile,
            "description": description,
        },
        column_name=column_name,
    )

    return {
        "dataset_id": dataset_id,
        "column": column_name,
        "details": details,
    }


# ============================================================
# MISSING VALUES
# ============================================================

@router.get(
    "/{dataset_id}/missing-values"
)
def get_missing_values(
    dataset_id: str,
):

    try:

        session = store.get(
            dataset_id
        )

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail="Dataset session not found.",
        ) from exc

    df = session.dataframe

    missing_mask = df.isna().any(
        axis=1
    )

    missing_df = df.loc[
        missing_mask
    ].copy()

    records = []

    for index, row in missing_df.iterrows():

        missing_columns = [
            str(column)
            for column in df.columns
            if pd.isna(row[column])
        ]

        records.append(
            {
                "index": index,
                "missing_columns":
                    missing_columns,
            }
        )

    return {
        "dataset_id": dataset_id,

        "total_rows_with_missing_values":
            len(records),

        "total_missing_cells":
            int(
                df.isna()
                .sum()
                .sum()
            ),

        "records": records,
    }


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

router.add_api_route(
    "/upload",
    analyze,
    methods=["POST"],
)