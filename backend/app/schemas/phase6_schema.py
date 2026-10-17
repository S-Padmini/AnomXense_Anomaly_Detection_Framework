from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Approach = Literal[
    "best_score",
    "combined_score",
]

ContaminationMode = Literal[
    "default",
    "custom",
]


class DetectionRequest(BaseModel):
    """
    Phase 6 detection configuration.

    contamination_mode:
        "default" uses an explicit PyOD contamination of 0.10 (10%).
        "custom" uses the investigator-selected value from 0.01 to 0.50.

    contamination:
        Fraction represented as a decimal.
        0.01 = 1%
        0.10 = 10%
        0.50 = 50%
    """

    model_config = ConfigDict(extra="forbid")

    approach: Approach = "best_score"

    contamination_mode: ContaminationMode = "default"

    contamination: float = Field(
        default=0.10,
        ge=0.01,
        le=0.50,
    )

    target_columns: list[str] = Field(
        default_factory=list
    )

    explain_by_columns: list[str] = Field(
        default_factory=list
    )

    @field_validator(
        "target_columns",
        "explain_by_columns",
    )
    @classmethod
    def clean_columns(
        cls,
        value: list[str],
    ) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for item in value or []:
            name = str(item).strip()
            if name and name not in seen:
                seen.add(name)
                result.append(name)

        return result


class FilterRequest(BaseModel):
    """
    Dynamic investigation filtering.
    """

    search: str = ""

    filters: dict[str, Any] = Field(
        default_factory=dict
    )

    sort_by: str = "rank"

    sort_direction: Literal[
        "asc",
        "desc",
    ] = "asc"

    page: int = Field(
        default=1,
        ge=1,
    )

    page_size: int = Field(
        default=50,
        ge=1,
        le=500,
    )


class Phase6Response(BaseModel):
    dataset_id: str
    status: str
    result: dict[str, Any]
