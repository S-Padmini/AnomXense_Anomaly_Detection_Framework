from __future__ import annotations

from typing import Any

import base64
import io
import re

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .evaluation import evaluate_detection


class MultivariateDetector:
    """
    Multivariate statistical anomaly detection using Mahalanobis Distance.

    IMPORTANT:
    - Input must be the Phase 3 preprocessed dataframe.
    - No raw-data preprocessing is performed here.
    - All usable numerical features supplied by Phase 3 are considered.
    - Constant features are excluded from the Mahalanobis calculation.
    - Every record receives a Mahalanobis score.
    - A dynamically calculated statistical threshold is used to classify
      records as normal or anomalous.
    """

    METHOD = "Mahalanobis Distance"

    def __init__(
        self,
        dataframe: pd.DataFrame,
        threshold_method: str = "chi_square",
        threshold_quantile: float = 0.975,
    ):
        if dataframe is None:
            raise ValueError(
                "Preprocessed dataframe cannot be None."
            )

        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                "MultivariateDetector expects a pandas DataFrame."
            )

        if dataframe.empty:
            raise ValueError(
                "Preprocessed dataframe is empty."
            )

        self.dataframe = dataframe.copy()
        self.threshold_method = threshold_method
        self.threshold_quantile = threshold_quantile

        if not 0 < threshold_quantile < 1:
            raise ValueError(
                "threshold_quantile must be between 0 and 1."
            )

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if value is None:
            return None

        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass

        if isinstance(value, np.integer):
            return int(value)

        if isinstance(value, np.floating):
            value = float(value)

            if not np.isfinite(value):
                return None

            return value

        if isinstance(value, np.bool_):
            return bool(value)

        if isinstance(value, pd.Timestamp):
            return value.isoformat()

        return value

    def _build_numeric_matrix(
        self,
    ) -> tuple[np.ndarray, list[str]]:
        numeric_columns: list[str] = []
        converted_columns: list[pd.Series] = []

        for column in self.dataframe.columns:
            series = self.dataframe[column]

            if pd.api.types.is_numeric_dtype(series):
                numeric_columns.append(str(column))

                converted_columns.append(
                    pd.to_numeric(
                        series,
                        errors="coerce",
                    )
                )

                continue

            if pd.api.types.is_bool_dtype(series):
                numeric_columns.append(str(column))

                converted_columns.append(
                    series.astype(int)
                )

                continue

            converted = pd.to_numeric(
                series,
                errors="coerce",
            )

            if converted.notna().all():
                numeric_columns.append(str(column))
                converted_columns.append(converted)

        if not converted_columns:
            raise ValueError(
                "Mahalanobis Distance requires at least one numerical "
                "feature in the Phase 3 preprocessed dataframe."
            )

        matrix_df = pd.concat(
            converted_columns,
            axis=1,
        )

        matrix_df.columns = numeric_columns

        matrix_df = matrix_df.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        matrix_df = matrix_df.fillna(
            matrix_df.median(numeric_only=True)
        )

        matrix_df = matrix_df.fillna(0.0)

        matrix = matrix_df.to_numpy(
            dtype=float,
        )

        if not np.isfinite(matrix).all():
            matrix = np.nan_to_num(
                matrix,
                nan=0.0,
                posinf=0.0,
                neginf=0.0,
            )

        return matrix, numeric_columns

    @staticmethod
    def _remove_constant_columns(
        matrix: np.ndarray,
        columns: list[str],
    ) -> tuple[np.ndarray, list[str], list[str]]:
        if matrix.shape[1] == 0:
            raise ValueError(
                "No features are available for Mahalanobis calculation."
            )

        variances = np.var(
            matrix,
            axis=0,
        )

        keep_indices = [
            index
            for index, variance in enumerate(variances)
            if np.isfinite(variance)
            and variance > 1e-12
        ]

        removed_columns = [
            columns[index]
            for index in range(len(columns))
            if index not in keep_indices
        ]

        if not keep_indices:
            raise ValueError(
                "Mahalanobis Distance cannot be calculated because all "
                "selected features have zero variance."
            )

        reduced_matrix = matrix[:, keep_indices]

        used_columns = [
            columns[index]
            for index in keep_indices
        ]

        return (
            reduced_matrix,
            used_columns,
            removed_columns,
        )

    @staticmethod
    def _calculate_inverse_covariance(
        matrix: np.ndarray,
    ) -> np.ndarray:
        covariance = np.cov(
            matrix,
            rowvar=False,
        )

        if np.ndim(covariance) == 0:
            covariance = np.array(
                [[float(covariance)]],
                dtype=float,
            )

        covariance = np.atleast_2d(
            covariance.astype(float)
        )

        if not np.isfinite(covariance).all():
            raise ValueError(
                "Covariance matrix contains invalid numerical values."
            )

        inverse_covariance = np.linalg.pinv(
            covariance,
            hermitian=True,
        )

        if not np.isfinite(inverse_covariance).all():
            raise ValueError(
                "Unable to calculate a valid inverse covariance matrix."
            )

        return inverse_covariance

    @staticmethod
    def _calculate_scores(
        matrix: np.ndarray,
        mean_vector: np.ndarray,
        inverse_covariance: np.ndarray,
    ) -> np.ndarray:
        centered = matrix - mean_vector

        squared_distances = np.einsum(
            "ij,jk,ik->i",
            centered,
            inverse_covariance,
            centered,
        )

        squared_distances = np.maximum(
            squared_distances,
            0.0,
        )

        scores = np.sqrt(
            squared_distances
        )

        return scores.astype(float)

    @staticmethod
    def _calculate_feature_contributions(
        record_vector: np.ndarray,
        mean_vector: np.ndarray,
        inverse_covariance: np.ndarray,
        columns: list[str],
    ) -> list[dict[str, Any]]:
        """
        Decompose the squared Mahalanobis distance into feature terms.

        For:

            d = x - mu
            P = Sigma^-1

        Mahalanobis squared distance is:

            D^2 = d.T @ P @ d

        The j-th feature contribution is:

            C_j = d_j * (P @ d)_j

        Signed contributions sum to D^2.

        Absolute contributions are used for ranking and percentages.
        """

        centered = (
            np.asarray(
                record_vector,
                dtype=float,
            )
            - mean_vector
        )

        adjusted = (
            inverse_covariance
            @ centered
        )

        raw_terms = (
            centered
            * adjusted
        )

        magnitudes = np.abs(
            raw_terms
        )

        total_magnitude = float(
            np.sum(magnitudes)
        )

        contributions: list[dict[str, Any]] = []

        for index, column in enumerate(columns):
            raw = float(
                raw_terms[index]
            )

            magnitude = float(
                magnitudes[index]
            )

            percentage = (
                magnitude
                / total_magnitude
                * 100.0
                if total_magnitude > 1e-15
                else 0.0
            )

            if centered[index] > 0:
                direction = "Above mean"
            elif centered[index] < 0:
                direction = "Below mean"
            else:
                direction = "At mean"

            contributions.append(
                {
                    "feature_name": column,
                    "feature": column,
                    "actual_value": (
                        MultivariateDetector._json_safe(
                            record_vector[index]
                        )
                    ),
                    "mean_value": float(
                        mean_vector[index]
                    ),
                    "deviation": float(
                        centered[index]
                    ),
                    "covariance_adjusted_deviation": float(
                        adjusted[index]
                    ),
                    "contribution": raw,
                    "absolute_contribution": magnitude,
                    "contribution_percentage": round(
                        percentage,
                        2,
                    ),
                    "signed_contribution": raw,
                    "direction": direction,
                    "formula": (
                        "C_j = (x_j - mu_j) * "
                        "[Sigma^-1(x - mu)]_j"
                    ),
                    "reason": (
                        "Feature contribution is derived directly "
                        "from the covariance-adjusted Mahalanobis "
                        "quadratic form."
                    ),
                }
            )

        contributions.sort(
            key=lambda item: float(
                item["absolute_contribution"]
            ),
            reverse=True,
        )

        for rank, item in enumerate(
            contributions,
            start=1,
        ):
            item["rank"] = rank

        return contributions

    def _calculate_threshold(
        self,
        scores: np.ndarray,
        number_of_features: int,
    ) -> tuple[float, str]:
        if scores.size == 0:
            raise ValueError(
                "Cannot calculate a threshold without Mahalanobis scores."
            )

        if number_of_features <= 0:
            raise ValueError(
                "Number of features must be greater than zero."
            )

        if (
            self.threshold_method.lower()
            == "chi_square"
        ):
            try:
                from scipy.stats import chi2

                chi_square_limit = chi2.ppf(
                    self.threshold_quantile,
                    df=number_of_features,
                )

                if (
                    np.isfinite(
                        chi_square_limit
                    )
                    and chi_square_limit > 0
                ):
                    threshold = float(
                        np.sqrt(
                            chi_square_limit
                        )
                    )

                    return (
                        threshold,
                        (
                            f"Chi-square "
                            f"({self.threshold_quantile:.3f} "
                            f"quantile, "
                            f"df={number_of_features})"
                        ),
                    )

            except Exception:
                pass

        threshold = float(
            np.quantile(
                scores,
                self.threshold_quantile,
            )
        )

        return (
            threshold,
            (
                f"Empirical score quantile "
                f"({self.threshold_quantile:.3f})"
            ),
        )

    @staticmethod
    def _build_score_interpretation(
        score: float,
        threshold: float,
        status: str,
    ) -> str:
        score_text = f"{score:.6g}"
        threshold_text = f"{threshold:.6g}"

        if score > threshold:
            excess = score - threshold

            return (
                f"The Mahalanobis score ({score_text}) is above the "
                f"statistical threshold ({threshold_text}) by "
                f"{excess:.6g}, so this record is classified as an anomaly."
            )

        difference = threshold - score

        return (
            f"The Mahalanobis score ({score_text}) is at or below the "
            f"statistical threshold ({threshold_text}); it is "
            f"{difference:.6g} below the threshold, so this record is "
            f"classified as normal."
        )

    def detect(self) -> dict[str, Any]:
        matrix, original_columns = (
            self._build_numeric_matrix()
        )

        (
            matrix,
            used_columns,
            removed_constant_columns,
        ) = self._remove_constant_columns(
            matrix,
            original_columns,
        )

        if matrix.shape[0] < 2:
            raise ValueError(
                "Mahalanobis Distance requires at least two records."
            )

        mean_vector = np.mean(
            matrix,
            axis=0,
        )

        inverse_covariance = (
            self._calculate_inverse_covariance(
                matrix
            )
        )

        scores = self._calculate_scores(
            matrix=matrix,
            mean_vector=mean_vector,
            inverse_covariance=inverse_covariance,
        )

        threshold, threshold_description = (
            self._calculate_threshold(
                scores=scores,
                number_of_features=len(
                    used_columns
                ),
            )
        )

        record_results: list[dict[str, Any]] = []

        anomaly_count = 0
        normal_count = 0

        for position, score in enumerate(
            scores,
            start=1,
        ):
            score = float(score)

            is_anomaly = (
                score > threshold
            )

            status = (
                "Anomaly"
                if is_anomaly
                else "Normal"
            )

            if is_anomaly:
                anomaly_count += 1
            else:
                normal_count += 1

            dataframe_index = (
                self.dataframe.index[
                    position - 1
                ]
            )

            feature_values: dict[
                str,
                Any,
            ] = {}

            for column_name in used_columns:
                value = (
                    self.dataframe.iloc[
                        position - 1
                    ][column_name]
                )

                feature_values[
                    column_name
                ] = self._json_safe(
                    value
                )

            feature_contributions = (
                self._calculate_feature_contributions(
                    record_vector=matrix[
                        position - 1
                    ],
                    mean_vector=mean_vector,
                    inverse_covariance=(
                        inverse_covariance
                    ),
                    columns=used_columns,
                )
            )

            interpretation = (
                self._build_score_interpretation(
                    score=score,
                    threshold=threshold,
                    status=status,
                )
            )

            record_results.append(
                {
                    "record_number": position,
                    "dataframe_index": (
                        self._json_safe(
                            dataframe_index
                        )
                    ),
                    "mah_distance": score,
                    "mahalanobis_score": score,
                    "threshold": threshold,
                    "status": status,
                    "is_anomaly": is_anomaly,
                    "feature_values": feature_values,
                    "top_contributors": (
                        feature_contributions[:3]
                    ),
                    "feature_contributions": (
                        feature_contributions
                    ),
                    "interpretation": interpretation,
                }
            )

        total_records = len(
            record_results
        )

        anomaly_percentage = (
            (
                anomaly_count
                / total_records
            )
            * 100
            if total_records > 0
            else 0.0
        )

        return {
            "variability": "Multivariate",
            "method_used": self.METHOD,
            "columns_involved": used_columns,
            "all_preprocessed_columns": (
                original_columns
            ),
            "constant_columns_excluded": (
                removed_constant_columns
            ),
            "total_columns_involved": len(
                used_columns
            ),
            "total_records": total_records,
            "anomaly_records": anomaly_count,
            "normal_records": normal_count,
            "anomaly_percentage": round(
                anomaly_percentage,
                2,
            ),
            "threshold": threshold,
            "mahalanobis_threshold": threshold,
            "threshold_method": threshold_description,
            "threshold_quantile": (
                self.threshold_quantile
            ),
            "records": record_results,
        }


# ======================================================================
# Controlled multivariate evaluation
# ======================================================================


def _build_evaluation_matrix(
    dataframe: pd.DataFrame,
) -> tuple[
    np.ndarray,
    list[str],
]:
    """
    Build the same numerical feature matrix used by the Mahalanobis
    detector.

    This helper intentionally follows the detector's own feature
    preparation rules so the evaluation is performed in the same
    feature space as the actual detector.
    """

    detector = MultivariateDetector(
        dataframe
    )

    matrix, columns = (
        detector._build_numeric_matrix()
    )

    (
        matrix,
        columns,
        _,
    ) = detector._remove_constant_columns(
        matrix,
        columns,
    )

    return matrix, columns


def _calculate_robust_feature_scales(
    matrix: np.ndarray,
) -> np.ndarray:
    """
    Calculate a robust scale for every feature.

    For each feature:

        MAD = median(|x - median(x)|)

    The scale used for perturbation is:

        max(
            MAD * 1.4826,
            IQR / 1.349,
            Standard Deviation,
            1% of feature range
        )

    This prevents the artificial perturbation from being tied directly
    to the Mahalanobis threshold.
    """

    number_of_features = (
        matrix.shape[1]
    )

    scales = np.zeros(
        number_of_features,
        dtype=float,
    )

    for feature_index in range(
        number_of_features
    ):
        values = matrix[
            :,
            feature_index,
        ].astype(float)

        median = float(
            np.median(values)
        )

        q1 = float(
            np.quantile(
                values,
                0.25,
            )
        )

        q3 = float(
            np.quantile(
                values,
                0.75,
            )
        )

        iqr = float(
            q3 - q1
        )

        mad = float(
            np.median(
                np.abs(
                    values
                    - median
                )
            )
        )

        standard_deviation = float(
            np.std(
                values,
                ddof=0,
            )
        )

        feature_range = float(
            np.max(values)
            - np.min(values)
        )

        if (
            not np.isfinite(
                feature_range
            )
            or feature_range <= 0
        ):
            feature_range = max(
                abs(
                    float(
                        np.max(values)
                    )
                ),
                abs(
                    float(
                        np.min(values)
                    )
                ),
                1.0,
            )

        scale = max(
            mad * 1.4826,
            iqr / 1.349,
            standard_deviation,
            feature_range * 0.01,
            1e-9,
        )

        if not np.isfinite(scale):
            scale = max(
                feature_range * 0.01,
                1e-9,
            )

        scales[
            feature_index
        ] = float(scale)

    return scales


def _inject_multivariate_perturbations(
    dataframe: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    list[int],
    dict[str, Any],
]:
    """
    Create a controlled multivariate evaluation dataset.

    Approximately 5% of records are selected.

    Each selected record is perturbed across multiple numerical
    dimensions using robust feature scales.

    The perturbation is NOT created by directly calculating a
    Mahalanobis threshold and placing the point beyond that threshold.

    Ground-truth labels are stored separately and are never supplied
    to the Mahalanobis detector.

    IMPORTANT:
    The evaluation dataframe is converted to float64 for all numerical
    columns before perturbation. This prevents pandas from rejecting
    floating-point injected values when the original Phase 3 column
    was stored as int64.
    """

    # --------------------------------------------------------------
    # Create a completely independent evaluation copy.
    # --------------------------------------------------------------

    evaluation_df = dataframe.copy(
        deep=True
    )

    # --------------------------------------------------------------
    # Build the same numerical feature space used by the detector.
    # --------------------------------------------------------------

    matrix, used_columns = (
        _build_evaluation_matrix(
            evaluation_df
        )
    )

    if matrix.shape[0] < 4:
        raise ValueError(
            "Multivariate accuracy evaluation requires at least "
            "four records."
        )

    if matrix.shape[1] < 1:
        raise ValueError(
            "Multivariate accuracy evaluation requires at least "
            "one varying numerical feature."
        )

    # --------------------------------------------------------------
    # IMPORTANT FIX:
    #
    # Convert every feature participating in the evaluation to
    # float64 before assigning the statistically generated
    # perturbations.
    #
    # This fixes:
    #
    # Invalid value '...' for dtype 'int64'
    #
    # Only the temporary evaluation dataframe is changed.
    # The original Phase 3 dataframe is never modified.
    # --------------------------------------------------------------

    for column_name in used_columns:
        evaluation_df[column_name] = pd.to_numeric(
            evaluation_df[column_name],
            errors="coerce",
        ).astype(
            "float64"
        )

    # Recalculate the evaluation matrix after dtype conversion.
    #
    # This keeps the matrix and dataframe perfectly aligned.
    matrix, used_columns = (
        _build_evaluation_matrix(
            evaluation_df
        )
    )

    # --------------------------------------------------------------
    # Calculate robust scale independently for each feature.
    # --------------------------------------------------------------

    feature_scales = (
        _calculate_robust_feature_scales(
            matrix
        )
    )

    # --------------------------------------------------------------
    # Select approximately 5% of records.
    # --------------------------------------------------------------

    injection_count = max(
        1,
        int(
            round(
                matrix.shape[0] * 0.05
            )
        ),
    )

    injection_count = min(
        injection_count,
        matrix.shape[0],
    )

    random_generator = np.random.default_rng(
        42
    )

    selected_positions = (
        random_generator.choice(
            matrix.shape[0],
            size=injection_count,
            replace=False,
        )
        .astype(int)
        .tolist()
    )

    selected_positions.sort()

    # --------------------------------------------------------------
    # Ground truth:
    #
    # 0 = normal
    # 1 = injected anomaly
    # --------------------------------------------------------------

    ground_truth_labels = [
        0
        for _ in range(
            matrix.shape[0]
        )
    ]

    # --------------------------------------------------------------
    # Generate a multivariate perturbation.
    #
    # The direction changes across dimensions so that the artificial
    # anomalies do not simply modify one column.
    #
    # The perturbation magnitude is based on robust feature scales.
    # --------------------------------------------------------------

    perturbation_multiplier = 2.75

    perturbation_details: list[
        dict[str, Any]
    ] = []

    for anomaly_number, row_position in enumerate(
        selected_positions
    ):
        original_vector = (
            matrix[
                row_position
            ].copy()
        )

        number_of_features = (
            len(used_columns)
        )

        # Create a deterministic direction vector.

        direction = np.ones(
            number_of_features,
            dtype=float,
        )

        for feature_index in range(
            number_of_features
        ):
            if (
                (
                    feature_index
                    + anomaly_number
                )
                % 2
                == 1
            ):
                direction[
                    feature_index
                ] = -1.0

        # Normalize the direction so the perturbation has a controlled
        # multivariate magnitude.

        direction_norm = float(
            np.linalg.norm(
                direction
            )
        )

        if (
            not np.isfinite(
                direction_norm
            )
            or direction_norm <= 0
        ):
            direction_norm = 1.0

        normalized_direction = (
            direction
            / direction_norm
        )

        # Each dimension uses its own robust scale.

        perturbation_vector = (
            normalized_direction
            * feature_scales
            * perturbation_multiplier
        )

        injected_vector = (
            original_vector
            + perturbation_vector
        )

        injected_vector = np.nan_to_num(
            injected_vector,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        # ----------------------------------------------------------
        # Write the perturbed values into the temporary dataframe.
        #
        # All participating columns are already float64.
        # ----------------------------------------------------------

        for feature_index, column_name in enumerate(
            used_columns
        ):
            evaluation_df.iloc[
                row_position,
                evaluation_df.columns.get_loc(
                    column_name
                ),
            ] = float(
                injected_vector[
                    feature_index
                ]
            )

        ground_truth_labels[
            row_position
        ] = 1

        perturbation_details.append(
            {
                "row_position": int(
                    row_position
                ),
                "original_values": {
                    column_name: float(
                        original_vector[
                            feature_index
                        ]
                    )
                    for feature_index, column_name
                    in enumerate(
                        used_columns
                    )
                },
                "injected_values": {
                    column_name: float(
                        injected_vector[
                            feature_index
                        ]
                    )
                    for feature_index, column_name
                    in enumerate(
                        used_columns
                    )
                },
                "perturbed_columns": list(
                    used_columns
                ),
                "perturbation_multiplier": (
                    perturbation_multiplier
                ),
            }
        )

    metadata = {
        "evaluation_columns": list(
            used_columns
        ),
        "injected_anomaly_count": int(
            injection_count
        ),
        "injected_anomaly_percentage": round(
            (
                injection_count
                / matrix.shape[0]
            )
            * 100,
            2,
        ),
        "random_seed": 42,
        "perturbation_multiplier": (
            perturbation_multiplier
        ),
        "feature_robust_scales": {
            column_name: float(
                feature_scales[
                    feature_index
                ]
            )
            for feature_index, column_name
            in enumerate(
                used_columns
            )
        },
        "injection_rule": (
            "Known anomalies were created by statistically "
            "perturbing selected records across multiple numerical "
            "features using feature-wise robust scales derived from "
            "MAD, IQR, standard deviation and feature range. "
            "The standard Mahalanobis detector was then applied "
            "independently without receiving the ground-truth labels."
        ),
        "perturbations": perturbation_details,
    }

    return (
        evaluation_df,
        ground_truth_labels,
        metadata,
    )


def _evaluate_multivariate_accuracy(
    preprocessed_df: pd.DataFrame,
) -> tuple[
    float,
    dict[str, Any],
]:
    """
    Evaluate Mahalanobis detection using controlled multivariate
    statistical perturbation.

    The detector does not receive the injected anomaly labels.
    """

    (
        evaluation_df,
        actual_labels,
        evaluation_metadata,
    ) = _inject_multivariate_perturbations(
        preprocessed_df
    )

    # --------------------------------------------------------------
    # Run the ordinary Mahalanobis detector independently.
    # --------------------------------------------------------------

    evaluation_detector = MultivariateDetector(
        evaluation_df
    )

    evaluation_result = (
        evaluation_detector.detect()
    )

    predicted_labels = [
        1
        if record.get(
            "is_anomaly"
        )
        else 0
        for record in (
            evaluation_result.get(
                "records",
                []
            )
        )
    ]

    # --------------------------------------------------------------
    # Compare known ground truth with detector predictions.
    # --------------------------------------------------------------

    evaluation = evaluate_detection(
        actual_labels=actual_labels,
        predicted_labels=predicted_labels,
    )

    evaluation.update(
        {
            "evaluation_columns": (
                evaluation_metadata[
                    "evaluation_columns"
                ]
            ),
            "injected_anomaly_count": (
                evaluation_metadata[
                    "injected_anomaly_count"
                ]
            ),
            "injected_anomaly_percentage": (
                evaluation_metadata[
                    "injected_anomaly_percentage"
                ]
            ),
            "random_seed": (
                evaluation_metadata[
                    "random_seed"
                ]
            ),
            "perturbation_multiplier": (
                evaluation_metadata[
                    "perturbation_multiplier"
                ]
            ),
            "feature_robust_scales": (
                evaluation_metadata[
                    "feature_robust_scales"
                ]
            ),
            "evaluation_rule": (
                evaluation_metadata[
                    "injection_rule"
                ]
            ),
        }
    )

    return (
        float(
            evaluation["accuracy"]
        ),
        evaluation,
    )


# ======================================================================
# PDF helpers
# ======================================================================


def _report_value(
    value: Any,
) -> str:
    if value is None:
        return "—"

    if isinstance(
        value,
        float,
    ):
        return f"{value:.6g}"

    return str(value)


def _safe_report_name(
    dataset_name: str,
) -> str:
    stem = re.sub(
        r"[^A-Za-z0-9.\_-]+",
        "_",
        str(
            dataset_name
            or "ANOMALY_Dataset"
        ),
    )

    stem = re.sub(
        r"_+",
        "_",
        stem,
    ).strip(
        "._"
    ) or "ANOMALY_Dataset"

    return (
        f"{stem}_Multivariate_Anomaly_Report.pdf"
    )


def _build_multivariate_pdf(
    dataset_name: str,
    preprocessed_df: pd.DataFrame,
    result: dict[str, Any],
) -> bytes:
    """
    Build the multivariate A4 PDF report.

    The report keeps the existing anomaly-record section and provides
    the Top 3 Feature Contributions table.
    """

    buffer = io.BytesIO()

    page = landscape(A4)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=page,
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Multivariate Anomaly Detection Report",
        author="ANOMALY",
    )

    styles = getSampleStyleSheet()

    title = ParagraphStyle(
        "MVTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        textColor=colors.HexColor("#173f8a"),
        spaceAfter=4 * mm,
    )

    meta = ParagraphStyle(
        "MVMeta",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4f5f78"),
        spaceAfter=1.5 * mm,
    )

    section = ParagraphStyle(
        "MVSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#102f68"),
        spaceBefore=3 * mm,
        spaceAfter=2 * mm,
    )

    cell = ParagraphStyle(
        "MVCell",
        parent=styles["BodyText"],
        fontSize=6.4,
        leading=8,
        textColor=colors.HexColor("#172033"),
    )

    center = ParagraphStyle(
        "MVCenter",
        parent=cell,
        alignment=1,
    )

    header = ParagraphStyle(
        "MVHeader",
        parent=cell,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=1,
    )

    records = result.get(
        "records",
        [],
    )

    anomalies = [
        record
        for record in records
        if record.get("is_anomaly")
        or str(
            record.get(
                "status",
                "",
            )
        ).lower()
        == "anomaly"
    ]

    columns = list(
        result.get(
            "columns_involved"
        )
        or []
    )

    threshold = result.get(
        "threshold"
    )

    story = [
        Paragraph(
            "Multivariate Anomaly Detection Report",
            title,
        ),
        Paragraph(
            f"<b>Dataset:</b> "
            f"{_report_value(dataset_name)}",
            meta,
        ),
        Paragraph(
            f"<b>No. of records:</b> "
            f"{len(preprocessed_df)}",
            meta,
        ),
        Paragraph(
            f"<b>No. of attributes:</b> "
            f"{len(preprocessed_df.columns)}",
            meta,
        ),
        Paragraph(
            f"<b>No. of anomaly:</b> "
            f"{len(anomalies)}",
            meta,
        ),
        Paragraph(
            f"<b>%:</b> "
            f"{_report_value(result.get('anomaly_percentage'))}%",
            meta,
        ),
        Paragraph(
            "<b>Method used:</b> "
            "Mahalanobis Distance",
            meta,
        ),
        Paragraph(
            f"<b>Threshold:</b> "
            f"{_report_value(threshold)}",
            meta,
        ),
        Spacer(
            1,
            3 * mm,
        ),
        Paragraph(
            "Detected Anomaly Records",
            section,
        ),
    ]

    if not anomalies:
        story.append(
            Paragraph(
                "No anomaly records were detected.",
                cell,
            )
        )

    else:
        headers = [
            "Record",
            *columns,
            "Threshold",
            "Mahalanobis Score",
            "Top 3 Contributing Columns",
        ]

        data = [
            [
                Paragraph(
                    header_text,
                    header,
                )
                for header_text in headers
            ]
        ]

        for record in anomalies:
            values = (
                record.get(
                    "feature_values"
                )
                or {}
            )

            row = [
                Paragraph(
                    _report_value(
                        record.get(
                            "record_number"
                        )
                    ),
                    center,
                )
            ]

            row += [
                Paragraph(
                    _report_value(
                        values.get(
                            column
                        )
                    ),
                    cell,
                )
                for column in columns
            ]

            row += [
                Paragraph(
                    _report_value(
                        record.get(
                            "threshold",
                            threshold,
                        )
                    ),
                    center,
                ),
                Paragraph(
                    _report_value(
                        record.get(
                            "mah_distance",
                            record.get(
                                "mahalanobis_score"
                            ),
                        )
                    ),
                    center,
                ),
            ]

            contributors = (
                record.get(
                    "top_contributors"
                )
                or record.get(
                    "feature_contributions"
                )
                or []
            )

            top_three_text = "<br/>".join(
                f"{_report_value(item.get('feature_name') or item.get('feature'))}: "
                f"{_report_value(item.get('contribution_percentage'))}%"
                for item in contributors[:3]
            ) or "—"

            row.append(
                Paragraph(
                    top_three_text,
                    cell,
                )
            )

            data.append(row)

        usable_width = (
            page[0]
            - 20 * mm
        )

        fixed_width = (
            15 * mm
            + 25 * mm
            + 32 * mm
            + 55 * mm
        )

        feature_width = max(
            18 * mm,
            (
                usable_width
                - fixed_width
            )
            / max(
                len(columns),
                1,
            ),
        )

        widths = (
            [15 * mm]
            + [
                feature_width
            ]
            * len(columns)
            + [
                25 * mm,
                32 * mm,
                55 * mm,
            ]
        )

        table = Table(
            data,
            colWidths=widths,
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#173f8a"
                        ),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.HexColor(
                            "#c9d3e5"
                        ),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                ]
            )
        )

        story.append(
            table
        )

    def footer(
        canvas,
        doc,
    ):
        canvas.saveState()

        canvas.setFont(
            "Helvetica",
            8,
        )

        canvas.setFillColor(
            colors.HexColor(
                "#68758a"
            )
        )

        canvas.drawRightString(
            page[0] - 10 * mm,
            6 * mm,
            f"Page {doc.page}",
        )

        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer,
    )

    return buffer.getvalue()


# ======================================================================
# Main detection function
# ======================================================================


def detect_multivariate(
    preprocessed_df: pd.DataFrame,
    actual_labels: list[int] | None = None,
) -> dict[str, Any]:
    """
    Run Mahalanobis Distance anomaly detection.

    Normal detection is performed on the actual Phase 3 preprocessed
    dataframe.

    If actual_labels are supplied, they are used for compatibility
    with existing callers.

    Otherwise, the function automatically performs a controlled
    statistical evaluation using a separate evaluation copy.

    The original Phase 3 dataframe is never modified.
    """

    # --------------------------------------------------------------
    # Normal detection
    # --------------------------------------------------------------

    detector = MultivariateDetector(
        preprocessed_df
    )

    result = detector.detect()

    accuracy: float | None = None

    evaluation: dict[
        str,
        Any,
    ] | None = None

    # --------------------------------------------------------------
    # Explicit ground-truth labels, if supplied by an existing caller
    # --------------------------------------------------------------

    if actual_labels is not None:

        predicted_labels = [
            1
            if record.get(
                "is_anomaly"
            )
            else 0
            for record in result.get(
                "records",
                [],
            )
        ]

        evaluation = evaluate_detection(
            actual_labels=actual_labels,
            predicted_labels=predicted_labels,
        )

        accuracy = float(
            evaluation["accuracy"]
        )

    # --------------------------------------------------------------
    # Automatic controlled evaluation
    # --------------------------------------------------------------

    else:

        (
            accuracy,
            evaluation,
        ) = _evaluate_multivariate_accuracy(
            preprocessed_df
        )

    # --------------------------------------------------------------
    # PDF
    # --------------------------------------------------------------

    dataset_name = (
        "ANOMALY Dataset"
    )

    pdf_bytes = (
        _build_multivariate_pdf(
            dataset_name,
            preprocessed_df,
            result,
        )
    )

    result["dataset_name"] = (
        dataset_name
    )

    result["accuracy"] = (
        accuracy
    )

    result["evaluation"] = (
        evaluation
    )

    result["pdf_base64"] = (
        base64.b64encode(
            pdf_bytes
        ).decode(
            "ascii"
        )
    )

    result["pdf_filename"] = (
        _safe_report_name(
            dataset_name
        )
    )

    return result