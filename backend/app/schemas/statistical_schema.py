from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# ======================================================================
# Common record schemas
# ======================================================================


class UnivariateRecord(BaseModel):
    """
    One record's IQR result for one numerical column.
    """

    record_number: int
    dataframe_index: Any
    column_name: str
    column_value: Any

    lower_boundary: float
    upper_boundary: float

    boundary_comparison: str

    status: str
    is_anomaly: bool

    reason: str


class UnivariateColumnResult(BaseModel):
    """
    Complete IQR analysis for one numerical column.
    """

    variability: str
    column_name: str
    column_dtype: str

    total_records: int
    anomaly_records: int
    normal_records: int
    anomaly_percentage: float

    method_used: str

    q1: float
    q3: float
    iqr: float

    lower_boundary: float
    upper_boundary: float

    records: list[UnivariateRecord]


class UnivariateSummaryItem(BaseModel):
    """
    Compact row used by the Univariate summary table.
    """

    s_no: int
    column_name: str
    total_anomaly_records: int
    anomaly_percentage: float


class UnivariateResponse(BaseModel):
    """
    Complete response returned by the Univariate API.
    """

    variability: str = "Univariate"
    method_used: str = "IQR"

    eligible_columns: list[str]

    summary: list[UnivariateSummaryItem]

    results: list[UnivariateColumnResult]

    number_of_attributes: int | None = None
    total_records: int | None = None
    dataset_name: str | None = None

    pdf_base64: str | None = None
    pdf_filename: str | None = None

    # ==================================================================
    # Accuracy evaluation
    # ==================================================================

    accuracy: float | None = None

    evaluation: dict[str, Any] | None = None


# ======================================================================
# Multivariate record schemas
# ======================================================================


class MultivariateRecord(BaseModel):
    """
    One record's Mahalanobis result.
    """

    record_number: int
    dataframe_index: Any

    mah_distance: float
    threshold: float

    status: str
    is_anomaly: bool

    feature_values: dict[str, Any]

    interpretation: str


class FeatureContribution(BaseModel):
    """
    Detailed contribution of one feature to a record's
    Mahalanobis squared-distance score.

    Extra fields are explicitly supported because the frontend
    displays detailed calculation information after the user
    selects View.
    """

    model_config = ConfigDict(extra="ignore")

    feature_name: str

    # ==================================================================
    # Compatibility / display fields
    # ==================================================================

    feature: str | None = None
    label: str | None = None

    # ==================================================================
    # Basic feature values
    # ==================================================================

    actual_value: float
    feature_mean: float

    mean_value: float | None = None
    deviation: float | None = None

    # ==================================================================
    # Covariance-adjusted calculation
    # ==================================================================

    covariance_adjusted_deviation: float | None = None

    # ==================================================================
    # Exact Mahalanobis contribution
    # ==================================================================

    contribution: float

    signed_contribution: float | None = None

    absolute_contribution: float

    contribution_percentage: float

    # ==================================================================
    # Optional SHAP information
    # ==================================================================

    shap_value: float | None = None

    absolute_shap_value: float | None = None

    shap_available: bool = False

    # ==================================================================
    # Display metadata
    # ==================================================================

    direction: str | None = None

    formula: str | None = None

    shap_formula: str | None = None

    rank: int

    reason: str


class MultivariateExplanation(BaseModel):
    """
    Dynamic explanation for one record.
    """

    model_config = ConfigDict(extra="ignore")

    record_number: int

    mah_distance: float | None = None

    mahalanobis_score: float | None = None

    threshold: float | None = None

    threshold_gap: float | None = None

    status: str | None = None

    is_anomaly: bool | None = None

    # ==================================================================
    # Existing frontend-compatible field
    # ==================================================================

    feature_contributions: list[FeatureContribution]

    # ==================================================================
    # Detailed contribution fields
    # ==================================================================

    top_contributors: list[FeatureContribution] = Field(
        default_factory=list
    )

    all_feature_contributions: list[FeatureContribution] = Field(
        default_factory=list
    )

    # ==================================================================
    # Feature information
    # ==================================================================

    columns_involved: list[str] = Field(
        default_factory=list
    )

    excluded_constant_columns: list[str] = Field(
        default_factory=list
    )

    actual_feature_values: dict[str, float] = Field(
        default_factory=dict
    )

    # ==================================================================
    # Mathematical validation
    # ==================================================================

    calculated_mahalanobis_distance: float | None = None

    calculated_mahalanobis_squared_distance: float | None = None

    signed_contribution_sum: float | None = None

    score_consistency: dict[str, Any] = Field(
        default_factory=dict
    )

    # ==================================================================
    # SHAP information
    # ==================================================================

    explanation_method: str | None = None

    shap_available: bool = False

    shap_library_available: bool = False

    shap_base_value: float | None = None

    shap_reconstructed_squared_score: float | None = None

    shap_score_difference: float | None = None

    shap_error: str | None = None

    # ==================================================================
    # Calculation explanation
    # ==================================================================

    calculation_summary: dict[str, Any] = Field(
        default_factory=dict
    )

    explanation: str | None = None


# ======================================================================
# Multivariate response
# ======================================================================


class MultivariateResponse(BaseModel):
    """
    Complete response returned by the Multivariate API.

    Includes:
        - Mahalanobis anomaly detection results
        - generated PDF report
        - controlled accuracy evaluation
        - evaluation statistics
    """

    variability: str = "Multivariate"

    method_used: str = "Mahalanobis Distance"

    # ==================================================================
    # Feature information
    # ==================================================================

    columns_involved: list[str]

    all_preprocessed_columns: list[str]

    constant_columns_excluded: list[str] = Field(
        default_factory=list
    )

    total_columns_involved: int

    # ==================================================================
    # Detection summary
    # ==================================================================

    total_records: int

    anomaly_records: int

    normal_records: int

    anomaly_percentage: float

    # ==================================================================
    # Mahalanobis threshold information
    # ==================================================================

    threshold: float

    threshold_method: str

    threshold_quantile: float

    # ==================================================================
    # Individual record results
    # ==================================================================

    records: list[MultivariateRecord]

    # ==================================================================
    # Dataset / report information
    # ==================================================================

    dataset_name: str | None = None

    pdf_base64: str | None = None

    pdf_filename: str | None = None

    # ==================================================================
    # Accuracy evaluation
    # ==================================================================

    accuracy: float | None = None

    evaluation: dict[str, Any] | None = None


# ======================================================================
# Explainability request / response
# ======================================================================


class MultivariateExplainRequest(BaseModel):
    """
    Request to explain one already detected record.
    """

    record_number: int = Field(
        ...,
        ge=1,
        description="1-based record number.",
    )

    top_n: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of top contributing features.",
    )

    mah_distance: float | None = None

    threshold: float | None = None


class MultivariateExplainResponse(BaseModel):
    """
    Response containing the dynamic feature explanation.
    """

    model_config = ConfigDict(extra="ignore")

    record_number: int

    # ==================================================================
    # Mahalanobis information
    # ==================================================================

    mah_distance: float | None = None

    mahalanobis_score: float | None = None

    threshold: float | None = None

    threshold_gap: float | None = None

    status: str | None = None

    is_anomaly: bool | None = None

    # ==================================================================
    # Existing-compatible field
    # ==================================================================

    feature_contributions: list[FeatureContribution]

    # ==================================================================
    # Full contribution list used by Explore
    # ==================================================================

    top_contributors: list[FeatureContribution] = Field(
        default_factory=list
    )

    all_feature_contributions: list[FeatureContribution] = Field(
        default_factory=list
    )

    # ==================================================================
    # Feature details
    # ==================================================================

    columns_involved: list[str] = Field(
        default_factory=list
    )

    excluded_constant_columns: list[str] = Field(
        default_factory=list
    )

    actual_feature_values: dict[str, float] = Field(
        default_factory=dict
    )

    # ==================================================================
    # Mathematical validation
    # ==================================================================

    calculated_mahalanobis_distance: float | None = None

    calculated_mahalanobis_squared_distance: float | None = None

    signed_contribution_sum: float | None = None

    score_consistency: dict[str, Any] = Field(
        default_factory=dict
    )

    # ==================================================================
    # Explainability method
    # ==================================================================

    explanation_method: str | None = None

    shap_available: bool = False

    shap_library_available: bool = False

    shap_base_value: float | None = None

    shap_reconstructed_squared_score: float | None = None

    shap_score_difference: float | None = None

    shap_error: str | None = None

    # ==================================================================
    # Calculation explanation
    # ==================================================================

    calculation_summary: dict[str, Any] = Field(
        default_factory=dict
    )

    explanation: str | None = None


# ======================================================================
# Statistical approach selection
# ======================================================================


class StatisticalApproachRequest(BaseModel):
    """
    Request sent when the user chooses a statistical approach.
    """

    dataset_id: str = Field(
        ...,
        min_length=1,
    )

    approach: str = Field(
        ...,
        description="Expected values: univariate or multivariate.",
    )


class StatisticalApproachResponse(BaseModel):
    """
    Response confirming the selected statistical approach.
    """

    dataset_id: str

    approach: str

    message: str


# ======================================================================
# Generic API error
# ======================================================================


class StatisticalErrorResponse(BaseModel):
    """
    Standard error response for statistical endpoints.
    """

    detail: str