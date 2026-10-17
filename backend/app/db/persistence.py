from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import (
    Anomaly,
    DatasetColumn,
    DatasetRun,
    DetectionRun,
)


# ============================================================
# PHASE 1
# ============================================================


def save_phase1_result(
    db: Session,
    *,
    dataset_id: str,
    filename: str,
    file_size: int,
    summary: dict[str, Any],
    dataframe_columns: list[str],
) -> None:
    """
    Persist the Phase 1 dataset result into:

    1. DATASET_RUNS
    2. DATASET_COLUMNS

    This function preserves the existing Phase 1 behavior.
    It does not modify Phase 1 analysis logic.
    """

    # ---------------------------------------------------------
    # DATASET_RUNS
    # ---------------------------------------------------------

    suffix = Path(filename or "").suffix.lower()

    file_type = (
        suffix.lstrip(".").upper()
        if suffix
        else "CSV"
    )

    dataset_run = DatasetRun(
        dataset_id=dataset_id,
        filename=filename,
        file_type=file_type,
        original_rows=int(
            summary.get("rows", 0)
        ),
        original_columns=int(
            summary.get("columns", 0)
        ),
        current_phase=1,
        status="ANALYZED",
    )

    db.add(dataset_run)

    # ---------------------------------------------------------
    # DATASET_COLUMNS
    # ---------------------------------------------------------

    column_details = summary.get(
        "column_details",
        {},
    )

    for column_order, column_name in enumerate(
        dataframe_columns,
        start=1,
    ):
        profile = column_details.get(
            column_name,
            {},
        )

        # Phase 1 has not performed preprocessing yet.
        # Therefore missing_after is the same as missing_before.
        missing_before = int(
            profile.get(
                "missing_values",
                0,
            )
            or 0
        )

        missing_percentage = float(
            profile.get(
                "missing_percentage",
                0,
            )
            or 0
        )

        unique_count = int(
            profile.get(
                "unique_values",
                0,
            )
            or 0
        )

        role = str(
            profile.get(
                "role",
                "Unknown",
            )
        )

        data_type = str(
            profile.get(
                "dtype",
                "Unknown",
            )
        )

        # Phase 1 does not calculate skewness.
        skewness = None

        description = str(
            profile.get(
                "description",
                "",
            )
            or ""
        ).strip()

        column_record = DatasetColumn(
            dataset_id=dataset_id,
            column_name=str(column_name),
            column_order=column_order,
            role=role,
            data_type=data_type,
            missing_before=missing_before,
            missing_after=missing_before,
            missing_percentage=missing_percentage,
            unique_count=unique_count,
            selected=True,
            skewness=skewness,
            imputation_method=None,
            imputation_value=None,
            llm_description=description or None,
        )

        db.add(column_record)

    # ---------------------------------------------------------
    # COMMIT
    # ---------------------------------------------------------

    db.commit()


# ============================================================
# STATISTICAL DETECTION
# ============================================================


def save_statistical_detection(
    db: Session,
    *,
    dataset_id: str,
    method: str,
    selected_columns: list[str],
    total_records: int,
    anomaly_count: int,
    normal_count: int,
    anomaly_rate: float,
    threshold: float | None,
    records: list[dict[str, Any]],
    status: str = "COMPLETED",
) -> int:
    """
    Persist one Statistical Approach detection run.

    Supported methods:

    - IQR
    - Mahalanobis Distance

    The statistical branch always receives the Phase 3
    preprocessed dataset before this function is called.

    Returns:
        detection_id
    """

    # ---------------------------------------------------------
    # SAFE COUNTS
    # ---------------------------------------------------------

    safe_total = max(
        int(total_records or 0),
        0,
    )

    safe_anomaly = max(
        int(anomaly_count or 0),
        0,
    )

    safe_normal = max(
        int(normal_count or 0),
        0,
    )

    # ---------------------------------------------------------
    # DETECTION RUN
    # ---------------------------------------------------------

    detection_run = DetectionRun(
        dataset_id=dataset_id,
        approach="statistical",
        model_name=method,
        target_columns=selected_columns,
        explain_by_columns=None,
        training_rows=safe_total,
        training_features=len(selected_columns),
        total_records=safe_total,
        anomaly_count=safe_anomaly,
        normal_count=safe_normal,
        anomaly_rate=_safe_float(
            anomaly_rate
        ),
        threshold=(
            _safe_float(threshold)
            if threshold is not None
            else None
        ),
        contamination=(
            safe_anomaly / safe_total
            if safe_total > 0
            else 0.0
        ),
        status=status,
    )

    db.add(detection_run)

    # ---------------------------------------------------------
    # FLUSH
    # ---------------------------------------------------------
    #
    # We need detection_id before inserting ANOMALIES.
    #

    db.flush()

    detection_id = int(
        detection_run.detection_id
    )

    # ---------------------------------------------------------
    # ANOMALY RECORDS
    # ---------------------------------------------------------

    for record in records:

        if str(
            record.get(
                "status",
                "",
            )
        ).lower() != "anomaly":
            continue

        # -----------------------------------------------------
        # SCORE
        # -----------------------------------------------------

        anomaly_score = _safe_float(
            record.get(
                "anomaly_score",
                record.get(
                    "score",
                    0.0,
                ),
            )
        )

        # -----------------------------------------------------
        # THRESHOLD
        # -----------------------------------------------------

        record_threshold_value = record.get(
            "threshold",
            threshold,
        )

        record_threshold = (
            _safe_float(
                record_threshold_value
            )
            if record_threshold_value is not None
            else 0.0
        )

        # -----------------------------------------------------
        # SCORE DIFFERENCE
        # -----------------------------------------------------

        score_difference = (
            anomaly_score - record_threshold
        )

        # -----------------------------------------------------
        # RECORD ID
        # -----------------------------------------------------

        record_id = _record_id(
            record,
            detection_id,
        )

        # -----------------------------------------------------
        # FEATURE / TARGET VALUES
        # -----------------------------------------------------

        target_values = record.get(
            "feature_values"
        )

        if target_values is None:
            target_values = record.get(
                "values"
            )

        # -----------------------------------------------------
        # EXPLANATION DATA
        # -----------------------------------------------------

        contributing_attributes = record.get(
            "contributing_attributes"
        )

        reason = record.get(
            "reason"
        )

        original_record = record.get(
            "original_record"
        )

        # -----------------------------------------------------
        # ORIGINAL ROW INDEX
        # -----------------------------------------------------

        original_row_index = record.get(
            "record_number",
            record.get(
                "original_row_index",
                0,
            ),
        )

        try:
            original_row_index = int(
                original_row_index or 0
            )
        except (
            TypeError,
            ValueError,
        ):
            original_row_index = 0

        # -----------------------------------------------------
        # ANOMALY
        # -----------------------------------------------------

        anomaly = Anomaly(
            detection_id=detection_id,
            record_id=record_id,
            original_row_index=original_row_index,
            anomaly_score=anomaly_score,
            threshold=record_threshold,
            score_difference=score_difference,
            model_name=method,
            target_values=target_values,
            explain_by_values=None,
            contributing_attributes=(
                contributing_attributes
            ),
            reason=(
                str(reason)
                if reason is not None
                else None
            ),
            original_record=original_record,
        )

        db.add(anomaly)

    # ---------------------------------------------------------
    # COMMIT
    # ---------------------------------------------------------

    db.commit()

    return detection_id


# ============================================================
# STATISTICAL DETECTION HELPERS
# ============================================================


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Convert a value safely to float.

    Statistical results may contain NumPy numeric types,
    strings, None, or missing values.
    """

    try:
        if value is None:
            return default

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def _record_id(
    record: dict[str, Any],
    detection_id: int,
) -> str:
    """
    Obtain a stable string record identifier.

    Preference order:

    1. record_id
    2. id
    3. record_number
    4. generated detection-based identifier
    """

    value = record.get(
        "record_id" 
    )

    if value is None:
        value = record.get(
            "id"
        )

    if value is None:
        value = record.get(
            "record_number"
        )

    if value is not None:
        return str(value)

    return f"{detection_id}_{id(record)}"