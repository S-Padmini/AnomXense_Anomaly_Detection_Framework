from __future__ import annotations

from pydantic import BaseModel, Field


class ColumnSelectionRequest(BaseModel):
    selected_columns: list[str] = Field(min_length=1)


class ColumnSelectionResponse(BaseModel):
    dataset_id: str
    selected_columns: list[str]
    selected_count: int
    total_columns: int
    selected_column_details: dict
    confirmed: bool = False
