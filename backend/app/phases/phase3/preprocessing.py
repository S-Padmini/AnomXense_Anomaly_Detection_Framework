from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

# Counts are always exact. These limits apply only to optional row-level
# examples sent to the browser, never to preprocessing or duplicate removal.
INSPECTION_DETAIL_LIMIT = 100
PREPROCESS_RESPONSE_ROW_LIMIT = 100
LARGE_DATASET_ROWS = 10_000


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        result = pd.isna(value)
        return bool(result) if not isinstance(result, (list, tuple, np.ndarray, pd.Series)) else False
    except Exception:
        return False


def _json_value(value: Any) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _numeric_values(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").dropna()


def _skewness(series: pd.Series) -> float:
    nums = _numeric_values(series)
    if len(nums) < 3:
        return 0.0
    value = float(nums.skew())
    return value if np.isfinite(value) else 0.0


def _format_number(value: float | None) -> float | int | None:
    if value is None or not np.isfinite(float(value)):
        return None
    rounded = round(float(value), 6)
    return int(rounded) if rounded.is_integer() else rounded


def _identifier_column(summary: dict[str, Any], selected: list[str]) -> str | None:
    for column in summary.get("identifier_column_names", []):
        if column in selected:
            return column
    for column in summary.get("identifier_column_names", []):
        return column
    return None


def _row_ref(index: Any, row: pd.Series, identifier: str | None) -> dict[str, Any]:
    item = {"index": _json_value(index)}
    if identifier and identifier in row.index:
        item["identifier_column"] = identifier
        item["identifier"] = _json_value(row[identifier])
    return item


def _limited_row_refs(
    df: pd.DataFrame,
    positions: np.ndarray,
    identifier: str | None,
    *,
    limit: int = INSPECTION_DETAIL_LIMIT,
) -> list[dict[str, Any]]:
    """Materialize a small, bounded set of row references only."""
    if limit <= 0 or len(positions) == 0:
        return []
    chosen = positions[:limit]
    view = df.iloc[chosen]
    refs: list[dict[str, Any]] = []
    # This loop is deliberately limited to at most `limit` records.
    for idx, row in view.iterrows():
        refs.append(_row_ref(idx, row, identifier))
    return refs


def _missing_records(
    df: pd.DataFrame,
    column: str,
    identifier: str | None,
    *,
    limit: int = INSPECTION_DETAIL_LIMIT,
) -> list[dict[str, Any]]:
    mask = df[column].isna().to_numpy()
    positions = np.flatnonzero(mask)[:max(0, limit)]
    refs = _limited_row_refs(df, positions, identifier, limit=limit)
    for ref in refs:
        ref["value"] = None
    return refs


def _duplicate_value_records(
    df: pd.DataFrame,
    column: str,
    identifier: str | None,
    *,
    limit: int = INSPECTION_DETAIL_LIMIT,
) -> list[dict[str, Any]]:
    """Return a bounded preview of duplicate-value groups.

    The full count is calculated separately with vectorized pandas operations.
    Only the first `limit` matching rows are grouped for display.
    """
    series = df[column]
    duplicate_mask = (series.notna() & series.duplicated(keep=False)).to_numpy()
    positions = np.flatnonzero(duplicate_mask)[:max(0, limit)]
    if len(positions) == 0:
        return []

    subset = df.iloc[positions]
    # Group only the bounded preview, never all duplicate rows.
    groups: list[dict[str, Any]] = []
    for value, group in subset.groupby(column, dropna=False, sort=False, observed=True):
        records = []
        for idx, row in group.iterrows():
            records.append(_row_ref(idx, row, identifier))
        groups.append({"value": _json_value(value), "records": records})
    return groups


def _exact_duplicate_records(
    df: pd.DataFrame,
    columns: list[str],
    identifier: str | None,
    *,
    detail_limit: int = INSPECTION_DETAIL_LIMIT,
) -> list[dict[str, Any]]:
    """Return a bounded list of exact duplicate-row examples."""
    if df.empty or not columns or detail_limit <= 0:
        return []
    duplicate_mask = df.duplicated(subset=columns, keep="first").to_numpy()
    positions = np.flatnonzero(duplicate_mask)[:detail_limit]
    return _limited_row_refs(df, positions, identifier, limit=detail_limit)


def build_preprocessing_inspection(
    df: pd.DataFrame,
    selected_columns: list[str],
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Calculate exact inspection counts while bounding browser payload size."""
    selected_columns = [c for c in selected_columns if c in df.columns]
    if not selected_columns:
        return {
            "row_count": int(len(df)), "columns": [], "missingTotal": 0,
            "exactDuplicateRows": 0, "duplicateValueTotal": 0,
            "allMissingRecords": [], "allDuplicateRecords": [],
            "inspection_details_limit": INSPECTION_DETAIL_LIMIT,
        }

    identifier = _identifier_column(summary, selected_columns)
    selected = df.loc[:, selected_columns]

    # Vectorized exact counts. These are the only values used for totals.
    missing_counts = selected.isna().sum(axis=0)
    duplicate_counts = {
        column: int((selected[column].notna() & selected[column].duplicated(keep=False)).sum())
        for column in selected_columns
    }
    exact_duplicate_mask = selected.duplicated(keep="first")
    exact_duplicate_count = int(exact_duplicate_mask.sum())

    columns: list[dict[str, Any]] = []
    all_missing_records: list[dict[str, Any]] = []
    for column in selected_columns:
        missing_count = int(missing_counts[column])
        duplicate_count = duplicate_counts[column]
        missing_records = (
            _missing_records(df, column, identifier)
            if missing_count else []
        )
        duplicate_records = (
            _duplicate_value_records(df, column, identifier)
            if duplicate_count else []
        )
        columns.append({
            "column": column,
            "dtype": str(df[column].dtype),
            "missing": missing_count,
            "duplicate_values": duplicate_count,
            "missing_records": missing_records,
            "missing_records_truncated": missing_count > len(missing_records),
            "duplicate_records": duplicate_records,
            "duplicate_records_truncated": duplicate_count > sum(len(g["records"]) for g in duplicate_records),
        })
        if missing_count:
            all_missing_records.append({
                "column": column,
                "records": missing_records,
                "records_truncated": missing_count > len(missing_records),
            })

    all_duplicate_records = _exact_duplicate_records(
        df, selected_columns, identifier, detail_limit=INSPECTION_DETAIL_LIMIT
    )
    return {
        "row_count": int(len(df)),
        "columns": columns,
        "missingTotal": int(missing_counts.sum()),
        "exactDuplicateRows": exact_duplicate_count,
        "duplicateValueTotal": int(sum(duplicate_counts.values())),
        "allMissingRecords": all_missing_records,
        "allDuplicateRecords": all_duplicate_records,
        "allDuplicateRecordsTruncated": exact_duplicate_count > len(all_duplicate_records),
        "inspection_details_limit": INSPECTION_DETAIL_LIMIT,
    }


def _action_text(action: dict[str, Any], numeric: bool) -> str:
    method = action["method"]
    if method in {"No missing values", "No usable numeric values"}:
        return method
    if numeric and action.get("skewness") is not None:
        return f'{method} (skewness {float(action["skewness"]):.2f})'
    return f"{method} ({action.get('filled_value')})"


def preprocess_dataset(
    df: pd.DataFrame,
    selected_columns: list[str],
    summary: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not selected_columns:
        raise ValueError("At least one column must be selected.")
    missing_columns = [c for c in selected_columns if c not in df.columns]
    if missing_columns:
        raise ValueError(f"Unknown selected columns: {missing_columns}")

    work = df.loc[:, selected_columns].copy()
    before_rows = len(work)

    # Exact duplicate detection/removal remains exact and vectorized.
    duplicate_mask = work.duplicated(subset=selected_columns, keep="first")
    duplicate_count = int(duplicate_mask.sum())
    identifier = _identifier_column(summary, selected_columns)
    duplicate_records = _exact_duplicate_records(
        work, selected_columns, identifier, detail_limit=INSPECTION_DETAIL_LIMIT
    )
    work = work.loc[~duplicate_mask].copy()

    before_missing = int(work.isna().to_numpy().sum())
    actions: dict[str, dict[str, Any]] = {}
    numeric_set = set(summary.get("numeric_column_names", []))
    datetime_set = set(summary.get("datetime_column_names", []))
    boolean_set = set(summary.get("boolean_column_names", []))

    for column in selected_columns:
        series = work[column]
        missing_count = int(series.isna().sum())
        skew = _skewness(series) if column in numeric_set else None
        if missing_count == 0:
            actions[column] = {
                "method": "No missing values", "skewness": _format_number(skew),
                "filled_value": None, "missing_values_handled": 0,
            }
            continue

        if column in numeric_set:
            nums = _numeric_values(series)
            if nums.empty:
                method, fill_value = "No usable numeric values", None
            else:
                method = "Mean imputation" if abs(skew or 0) <= 0.5 else "Median imputation"
                fill_value = float(nums.mean() if method == "Mean imputation" else nums.median())
                work[column] = series.fillna(fill_value)
        elif column in datetime_set:
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")
            mode = parsed.dropna().mode()
            fill_value = mode.iloc[0] if not mode.empty else None
            if fill_value is not None:
                work[column] = parsed.fillna(fill_value)
            method = "Date/Time mode imputation"
        else:
            nonmissing = series.dropna()
            mode = nonmissing.mode()
            fill_value = mode.iloc[0] if not mode.empty else None
            if fill_value is not None:
                work[column] = series.fillna(fill_value)
            method = "Boolean mode imputation" if column in boolean_set else "Mode imputation"

        actions[column] = {
            "method": method,
            "skewness": _format_number(skew),
            "filled_value": _json_value(fill_value),
            "missing_values_handled": missing_count,
        }

    after_missing = int(work.isna().to_numpy().sum())
    work.index.name = "index"
    action_text = {c: _action_text(a, c in numeric_set) for c, a in actions.items()}

    # Do not serialize a 100k-row DataFrame into the POST response. The frontend
    # already loads the paginated /preview endpoint immediately afterward.
    response_limit = None if len(work) <= PREPROCESS_RESPONSE_ROW_LIMIT else PREPROCESS_RESPONSE_ROW_LIMIT
    response_rows = _dataframe_to_records(work, limit=response_limit)
    result = {
        "success": True,
        "message": "Preprocessing completed successfully",
        "before": {
            "rows": before_rows,
            "columns": len(selected_columns),
            "missing_values": before_missing,
            "duplicate_records": duplicate_count,
        },
        "after": {
            "rows": int(len(work)),
            "columns": len(selected_columns),
            "missing_values": after_missing,
            "duplicate_records": 0,
        },
        "missing_values_handled": before_missing - after_missing,
        "duplicate_records_removed": duplicate_count,
        "columns_removed": [],
        "extreme_values_retained": True,
        "actions": actions,
        "action_text": action_text,
        "duplicate_records": duplicate_records,
        "duplicate_records_truncated": duplicate_count > len(duplicate_records),
        "selected_columns": selected_columns,
        "rows": response_rows,
        "rows_truncated": len(work) > len(response_rows),
        "rows_preview_limit": len(response_rows) if len(work) > len(response_rows) else None,
        "index_name": "index",
    }
    return work.loc[:, selected_columns].copy(), result


def _dataframe_to_records(
    df: pd.DataFrame,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Serialize a bounded preview using itertuples rather than iterrows."""
    view = df if limit is None else df.iloc[:max(0, int(limit))]
    columns = [str(column) for column in view.columns]
    records: list[dict[str, Any]] = []
    for idx, values in zip(view.index, view.itertuples(index=False, name=None)):
        item = {"__index": _json_value(idx)}
        item.update({column: _json_value(value) for column, value in zip(columns, values)})
        records.append(item)
    return records
