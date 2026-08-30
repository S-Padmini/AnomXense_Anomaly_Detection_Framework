from __future__ import annotations

from pydantic import BaseModel, Field


class Phase1AnalyzeResponse(BaseModel):
    dataset_id: str
    filename: str
    rows: int
    columns: int
    numeric: int
    categorical: int
    datetime: int
    identifiers: int
    boolean: int
    null_empty: int
    total_missing_values: int
    duplicate_records: int
    file_size_bytes: int
    file_size_mb: float
    all_column_names: list[str] = Field(default_factory=list)
    numeric_column_names: list[str] = Field(default_factory=list)
    categorical_column_names: list[str] = Field(default_factory=list)
    datetime_column_names: list[str] = Field(default_factory=list)
    identifier_column_names: list[str] = Field(default_factory=list)
    boolean_column_names: list[str] = Field(default_factory=list)
    null_column_names: list[str] = Field(default_factory=list)
    columns_with_missing_names: list[str] = Field(default_factory=list)
    column_details: dict = Field(default_factory=dict)
