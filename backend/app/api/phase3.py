from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.store import store
from app.phases.phase3.preprocessing import build_preprocessing_inspection, preprocess_dataset
from app.phases.phase3.statistical_analysis import analyze_statistics
from app.schemas.phase3_schema import PreprocessRequest, StatisticalAnalysisRequest

router = APIRouter(prefix="/api/phase3", tags=["Phase 3"])


def _session(dataset_id: str):
    try:
        return store.get(dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Dataset session not found.") from exc


def _validate_columns(session, columns: list[str]) -> list[str]:
    if not columns:
        raise HTTPException(status_code=400, detail="Select at least one column.")
    unknown = [c for c in columns if c not in session.dataframe.columns]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown columns: {unknown}")
    return [c for c in session.dataframe.columns if c in set(columns)]


@router.get("/{dataset_id}/preprocessing/inspection")
def preprocessing_inspection(dataset_id: str):
    session = _session(dataset_id)
    if not session.selected_columns:
        raise HTTPException(status_code=400, detail="Select at least one column.")
    return build_preprocessing_inspection(
        session.dataframe, session.selected_columns, session.summary
    )


@router.get("/{dataset_id}/preprocessing/inspection/missing/{column_name:path}")
def missing_values(dataset_id: str, column_name: str):
    session = _session(dataset_id)
    if column_name not in session.dataframe.columns:
        raise HTTPException(status_code=404, detail=f"Column '{column_name}' not found.")
    result = build_preprocessing_inspection(session.dataframe, [column_name], session.summary)
    item = result["columns"][0]
    return {"dataset_id": dataset_id, "column": column_name,
            "missing": item["missing"], "records": item["missing_records"]}


@router.get("/{dataset_id}/preprocessing/inspection/duplicates/{column_name:path}")
def duplicate_values(dataset_id: str, column_name: str):
    session = _session(dataset_id)
    if column_name not in session.dataframe.columns:
        raise HTTPException(status_code=404, detail=f"Column '{column_name}' not found.")
    result = build_preprocessing_inspection(session.dataframe, [column_name], session.summary)
    item = result["columns"][0]
    return {"dataset_id": dataset_id, "column": column_name,
            "duplicate_values": item["duplicate_values"], "records": item["duplicate_records"]}


@router.post("/{dataset_id}/preprocess")
def preprocess(dataset_id: str, request: PreprocessRequest):
    session = _session(dataset_id)
    selected = _validate_columns(session, request.selected_columns)
    if not session.confirmed:
        raise HTTPException(status_code=409, detail="Confirm the column selection first.")

    session.selected_columns = selected
    processed_df, result = preprocess_dataset(session.dataframe, selected, session.summary)
    session.preprocessed_df = processed_df
    session.preprocess_result = result
    session.statistical_result = None
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/statistical-analysis")
def statistical_analysis(dataset_id: str, request: StatisticalAnalysisRequest):
    session = _session(dataset_id)
    if session.preprocessed_df is None:
        raise HTTPException(status_code=409, detail="Run preprocessing before statistical analysis.")
    selected = _validate_columns(session, request.selected_columns)
    session.selected_columns = selected
    result = analyze_statistics(session.preprocessed_df, selected, session.summary)
    session.statistical_result = result
    return {"dataset_id": dataset_id, **result}


@router.get("/{dataset_id}/statistical-analysis")
def get_statistical_analysis(dataset_id: str):
    session = _session(dataset_id)
    if session.statistical_result is None:
        raise HTTPException(status_code=404, detail="Statistical analysis has not been run.")
    return {"dataset_id": dataset_id, **session.statistical_result}


@router.get("/{dataset_id}/preview")
def preprocessed_preview(dataset_id: str, page: int = 1, page_size: int = 10):
    session = _session(dataset_id)
    if session.preprocessed_df is None:
        raise HTTPException(status_code=404, detail="Preprocessing has not been run.")
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = len(session.preprocessed_df)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    df = session.preprocessed_df[session.selected_columns].iloc[
        (page - 1) * page_size : page * page_size
    ]

    rows = []
    for idx, row in df.iterrows():
        item = {"__index": idx.item() if hasattr(idx, "item") else idx}
        for col in df.columns:
            value = row[col]
            if hasattr(value, "isoformat"):
                value = value.isoformat()
            elif hasattr(value, "item"):
                try:
                    value = value.item()
                except Exception:
                    pass
            item[col] = None if value != value else value
        rows.append(item)

    return {
        "dataset_id": dataset_id,
        "page": page,
        "page_size": page_size,
        "total_rows": total,
        "total_pages": total_pages,
        "columns": session.selected_columns,
        "rows": rows,
    }
