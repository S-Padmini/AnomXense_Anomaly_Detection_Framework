from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

# Exact descriptive statistics remain full-data; only expensive exploratory
# clustering and nearest-neighbour analyses use a deterministic bounded sample.
EXPENSIVE_ANALYSIS_SAMPLE_SIZE = 1000
SILHOUETTE_SAMPLE_SIZE = 750


# ============================================================
# Utility Functions
# ============================================================

def _finite_float(value: Any, digits: int = 4) -> float | None:
    """
    Convert a value to a finite rounded float.
    Returns None when the value cannot be represented safely.
    """
    try:
        value = float(value)

        if math.isfinite(value):
            return round(value, digits)

        return None

    except Exception:
        return None


def _distribution_label(skew: float) -> str:
    """
    Interpretation of skewness.
    The actual skewness value is always returned separately.
    """
    absolute_skew = abs(skew)

    if absolute_skew <= 0.5:
        return "Approximately Symmetric"

    if absolute_skew <= 1:
        return "Moderately Skewed"

    return "Highly Skewed"


def _relationship(r: float) -> str:
    """
    Interpretation of Pearson correlation.
    The actual correlation value is always shown separately.
    """
    absolute_r = abs(r)

    if absolute_r < 0.1:
        return "Very Weak"

    if absolute_r < 0.3:
        return "Weak"

    if absolute_r < 0.7:
        return "Moderate"

    if absolute_r < 0.9:
        return "Strong"

    return "Very Strong"


def _scale_label(ratio: float) -> str:
    """
    Interpretation of feature-range ratio.
    """
    if ratio <= 10:
        return "Similar"

    if ratio <= 100:
        return "Different"

    if ratio <= 1000:
        return "Very Different"

    return "Highly Different"


def _cluster_label(silhouette: float) -> str:
    """
    Interpretation of silhouette score.

    These are interpretation labels only.
    The actual silhouette score is always returned.
    """
    if silhouette >= 0.50:
        return "Strong"

    if silhouette >= 0.25:
        return "Moderate"

    return "Weak"


# ============================================================
# Large-data helper
# ============================================================

def _bounded_analysis_sample(X: np.ndarray) -> tuple[np.ndarray, bool]:
    """Return all rows for small inputs or a deterministic sample for costly analyses."""
    values = np.asarray(X)
    if len(values) <= EXPENSIVE_ANALYSIS_SAMPLE_SIZE:
        return values, False
    rng = np.random.default_rng(42)
    positions = np.sort(rng.choice(len(values), size=EXPENSIVE_ANALYSIS_SAMPLE_SIZE, replace=False))
    return values[positions], True


# ============================================================
# 7. Cluster Structure Analysis
# ============================================================

def _cluster_analysis(X: np.ndarray) -> dict[str, Any]:
    """
    Evaluate K-Means cluster structure using silhouette score.

    Tested k values:
        2 through min(8, n-1)

    The best k is the one with the highest silhouette score.
    """

    total_n = len(X)
    X, sampled = _bounded_analysis_sample(X)
    n = len(X)

    if n < 4:
        return {
            "estimated_clusters": None,
            "silhouette_score": None,
            "cluster_structure": "Unavailable",
            "cluster_scores": [],
            "reason": "At least 4 records are required.",
            "sampled": sampled,
            "total_observations": int(total_n),
            "observations_analyzed": int(n),
        }

    cluster_scores: list[dict[str, Any]] = []

    best_k = None
    best_score = -1.0

    max_k = min(8, n - 1)

    for k in range(2, max_k + 1):

        try:
            model = KMeans(
                n_clusters=k,
                n_init=10,
                random_state=42,
            )

            labels = model.fit_predict(X)

            if len(set(labels)) < 2:
                continue

            score = float(
                silhouette_score(
                    X,
                    labels,
                    sample_size=min(SILHOUETTE_SAMPLE_SIZE, len(X)),
                    random_state=42,
                )
            )

            cluster_scores.append(
                {
                    "clusters": int(k),
                    "silhouette_score": _finite_float(score),
                }
            )

            if score > best_score:
                best_k = k
                best_score = score

        except Exception:
            continue

    if best_k is None:
        return {
            "estimated_clusters": None,
            "silhouette_score": None,
            "cluster_structure": "Unavailable",
            "cluster_scores": cluster_scores,
            "reason": "Cluster structure could not be estimated.",
            "sampled": sampled,
            "total_observations": int(total_n),
            "observations_analyzed": int(n),
        }

    label = _cluster_label(best_score)

    return {
        "estimated_clusters": int(best_k),
        "silhouette_score": _finite_float(best_score),
        "cluster_structure": label,
        "cluster_scores": cluster_scores,
        "reason": None,
        "sampled": sampled,
        "total_observations": int(total_n),
        "observations_analyzed": int(n),
    }


# ============================================================
# 8. Local Density & Neighborhood Analysis
# ============================================================

def _density_analysis(X: np.ndarray) -> dict[str, Any]:
    """
    Simple nearest-neighbor density analysis.

    Only two primary measurements are used:
        1. Mean nearest-neighbor distance
        2. Coefficient of variation (CV)

    No additional density algorithms are performed.
    """

    total_n = len(X)
    X, sampled = _bounded_analysis_sample(X)
    n = len(X)

    if n < 3:
        return {
            "observations_analyzed": n,
            "mean_nearest_neighbor_distance": None,
            "density_variability_cv": None,
            "local_density": "Unavailable",
            "sampled": sampled,
            "total_observations": int(total_n),
        }

    # n_neighbors=2 because the first returned distance is
    # distance to the observation itself (0).
    model = NearestNeighbors(n_neighbors=2)

    model.fit(X)

    distances, _ = model.kneighbors(X)

    nearest_distances = distances[:, 1]

    mean_distance = float(np.mean(nearest_distances))

    if n > 1:
        std_distance = float(np.std(nearest_distances, ddof=1))
    else:
        std_distance = 0.0

    if mean_distance > 0:
        cv = std_distance / mean_distance
    else:
        cv = 0.0

    local_density = (
        "Variable"
        if cv >= 0.30
        else "Relatively Uniform"
    )

    return {
        "observations_analyzed": int(n),
        "total_observations": int(total_n),
        "sampled": sampled,
        "mean_nearest_neighbor_distance": _finite_float(
            mean_distance
        ),
        "density_variability_cv": _finite_float(cv),
        "local_density": local_density,
    }


# ============================================================
# 9. Temporal Structure Analysis
# ============================================================

def _temporal_structure_analysis(
    df: pd.DataFrame,
    datetime_columns: list[str],
) -> dict[str, Any]:
    """
    Analyze the STRUCTURE of the temporal column.

    This analysis does NOT analyze numerical behaviour.

    It checks only:
        - valid timestamps
        - chronological ordering
        - timestamp intervals
        - interval regularity
    """

    if not datetime_columns:
        return {
            "temporal_column": None,
            "valid_timestamps": 0,
            "invalid_or_missing_timestamps": 0,
            "chronological_ordering": "Not applicable",
            "interval": None,
            "interval_unit": None,
            "regular_intervals": "Not applicable",
            "temporal_structure": "No Temporal Structure",
        }

    temporal_column = datetime_columns[0]

    raw_dates = pd.to_datetime(
        df[temporal_column],
        errors="coerce",
        format="mixed",
    )

    valid_dates = raw_dates.dropna()

    valid_count = int(len(valid_dates))

    invalid_count = int(len(raw_dates) - valid_count)

    if valid_count < 2:

        return {
            "temporal_column": temporal_column,
            "valid_timestamps": valid_count,
            "invalid_or_missing_timestamps": invalid_count,
            "chronological_ordering": "Not enough data",
            "interval": None,
            "interval_unit": None,
            "regular_intervals": "Not enough data",
            "temporal_structure": "Insufficient Temporal Data",
        }

    # Sort only for interval analysis.
    ordered_dates = valid_dates.sort_values()

    # Determine whether the original valid observations
    # were already chronologically ordered.
    original_values = valid_dates.reset_index(drop=True)

    chronological_ordering = bool(
        original_values.is_monotonic_increasing
    )

    deltas = (
        ordered_dates
        .diff()
        .dropna()
        .dt.total_seconds()
    )

    if deltas.empty:

        return {
            "temporal_column": temporal_column,
            "valid_timestamps": valid_count,
            "invalid_or_missing_timestamps": invalid_count,
            "chronological_ordering": chronological_ordering,
            "interval": None,
            "interval_unit": None,
            "regular_intervals": "Not enough data",
            "temporal_structure": "Structured",
        }

    median_seconds = float(deltas.median())

    # Convert interval into the most meaningful unit.
    if median_seconds >= 86400:
        interval_value = median_seconds / 86400
        interval_unit = "day"

    elif median_seconds >= 3600:
        interval_value = median_seconds / 3600
        interval_unit = "hour"

    elif median_seconds >= 60:
        interval_value = median_seconds / 60
        interval_unit = "minute"

    else:
        interval_value = median_seconds
        interval_unit = "second"

    # Regularity is determined from the actual interval values.
    regular_intervals = bool(
        np.allclose(
            deltas.to_numpy(dtype=float),
            median_seconds,
            rtol=0.01,
            atol=1e-6,
        )
    )

    temporal_structure = (
        "Structured"
        if chronological_ordering and regular_intervals
        else "Partially Structured"
    )

    return {
        "temporal_column": temporal_column,
        "valid_timestamps": valid_count,
        "invalid_or_missing_timestamps": invalid_count,
        "chronological_ordering": (
            "Yes" if chronological_ordering else "No"
        ),
        "interval": _finite_float(interval_value, 4),
        "interval_unit": interval_unit,
        "regular_intervals": (
            "Yes" if regular_intervals else "No"
        ),
        "temporal_structure": temporal_structure,
    }


# ============================================================
# 10. Time-Series Pattern Analysis
# ============================================================

def _time_series_pattern_analysis(
    df: pd.DataFrame,
    datetime_columns: list[str],
    numeric_columns: list[str],
) -> dict[str, Any]:
    """
    Simple temporal pattern analysis.

    ONLY lag-1 autocorrelation is calculated.

    This is intentionally different from Temporal Structure Analysis:

        #9 -> structure of timestamps
        #10 -> sequential relationship between numerical values
    """

    if not datetime_columns:

        return {
            "temporal_column": None,
            "numerical_signals": [],
            "pattern_analysis": [],
            "selected_signal": None,
            "lag": 1,
            "autocorrelation": None,
            "result": "Unavailable",
            "reason": "A valid date/time column is required.",
        }

    if not numeric_columns:

        return {
            "temporal_column": datetime_columns[0],
            "numerical_signals": [],
            "pattern_analysis": [],
            "selected_signal": None,
            "lag": 1,
            "autocorrelation": None,
            "result": "Unavailable",
            "reason": "At least one numerical signal is required.",
        }

    temporal_column = datetime_columns[0]

    # Copy only the date and numeric signals required for this calculation.
    # Avoid duplicating all categorical columns for large datasets.
    working = pd.DataFrame({
        "_analysis_datetime": pd.to_datetime(
            df[temporal_column], errors="coerce", format="mixed"
        )
    })
    for column in numeric_columns:
        working[column] = pd.to_numeric(df[column], errors="coerce")

    working = working.dropna(subset=["_analysis_datetime"]).sort_values(
        "_analysis_datetime", kind="mergesort"
    )

    pattern_rows: list[dict[str, Any]] = []

    for column in numeric_columns:

        values = pd.to_numeric(
            working[column],
            errors="coerce",
        )

        valid = values.dropna()

        if len(valid) < 3:
            continue

        autocorrelation = valid.autocorr(lag=1)

        if pd.isna(autocorrelation):
            continue

        autocorrelation = float(autocorrelation)

        if autocorrelation >= 0.7:
            interpretation = "Strong Sequential Dependence"

        elif autocorrelation >= 0.3:
            interpretation = "Moderate Sequential Dependence"

        elif autocorrelation > -0.3:
            interpretation = "Weak Sequential Dependence"

        elif autocorrelation > -0.7:
            interpretation = "Moderate Negative Sequential Dependence"

        else:
            interpretation = "Strong Negative Sequential Dependence"

        pattern_rows.append(
            {
                "feature": column,
                "observations": int(len(valid)),
                "lag": 1,
                "autocorrelation": _finite_float(
                    autocorrelation
                ),
                "interpretation": interpretation,
            }
        )

    if not pattern_rows:

        return {
            "temporal_column": temporal_column,
            "numerical_signals": numeric_columns,
            "pattern_analysis": [],
            "selected_signal": None,
            "lag": 1,
            "autocorrelation": None,
            "result": "Unavailable",
            "reason": (
                "Insufficient valid numerical observations "
                "for lag-1 autocorrelation."
            ),
        }

    # Select the strongest absolute sequential relationship.
    strongest = max(
        pattern_rows,
        key=lambda row: abs(
            float(row["autocorrelation"])
        ),
    )

    return {
        "temporal_column": temporal_column,
        "numerical_signals": numeric_columns,
        "pattern_analysis": pattern_rows,
        "selected_signal": strongest["feature"],
        "lag": 1,
        "autocorrelation": strongest["autocorrelation"],
        "result": strongest["interpretation"],
        "reason": None,
    }


# ============================================================
# MAIN STATISTICAL ANALYSIS
# ============================================================

def analyze_statistics(
    df: pd.DataFrame,
    selected_columns: list[str],
    summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Complete Phase 3 statistical analysis.

    The analysis contains exactly 10 characteristics:

        1. Dataset Size & Dimensionality
        2. Data Type & Feature Composition
        3. Distribution Analysis
        4. Extreme Value Analysis
        5. Feature Scale Analysis
        6. Correlation Analysis
        7. Cluster Structure Analysis
        8. Local Density & Neighborhood Analysis
        9. Temporal Structure Analysis
        10. Time-Series Pattern Analysis
    """

    # --------------------------------------------------------
    # Determine selected feature types
    # --------------------------------------------------------

    numeric_columns = [
        column
        for column in summary.get(
            "numeric_column_names",
            [],
        )
        if column in selected_columns
        and column in df.columns
    ]

    datetime_columns = [
        column
        for column in summary.get(
            "datetime_column_names",
            [],
        )
        if column in selected_columns
        and column in df.columns
    ]

    categorical_columns = [
        column
        for column in selected_columns
        if column in df.columns
        and column not in numeric_columns
        and column not in datetime_columns
    ]

    # --------------------------------------------------------
    # 3, 4, 5 - Numerical calculations
    # --------------------------------------------------------

    distributions: list[dict[str, Any]] = []
    extreme_rows: list[dict[str, Any]] = []
    scale_rows: list[dict[str, Any]] = []

    for column in numeric_columns:

        values = pd.to_numeric(
            df[column],
            errors="coerce",
        ).dropna()

        if values.empty:
            continue

        mean = float(values.mean())

        median = float(values.median())

        std = (
            float(values.std(ddof=1))
            if len(values) > 1
            else 0.0
        )

        skew = (
            float(values.skew())
            if len(values) >= 3
            else 0.0
        )

        # IQR
        q1 = float(values.quantile(0.25))
        q3 = float(values.quantile(0.75))

        iqr = q3 - q1

        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)

        extreme_count = int(
            (
                (values < lower_bound)
                | (values > upper_bound)
            ).sum()
        )

        minimum = float(values.min())
        maximum = float(values.max())

        feature_range = maximum - minimum

        # Distribution
        distributions.append(
            {
                "feature": column,
                "mean": _finite_float(mean),
                "median": _finite_float(median),
                "std": _finite_float(std),
                "skewness": _finite_float(skew),
                "distribution": _distribution_label(skew),
            }
        )

        # Extreme values
        extreme_rows.append(
            {
                "feature": column,
                "q1": _finite_float(q1),
                "q3": _finite_float(q3),
                "iqr": _finite_float(iqr),
                "lower_bound": _finite_float(
                    lower_bound
                ),
                "upper_bound": _finite_float(
                    upper_bound
                ),
                "extreme_values": extreme_count,
                "extreme_percentage": _finite_float(
                    (
                        extreme_count
                        / len(values)
                        * 100
                    )
                ),
            }
        )

        # Scale
        scale_rows.append(
            {
                "feature": column,
                "minimum": _finite_float(minimum),
                "maximum": _finite_float(maximum),
                "range": _finite_float(
                    feature_range
                ),
                "std": _finite_float(std),
            }
        )

    # --------------------------------------------------------
    # 6 - Pearson Correlation
    # --------------------------------------------------------

    correlation_rows: list[dict[str, Any]] = []

    if len(numeric_columns) >= 2:

        numeric_df = df[numeric_columns].apply(
            pd.to_numeric,
            errors="coerce",
        )

        correlation_matrix = numeric_df.corr(
            method="pearson"
        )

        for i, feature_a in enumerate(
            numeric_columns
        ):

            for feature_b in numeric_columns[
                i + 1:
            ]:

                value = correlation_matrix.loc[
                    feature_a,
                    feature_b,
                ]

                if pd.notna(value):

                    correlation_value = float(
                        value
                    )

                    correlation_rows.append(
                        {
                            "feature_a": feature_a,
                            "feature_b": feature_b,
                            "correlation": _finite_float(
                                correlation_value
                            ),
                            "relationship": _relationship(
                                correlation_value
                            ),
                        }
                    )

    # --------------------------------------------------------
    # 5 - Feature scale summary
    # --------------------------------------------------------

    ranges = [
        float(row["range"])
        for row in scale_rows
        if row["range"] is not None
        and float(row["range"]) > 0
    ]

    if ranges:

        smallest_range = min(ranges)

        largest_range = max(ranges)

        scale_ratio = (
            largest_range
            / smallest_range
        )

        scale_classification = _scale_label(
            scale_ratio
        )

    else:

        smallest_range = None
        largest_range = None
        scale_ratio = None
        scale_classification = "Unavailable"

    # --------------------------------------------------------
    # 7 - Cluster + 8 - Density
    #
    # These use standardized numerical values.
    # Missing numerical values are median-imputed only
    # for these calculations.
    # --------------------------------------------------------

    cluster_result = {
        "estimated_clusters": None,
        "silhouette_score": None,
        "cluster_structure": "Unavailable",
        "cluster_scores": [],
        "reason": "No suitable numerical matrix.",
    }

    density_result = {
        "observations_analyzed": 0,
        "mean_nearest_neighbor_distance": None,
        "density_variability_cv": None,
        "local_density": "Unavailable",
    }

    if numeric_columns and len(df) >= 4:

        numerical_matrix = df[
            numeric_columns
        ].apply(
            pd.to_numeric,
            errors="coerce",
        )

        # Median imputation here is ONLY for preparing
        # the numerical matrix required by cluster/density
        # calculations. It does not alter the original df.
        numerical_matrix = numerical_matrix.fillna(
            numerical_matrix.median()
        )

        numerical_matrix = numerical_matrix.dropna(
            axis=0,
            how="any",
        )

        if (
            len(numerical_matrix) >= 4
            and numerical_matrix.shape[1] >= 1
        ):

            scaler = StandardScaler()

            X = scaler.fit_transform(
                numerical_matrix
            )

            cluster_result = _cluster_analysis(X)

            density_result = _density_analysis(X)

    # --------------------------------------------------------
    # 9 - Temporal Structure
    # --------------------------------------------------------

    temporal = _temporal_structure_analysis(
        df,
        datetime_columns,
    )

    # --------------------------------------------------------
    # 10 - Time-Series Pattern
    # --------------------------------------------------------

    time_series = _time_series_pattern_analysis(
        df,
        datetime_columns,
        numeric_columns,
    )

    # --------------------------------------------------------
    # General summary values
    # --------------------------------------------------------

    row_count = int(len(df))

    feature_count = int(len(selected_columns))

    numerical_count = int(
        len(numeric_columns)
    )

    categorical_count = int(
        len(categorical_columns)
    )

    datetime_count = int(
        len(datetime_columns)
    )

    abs_skews = [
        abs(float(row["skewness"]))
        for row in distributions
        if row["skewness"] is not None
    ]

    average_absolute_skewness = (
        float(np.mean(abs_skews))
        if abs_skews
        else 0.0
    )

    maximum_absolute_skewness = (
        max(abs_skews)
        if abs_skews
        else 0.0
    )

    strongest_correlation = max(
        (
            abs(
                float(
                    row["correlation"]
                )
            )
            for row in correlation_rows
            if row["correlation"] is not None
        ),
        default=0.0,
    )

    total_extreme_values = sum(
        int(row["extreme_values"])
        for row in extreme_rows
    )

    # --------------------------------------------------------
    # 1 - Dataset Size & Dimensionality
    # --------------------------------------------------------

    dataset_size = (
        "Small"
        if row_count < 5000
        else "Medium"
        if row_count < 100000
        else "Large"
    )

    dimensionality = (
        "Low"
        if feature_count <= 10
        else "Moderate"
        if feature_count <= 50
        else "High"
    )

    if numeric_columns and categorical_columns:
        data_type = "Mixed"

    elif numeric_columns:
        data_type = "Numerical"

    elif categorical_columns:
        data_type = "Categorical"

    elif datetime_columns:
        data_type = "Date/Time"

    else:
        data_type = "Other"

    # --------------------------------------------------------
    # 2 - Feature Composition
    # --------------------------------------------------------

    # --------------------------------------------------------
    # 1. Dataset Size & Dimensionality
    # --------------------------------------------------------

    sections = {

        "overview": {

            "title": "1. Dataset Size & Dimensionality",

            "result": dataset_size,

            "dataset_overview": {
                "records": row_count,
                "features": feature_count,
                "dataset_size": dataset_size,
                "dimensionality": dimensionality,
                "data_type": data_type,
            },

            "inferences": [
                (
                    f"The processed dataset contains "
                    f"{row_count} records across "
                    f"{feature_count} selected feature(s), "
                    f"giving a {dataset_size.lower()} "
                    f"dataset profile."
                ),
                (
                    f"The dataset contains "
                    f"{numerical_count} numerical, "
                    f"{categorical_count} categorical, "
                    f"and {datetime_count} date/time "
                    f"feature(s)."
                ),
            ],
        },

        # ----------------------------------------------------
        # 2. Data Type & Feature Composition
        # ----------------------------------------------------

        "types": {

            "title": "2. Data Type & Feature Composition",

            "result": f"{numerical_count} Numerical",

            "feature_composition": {

                "numerical": {
                    "count": numerical_count,
                    "columns": numeric_columns,
                },

                "categorical": {
                    "count": categorical_count,
                    "columns": categorical_columns,
                },

                "date_time": {
                    "count": datetime_count,
                    "columns": datetime_columns,
                },
            },

            "inferences": [
                (
                    f"{numerical_count} numerical "
                    f"feature(s) are available for "
                    f"quantitative statistical analysis."
                    if numerical_count
                    else
                    "No numerical feature was selected "
                    "for quantitative statistical analysis."
                ),
                (
                    f"{datetime_count} date/time feature(s) "
                    f"are available for temporal analysis."
                    if datetime_count
                    else
                    "No date/time feature was selected "
                    "for temporal analysis."
                ),
            ],
        },

        # ----------------------------------------------------
        # 3. Distribution Analysis
        # ----------------------------------------------------

        "distribution": {

            "title": "3. Distribution Analysis",

            "result": "Calculated"
            if distributions
            else "Unavailable",

            "distribution_statistics": distributions,

            "summary": {
                "features_analyzed": len(
                    distributions
                ),
                "average_absolute_skewness":
                    _finite_float(
                        average_absolute_skewness
                    ),
                "maximum_absolute_skewness":
                    _finite_float(
                        maximum_absolute_skewness
                    ),
            },

            "inferences": [

                (
                    f"The average absolute skewness is "
                    f"{average_absolute_skewness:.4f}, "
                    f"indicating low overall distribution "
                    f"asymmetry."
                    if average_absolute_skewness <= 0.5
                    else
                    f"The average absolute skewness is "
                    f"{average_absolute_skewness:.4f}, "
                    f"indicating noticeable distribution "
                    f"asymmetry."
                ),

                (
                    f"The maximum absolute skewness is "
                    f"{maximum_absolute_skewness:.4f}."
                    if distributions
                    else
                    "No numerical distributions were "
                    "available for analysis."
                ),
            ],
        },

        # ----------------------------------------------------
        # 4. Extreme Value Analysis
        # ----------------------------------------------------

        "extreme": {

            "title": "4. Extreme Value Analysis",

            "result": (
                f"{total_extreme_values} Extreme"
            ),

            "iqr_analysis": extreme_rows,

            "summary": {
                "features_analyzed": len(
                    extreme_rows
                ),
                "total_extreme_values":
                    total_extreme_values,
            },

            "inferences": [

                (
                    f"The IQR rule identifies "
                    f"{total_extreme_values} "
                    f"extreme observation(s) across "
                    f"the analyzed numerical features."
                ),

                (
                    "No IQR-extreme observations were "
                    "detected."
                    if total_extreme_values == 0
                    else
                    "IQR-extreme observations were detected. "
                    "They were retained because extreme "
                    "values may represent genuine anomalies."
                ),
            ],
        },

        # ----------------------------------------------------
        # 5. Feature Scale Analysis
        # ----------------------------------------------------

        "scale": {

            "title": "5. Feature Scale Analysis",

            "result": scale_classification,

            "feature_scale": scale_rows,

            "scale_summary": {

                "smallest_non_zero_range":
                    _finite_float(
                        smallest_range
                    ),

                "largest_range":
                    _finite_float(
                        largest_range
                    ),

                "range_ratio":
                    _finite_float(
                        scale_ratio
                    ),
            },

            "range_ratio": _finite_float(
                scale_ratio
            ),

            "inferences": [

                (
                    f"The largest-to-smallest "
                    f"non-zero feature-range ratio "
                    f"is {scale_ratio:.2f}×, "
                    f"indicating {scale_classification.lower()} "
                    f"feature scales."
                    if scale_ratio is not None
                    else
                    "A scale ratio could not be "
                    "computed because no usable "
                    "numerical ranges were available."
                ),

                (
                    "The numerical feature ranges are "
                    "substantially different, so scale "
                    "should be considered when evaluating "
                    "distance-based anomaly detection methods."
                    if scale_ratio is not None
                    and scale_ratio > 10
                    else
                    "The numerical feature ranges are "
                    "relatively similar."
                ),
            ],
        },

        # ----------------------------------------------------
        # 6. Correlation Analysis
        # ----------------------------------------------------

        "correlation": {

            "title": "6. Correlation Analysis",

            "result": (
                _relationship(
                    strongest_correlation
                )
                if correlation_rows
                else "Unavailable"
            ),

            "pearson_correlation":
                correlation_rows,

            "summary": {

                "feature_pairs_analyzed":
                    len(correlation_rows),

                "strongest_absolute_correlation":
                    _finite_float(
                        strongest_correlation
                    ),
            },

            "inferences": [

                (
                    f"The strongest absolute Pearson "
                    f"correlation is "
                    f"{strongest_correlation:.4f}, "
                    f"indicating an overall "
                    f"{_relationship(strongest_correlation).lower()} "
                    f"linear relationship among "
                    f"numerical features."
                    if correlation_rows
                    else
                    "At least two numerical features "
                    "are required for correlation analysis."
                ),

                (
                    "No feature pair reaches |r| ≥ 0.70."
                    if correlation_rows
                    and strongest_correlation < 0.70
                    else
                    "At least one feature pair reaches "
                    "|r| ≥ 0.70."
                    if correlation_rows
                    else
                    "Correlation analysis could not "
                    "be performed."
                ),
            ],
        },

        # ----------------------------------------------------
        # 7. Cluster Structure Analysis
        # ----------------------------------------------------

        "cluster": {

            "title": "7. Cluster Structure Analysis",

            "result":
                cluster_result[
                    "cluster_structure"
                ],

            "cluster_analysis":
                cluster_result,

            "inferences": [

                (
                    f"The best tested cluster count "
                    f"is {cluster_result['estimated_clusters']}, "
                    f"with a silhouette score of "
                    f"{cluster_result['silhouette_score']:.4f}."
                    if cluster_result[
                        "estimated_clusters"
                    ] is not None
                    else
                    cluster_result["reason"]
                ),

                (
                    f"The observed cluster structure "
                    f"is {cluster_result['cluster_structure'].lower()}."
                    if cluster_result[
                        "estimated_clusters"
                    ] is not None
                    else
                    "A valid cluster structure could "
                    "not be established."
                ),
            ],
        },

        # ----------------------------------------------------
        # 8. Local Density & Neighborhood Analysis
        # ----------------------------------------------------

        "density": {

            "title":
                "8. Local Density & Neighborhood Analysis",

            "result":
                density_result[
                    "local_density"
                ],

            "density_analysis":
                density_result,

            "inferences": [

                (
                    f"The mean nearest-neighbor "
                    f"distance is "
                    f"{density_result['mean_nearest_neighbor_distance']:.4f} "
                    f"with a density variation CV of "
                    f"{density_result['density_variability_cv']:.4f}."
                    if density_result[
                        "density_variability_cv"
                    ] is not None
                    else
                    "Nearest-neighbor density analysis "
                    "was unavailable."
                ),

                (
                    "The observed nearest-neighbor "
                    "distances show variation in local "
                    "neighborhood density."
                    if density_result[
                        "local_density"
                    ] == "Variable"
                    else
                    "The observed nearest-neighbor "
                    "distances are relatively uniform."
                    if density_result[
                        "local_density"
                    ] == "Relatively Uniform"
                    else
                    "Local neighborhood density "
                    "could not be determined."
                ),
            ],
        },

        # ----------------------------------------------------
        # 9. Temporal Structure Analysis
        # ----------------------------------------------------

        "temporal": {

            "title":
                "9. Temporal Structure Analysis",

            "result":
                temporal[
                    "temporal_structure"
                ],

            "temporal_structure":
                temporal,

            "inferences": [

                (
                    f"The selected temporal column is "
                    f"{temporal['temporal_column']} "
                    f"with "
                    f"{temporal['valid_timestamps']} "
                    f"valid timestamp(s)."
                    if temporal[
                        "temporal_column"
                    ]
                    else
                    "No date/time column was selected."
                ),

                (
                    f"Timestamps are "
                    f"{str(temporal['chronological_ordering']).lower()} "
                    f"chronologically ordered and interval "
                    f"regularity is "
                    f"{str(temporal['regular_intervals']).lower()}."
                    if temporal[
                        "temporal_column"
                    ]
                    else
                    "Temporal structure cannot be established "
                    "without a valid date/time column."
                ),
            ],
        },

        # ----------------------------------------------------
        # 10. Time-Series Pattern Analysis
        # ----------------------------------------------------

        "timeseries": {

            "title":
                "10. Time-Series Pattern Analysis",

            "result":
                time_series["result"],

            "pattern_analysis":
                time_series[
                    "pattern_analysis"
                ],

            "time_series_summary": {

                "temporal_column":
                    time_series[
                        "temporal_column"
                    ],

                "selected_signal":
                    time_series[
                        "selected_signal"
                    ],

                "lag":
                    time_series["lag"],

                "autocorrelation":
                    time_series[
                        "autocorrelation"
                    ],
            },

            "inferences": [

                (
                    f"The strongest lag-1 "
                    f"autocorrelation is "
                    f"{time_series['autocorrelation']:.4f} "
                    f"for {time_series['selected_signal']}."
                    if time_series[
                        "autocorrelation"
                    ] is not None
                    else
                    time_series["reason"]
                ),

                (
                    "This indicates the measured "
                    "degree of sequential dependence "
                    "between consecutive numerical "
                    "observations."
                    if time_series[
                        "autocorrelation"
                    ] is not None
                    else
                    "A valid temporal column and "
                    "numerical signal are required "
                    "for this analysis."
                ),
            ],
        },
    }

    # --------------------------------------------------------
    # Final Phase 3 response
    # --------------------------------------------------------

    return {

        "analysis_completed": True,

        "records": row_count,

        "features": feature_count,

        "selected_columns":
            selected_columns,

        "numeric_columns":
            numeric_columns,

        "categorical_columns":
            categorical_columns,

        "datetime_columns":
            datetime_columns,

        "sections":
            sections,
    }