from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


# ============================================================
# SQLite INTEGER PRIMARY KEY SUPPORT
# ============================================================
#
# SQLite needs INTEGER PRIMARY KEY for reliable auto-increment.
# Other databases can use BIGINT.
#
SQLiteBigInt = BigInteger().with_variant(
    Integer,
    "sqlite",
)


# ============================================================
# DATASET_RUNS
# ============================================================


class DatasetRun(Base):
    __tablename__ = "DATASET_RUNS"

    dataset_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    original_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    original_columns: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    current_phase: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# ============================================================
# DATASET_COLUMNS
# ============================================================


class DatasetColumn(Base):
    __tablename__ = "DATASET_COLUMNS"

    column_id: Mapped[int] = mapped_column(
        SQLiteBigInt,
        primary_key=True,
        autoincrement=True,
    )

    dataset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "DATASET_RUNS.dataset_id"
        ),
        nullable=False,
        index=True,
    )

    column_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    column_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    data_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    missing_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    missing_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    missing_percentage: Mapped[float] = mapped_column(
        Numeric(8, 4),
        nullable=False,
    )

    unique_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    selected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    skewness: Mapped[float | None] = mapped_column(
        Numeric(12, 6),
        nullable=True,
    )

    imputation_method: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    imputation_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    llm_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


# ============================================================
# PREPROCESSING_RUNS
# ============================================================


class PreprocessingRun(Base):
    __tablename__ = "PREPROCESSING_RUNS"

    preprocessing_id: Mapped[int] = mapped_column(
        SQLiteBigInt,
        primary_key=True,
        autoincrement=True,
    )

    dataset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "DATASET_RUNS.dataset_id"
        ),
        nullable=False,
        index=True,
    )

    rows_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    rows_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    missing_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    missing_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    duplicate_records_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    duplicate_records_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    duplicates_removed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    statistical_analysis: Mapped[
        dict | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# ============================================================
# OBJECTIVES
# ============================================================


class Objective(Base):
    __tablename__ = "OBJECTIVES"

    objective_id: Mapped[int] = mapped_column(
        SQLiteBigInt,
        primary_key=True,
        autoincrement=True,
    )

    dataset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "DATASET_RUNS.dataset_id"
        ),
        nullable=False,
        index=True,
    )

    original_objective: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    interpreted_objective: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    anomaly_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    anomaly_scope: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    target_columns: Mapped[
        list | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    attributes_involved: Mapped[
        list | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# ============================================================
# MODEL_RECOMMENDATIONS
# ============================================================


class ModelRecommendation(Base):
    __tablename__ = "MODEL_RECOMMENDATIONS"

    recommendation_id: Mapped[int] = mapped_column(
        SQLiteBigInt,
        primary_key=True,
        autoincrement=True,
    )

    dataset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "DATASET_RUNS.dataset_id"
        ),
        nullable=False,
        index=True,
    )

    rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    statistical_score: Mapped[float] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    objective_score: Mapped[float] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    final_score: Mapped[float] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    is_selected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# ============================================================
# DETECTION_RUNS
# ============================================================
#
# This existing table can represent BOTH:
#
# 1. ML detection
#       approach = "ml"
#       model_name = "CBLOF"
#
# 2. Statistical detection
#       approach = "statistical"
#       model_name = "IQR"
#       or
#       model_name = "Mahalanobis Distance"
#
# Therefore no additional table is required for the new
# statistical branch.
#
# ============================================================


class DetectionRun(Base):
    __tablename__ = "DETECTION_RUNS"

    detection_id: Mapped[int] = mapped_column(
        SQLiteBigInt,
        primary_key=True,
        autoincrement=True,
    )

    dataset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "DATASET_RUNS.dataset_id"
        ),
        nullable=False,
        index=True,
    )

    approach: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    target_columns: Mapped[
        list | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    explain_by_columns: Mapped[
        list | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    training_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    training_features: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    total_records: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    anomaly_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    normal_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    anomaly_rate: Mapped[float] = mapped_column(
        Numeric(8, 4),
        nullable=False,
    )

    threshold: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )

    contamination: Mapped[float] = mapped_column(
        Numeric(8, 6),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# ============================================================
# ANOMALIES
# ============================================================
#
# This table can store anomaly records from:
#
# - ML models
# - IQR
# - Mahalanobis Distance
#
# Existing JSON fields are sufficient for storing dynamic
# contributing attributes and explanations.
#
# ============================================================


class Anomaly(Base):
    __tablename__ = "ANOMALIES"

    anomaly_id: Mapped[int] = mapped_column(
        SQLiteBigInt,
        primary_key=True,
        autoincrement=True,
    )

    detection_id: Mapped[int] = mapped_column(
        SQLiteBigInt,
        ForeignKey(
            "DETECTION_RUNS.detection_id"
        ),
        nullable=False,
        index=True,
    )

    record_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    original_row_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    anomaly_score: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )

    threshold: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )

    score_difference: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    target_values: Mapped[
        dict | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    explain_by_values: Mapped[
        dict | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    contributing_attributes: Mapped[
        list | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    original_record: Mapped[
        dict | None
    ] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# ============================================================
# REPORTS
# ============================================================


class Report(Base):
    __tablename__ = "REPORTS"

    report_id: Mapped[int] = mapped_column(
        SQLiteBigInt,
        primary_key=True,
        autoincrement=True,
    )

    detection_id: Mapped[int] = mapped_column(
        SQLiteBigInt,
        ForeignKey(
            "DETECTION_RUNS.detection_id"
        ),
        nullable=False,
        index=True,
    )

    report_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    report_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )