from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ============================================================
# TYPE DEFINITIONS
# ============================================================

DetectionApproach = Literal[
    "univariate",
    "multivariate",
]

ScoreMethod = Literal[
    "best_score",
    "combined_score",
]

ContaminationMode = Literal[
    "default",
    "custom",
]


# ============================================================
# BENCHMARK REQUEST
# ============================================================

class BenchmarkRequest(BaseModel):
    """
    Request for Automatic Discovery model benchmarking.

    The benchmark is performed after Phase 3 preprocessing.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    approach: DetectionApproach


# ============================================================
# DETECTION REQUEST
# ============================================================

class DetectionRequest(BaseModel):
    """
    Request for final Automatic Discovery detection.

    The final detection uses the fixed top-three recommendation set.
    Best Score trains exactly the one model selected by the user;
    Combined Score trains all three fixed top-three models.

    score_method:
        Controls both the displayed benchmark score and the final
        detection mode.

    contamination_mode:
        Controls whether the default 0.10 contamination or a
        user-supplied contamination value is used.

    selected_model:
        Required for Best Score and ignored for Combined Score.
        Best Score trains exactly this one model. Combined Score
        intentionally trains all three fixed top-three models.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    score_method: ScoreMethod

    contamination_mode: ContaminationMode = "default"

    contamination: float = Field(
        default=0.10,
        ge=0.01,
        le=0.50,
        description=(
            "Custom contamination value. Used only when "
            "contamination_mode='custom'."
        ),
    )

    selected_model: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description=(
            "Required when score_method='best_score'. It identifies "
            "the one model to train. It is intentionally ignored when "
            "score_method='combined_score', where all three fixed "
            "top-three models are trained."
        ),
    )

    @model_validator(mode="after")
    def validate_contamination_mode(
        self,
    ) -> "DetectionRequest":
        """
        Keep the backend-owned default at exactly 0.10.

        If the frontend sends contamination_mode='default' with
        another value, the backend resets it to 0.10 rather than
        allowing an accidental custom value.
        """
        if (
            self.contamination_mode == "default"
            and self.contamination != 0.10
        ):
            self.contamination = 0.10

        return self

    def effective_contamination(self) -> float:
        """
        Return the contamination actually used by detection.
        """
        if self.contamination_mode == "default":
            return 0.10

        return float(self.contamination)