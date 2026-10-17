from __future__ import annotations

import io
from pathlib import Path
from pydantic import BaseModel, Field

from app.db.postgres_connection import (
    get_postgres_schema,
    list_postgres_tables,
    read_postgres_table,
)

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.store import store
from app.db.database import get_db
from app.db.persistence import save_phase1_result
from app.phases.phase1.column_analyzer import analyze_dataset
from app.services.llm_descriptions import generate_column_description


router = APIRouter(
    prefix="/api/phase1",
    tags=["Phase 1"],
)

class PostgresTableRequest(BaseModel):
    table_name: str = Field(
        min_length=1,
        max_length=128,
    )

# ============================================================
# DATASET READING
# ============================================================

def _read_dataframe(
    filename: str,
    file_obj,
) -> pd.DataFrame:
    """
    Read directly from UploadFile's underlying file object.

    The old endpoint first did `await file.read()`, which duplicated the
    complete upload in Python memory before pandas parsed it. For very large
    CSVs this is an unnecessary memory spike. The optimized version streams
    the upload into pandas without creating a second full bytes object.
    """
    suffix = Path(filename or "").suffix.lower()

    try:
        file_obj.seek(0)

        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(file_obj)

        if suffix == ".json":
            return pd.read_json(file_obj)

        if suffix in {".tsv", ".tab"}:
            return pd.read_csv(
                file_obj,
                sep="\t",
                encoding="utf-8-sig",
                engine="c",
            )

        return pd.read_csv(
            file_obj,
            encoding="utf-8-sig",
            engine="c",
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to read dataset '{filename}': {exc}",
        ) from exc


# ============================================================
# UNIQUE COLUMN NAMES
# ============================================================

def _unique_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:

    names = []
    seen: dict[str, int] = {}

    for index, raw_name in enumerate(df.columns):

        name = str(raw_name).strip()

        if not name:
            name = f"column_{index + 1}"

        count = seen.get(name, 0) + 1
        seen[name] = count

        names.append(
            name
            if count == 1
            else f"{name}_{count}"
        )

    # Renaming columns does not require copying the 10M-row dataframe.
    df.columns = names
    return df


# ============================================================
# COLUMN NAME RESOLUTION
# ============================================================

def _resolve_column_name(
    requested_name: str,
    columns,
) -> str | None:

    requested = str(
        requested_name
    ).strip()

    if requested in columns:
        return requested

    for column in columns:

        canonical = str(column)

        if canonical.strip() == requested:
            return canonical

    return None


# ============================================================
# COLUMN INFO
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
    db: Session = Depends(get_db),
):
    """
    Analyze an uploaded dataset.

    Large-file optimization:
      * do not materialize the complete upload as bytes;
      * parse directly from UploadFile's spooled file;
      * keep the existing pandas dataframe session contract so Phase 2+
        behavior is unchanged.
    """
    filename = file.filename or "dataset.csv"

    # UploadFile uses a file-like object and can spool large uploads to disk.
    # Obtain its size without reading the complete upload into RAM.
    try:
        file.file.seek(0, 2)
        file_size = int(file.file.tell())
        file.file.seek(0)
    except Exception:
        file_size = 0
        try:
            file.file.seek(0)
        except Exception:
            pass

    if file_size <= 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    df = _unique_columns(
        _read_dataframe(
            filename,
            file.file,
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
        file_size=file_size,
    )

    session = store.create(
        filename=filename,
        file_size=file_size,
        dataframe=df,
        summary=summary,
    )

    summary["dataset_id"] = session.dataset_id
    session.summary = summary

    try:
        save_phase1_result(
            db=db,
            dataset_id=session.dataset_id,
            filename=filename,
            file_size=file_size,
            summary=summary,
            dataframe_columns=[str(column) for column in df.columns],
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=(
                "Phase 1 analysis completed, but the result could not be "
                f"saved to the database: {exc}"
            ),
        ) from exc

    return summary

# ============================================================
# POSTGRESQL TABLE SOURCE
# ============================================================

@router.get("/postgres/tables")
def get_postgres_tables():
    """List tables available in the configured PostgreSQL schema."""

    try:
        tables = list_postgres_tables()
        schema = get_postgres_schema()

        return {
            "source": "postgresql",
            "schema": schema,
            "tables": tables,
            "total_tables": len(tables),
        }

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.post("/postgres/load")
def load_postgres_table(
    request: PostgresTableRequest,
):
    """Load a selected PostgreSQL table into the Phase 1 workflow."""

    table_name = request.table_name.strip()

    try:
        df = read_postgres_table(table_name)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="The selected PostgreSQL table contains no rows.",
        )

    if len(df.columns) == 0:
        raise HTTPException(
            status_code=400,
            detail="The selected PostgreSQL table contains no columns.",
        )

    df = _unique_columns(df)

    # Approximate in-memory dataset size for Phase 1 metadata.
    file_size = int(
        df.memory_usage(index=True, deep=True).sum()
    )

    filename = f"{table_name}.csv"

    try:
        summary = analyze_dataset(
            df=df,
            filename=filename,
            file_size=file_size,
        )

        session = store.create(
            filename=filename,
            file_size=file_size,
            dataframe=df,
            summary=summary,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to analyze the selected PostgreSQL table.",
        ) from exc

    summary["dataset_id"] = session.dataset_id
    summary["source_type"] = "postgresql"
    summary["source_table"] = table_name
    summary["source_schema"] = get_postgres_schema()

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
# ============================================================

@router.get(
    "/{dataset_id}/column/{column_name:path}"
)
def get_column_details(
    dataset_id: str,
    column_name: str,
):

    # --------------------------------------------------------
    # GET SESSION
    # --------------------------------------------------------

    try:

        session = store.get(
            dataset_id
        )

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail="Dataset session not found.",
        ) from exc

    # --------------------------------------------------------
    # RESOLVE ACTUAL COLUMN
    # --------------------------------------------------------

    actual_column_name = _resolve_column_name(
        requested_name=column_name,
        columns=session.dataframe.columns,
    )

    if actual_column_name is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Column '{column_name}' "
                f"not found."
            ),
        )

    # --------------------------------------------------------
    # GET PROFILE
    # --------------------------------------------------------

    column_details = session.summary.get(
        "column_details",
        {},
    )

    profile = None

    if actual_column_name in column_details:

        profile = dict(
            column_details[
                actual_column_name
            ]
        )

    else:

        for profile_name, profile_data in column_details.items():

            if (
                str(profile_name).strip()
                == str(actual_column_name).strip()
            ):

                profile = dict(
                    profile_data
                )

                break

    # --------------------------------------------------------
    # FALLBACK PROFILE
    # --------------------------------------------------------

    if profile is None:

        series = session.dataframe[
            actual_column_name
        ]

        profile = {
            "role": "Unknown",

            "dtype": str(
                series.dtype
            ),

            "missing_percentage": float(
                series.isna().mean() * 100
            ),

            "description": "",
        }

    # --------------------------------------------------------
    # LLM DESCRIPTION
    # --------------------------------------------------------

    description = str(
        profile.get(
            "description",
            "",
        )
        or ""
    ).strip()

    llm_error = None

    try:

        result = generate_column_description(
            profile=profile,
            dataset_summary=session.summary,
            df=session.dataframe,

        )

        print(
            "\n========== LLM COLUMN DESCRIPTION =========="
        )

        print(
            "COLUMN:",
            actual_column_name,
        )

        print(
            "RAW LLM RESULT:",
            repr(result),
        )

        # ----------------------------------------------------
        # LLM SERVICE RETURNS DICTIONARY
        # ----------------------------------------------------

        if isinstance(result, dict):

            llm_description = result.get(
                "description"
            )

            if llm_description:

                description = str(
                    llm_description
                ).strip()

        # ----------------------------------------------------
        # LLM SERVICE RETURNS STRING
        # ----------------------------------------------------

        elif isinstance(result, str):

            if result.strip():

                description = result.strip()

        print(
            "FINAL DESCRIPTION:",
            repr(description),
        )

        print(
            "============================================\n"
        )

    except Exception as exc:

        llm_error = str(exc)

        print(
            "\n========== LLM DESCRIPTION ERROR =========="
        )

        print(
            "COLUMN:",
            actual_column_name,
        )

        print(
            "ERROR:",
            repr(exc),
        )

        print(
            "===========================================\n"
        )

    # --------------------------------------------------------
    # IF LLM FAILED AND NO DESCRIPTION EXISTS,
    # KEEP EMPTY STRING.
    # --------------------------------------------------------

    details = _column_info_only(
        profile={
            **profile,
            "description": description,
        },
        column_name=actual_column_name,
    )

    response = {
        "dataset_id": dataset_id,

        "column": actual_column_name,

        "details": details,
    }

    # --------------------------------------------------------
    # DEVELOPMENT DIAGNOSTIC
    #
    # This tells us exactly why the LLM is empty.
    # --------------------------------------------------------

    if llm_error:

        response["llm_error"] = llm_error

    return response


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
                "missing_columns": missing_columns,
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