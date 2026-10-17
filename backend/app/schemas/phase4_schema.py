from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================
# PHASE 4
# OBJECTIVE REQUEST
# ============================================================

class ObjectiveRequest(BaseModel):
    """
    Natural-language detection objective supplied by
    the investigator.
    """

    objective: str = Field(
        ...,
        min_length=1,
        description=(
            "Natural-language anomaly detection objective."
        ),
    )


# ============================================================
# PHASE 4
# RECOMMENDED COLUMN
# ============================================================

class ObjectiveColumn(BaseModel):
    """
    Semantically recommended dataset column.

    The column must come from the actual dataset.

    reason:
        Explanation of why the column is relevant.

    confidence:
        Semantic confidence assigned by the LLM.

    evidence:
        Supporting semantic evidence used for the recommendation.
    """

    column: str

    reason: str = ""

    confidence: Optional[float] = None

    evidence: Optional[str] = None


# ============================================================
# PHASE 4
# OBJECTIVE UNDERSTANDING
# ============================================================

class ObjectiveUnderstanding(BaseModel):
    """
    Complete semantic interpretation of the investigator's
    natural-language anomaly-detection objective.

    Phase 4 determines:

        - what the investigator wants to detect
        - inferred anomaly type
        - comparison scope
        - detection behavior
        - temporal requirement
        - relevant target columns
        - reference columns
        - context columns
        - assumptions
        - warnings

    Attribute selection validation is performed separately
    against the confirmed Phase 2 selection.
    """

    # --------------------------------------------------------
    # ORIGINAL OBJECTIVE
    # --------------------------------------------------------

    original_objective: Optional[str] = None

    # --------------------------------------------------------
    # SEMANTIC INTERPRETATION
    # --------------------------------------------------------

    interpreted_objective: str

    # --------------------------------------------------------
    # ANOMALY TYPE
    # --------------------------------------------------------

    anomaly_type: str

    anomaly_type_confidence: Optional[float] = None

    anomaly_type_reason: str = ""

    # --------------------------------------------------------
    # COMPARISON SCOPE
    # --------------------------------------------------------

    comparison_scope: str = "none"

    comparison_scope_confidence: Optional[float] = None

    comparison_scope_reason: str = ""

    # --------------------------------------------------------
    # DETECTION BEHAVIOR
    # --------------------------------------------------------

    detection_behavior: str = ""

    detection_behavior_reason: str = ""

    # --------------------------------------------------------
    # TEMPORAL REQUIREMENT
    # --------------------------------------------------------

    temporal_requirement: str = "unclear"

    temporal_requirement_reason: str = ""

    # --------------------------------------------------------
    # TARGET COLUMNS
    # --------------------------------------------------------

    target_columns: List[ObjectiveColumn] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # REFERENCE COLUMNS
    # --------------------------------------------------------

    reference_columns: List[ObjectiveColumn] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # CONTEXT COLUMNS
    # --------------------------------------------------------

    context_columns: List[ObjectiveColumn] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # ALL OBJECTIVE-REQUIRED ATTRIBUTES
    # --------------------------------------------------------

    attributes_involved: List[ObjectiveColumn] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # ATTRIBUTE SELECTION VALIDATION
    # --------------------------------------------------------

    attribute_selection_valid: bool = True

    missing_attributes: List[str] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # ASSUMPTIONS
    # --------------------------------------------------------

    assumptions: List[str] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # WARNINGS
    # --------------------------------------------------------

    warnings: List[str] = Field(
        default_factory=list
    )


# ============================================================
# PHASE 5
# SCORE DETAIL
# ============================================================

class ScoreDetail(BaseModel):
    """
    Individual statistical or objective scoring contribution
    used by Phase 5 model recommendation.
    """

    factor: Optional[str] = None

    name: Optional[str] = None

    score: float = 0.0

    maximum: Optional[float] = None

    max_score: Optional[float] = None

    reason: str = ""

    evidence: Optional[str] = None


# ============================================================
# PHASE 5
# MODEL RECOMMENDATION
# ============================================================

class ModelRecommendation(BaseModel):
    """
    Model recommendation generated during Phase 5.

    Statistical suitability:
        Maximum 70 points.

    Objective matching:
        Maximum 30 points.

    Final score:
        Maximum 100 points.
    """

    model: str

    description: Optional[str] = None

    # --------------------------------------------------------
    # STATISTICAL SCORE
    # --------------------------------------------------------

    statistical_score: float = 0.0

    statistical_maximum: float = 70.0

    statistical_max_score: Optional[float] = 70.0

    # --------------------------------------------------------
    # OBJECTIVE SCORE
    # --------------------------------------------------------

    objective_score: float = 0.0

    objective_maximum: float = 30.0

    objective_max_score: Optional[float] = 30.0

    # --------------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------------

    final_score: float = 0.0

    final_maximum: float = 100.0

    final_max_score: Optional[float] = 100.0

    # --------------------------------------------------------
    # SCORE DETAILS
    # --------------------------------------------------------

    statistical_details: List[ScoreDetail] = Field(
        default_factory=list
    )

    objective_details: List[ScoreDetail] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # MODEL EXPLANATION
    # --------------------------------------------------------

    strengths: List[str] = Field(
        default_factory=list
    )

    limitations: List[str] = Field(
        default_factory=list
    )

    recommendation_reason: Optional[str] = None

    rank: Optional[int] = None


# ============================================================
# PHASE 4
# ANALYSIS RESPONSE
# ============================================================

class Phase4AnalysisResponse(BaseModel):
    """
    Response returned after Phase 4 objective analysis.
    """

    dataset_id: str

    objective: ObjectiveUnderstanding

    recommendations: List[ModelRecommendation] = Field(
        default_factory=list
    )

    confirmed: bool = False


# ============================================================
# PHASE 4
# CONFIRM RESPONSE
# ============================================================

class Phase4ConfirmResponse(BaseModel):
    """
    Response returned when the investigator confirms the
    Phase 4 objective understanding.

    Phase 4 cannot be confirmed while attribute-selection
    validation has failed.
    """

    dataset_id: str

    confirmed: bool

    objective: ObjectiveUnderstanding

    recommendations: List[ModelRecommendation] = Field(
        default_factory=list
    )