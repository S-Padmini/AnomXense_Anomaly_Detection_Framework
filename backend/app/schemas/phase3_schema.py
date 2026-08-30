from __future__ import annotations

from pydantic import BaseModel, Field


class PreprocessRequest(BaseModel):
    selected_columns: list[str] = Field(min_length=1)


class StatisticalAnalysisRequest(BaseModel):
    selected_columns: list[str] = Field(min_length=1)
