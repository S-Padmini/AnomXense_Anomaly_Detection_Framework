from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# Optional SHAP support.
#
# SHAP is used whenever it can successfully explain the Mahalanobis
# squared-distance function.
#
# IMPORTANT:
# SHAP is NEVER allowed to break the explanation endpoint.
#
# If SHAP is unavailable or fails, the exact mathematical
# Mahalanobis contribution decomposition is always used.
# ------------------------------------------------------------------
try:
    import shap

    SHAP_AVAILABLE = True
except Exception:
    shap = None
    SHAP_AVAILABLE = False


class MahalanobisExplainability:
    """
    Explain an individual Mahalanobis anomaly score.

    Two complementary explanation methods are supported:

    1. Exact Mahalanobis feature contribution

           D² = dᵀ Σ⁻¹ d

       where:

           d = x - μ

       and:

           C_j = d_j * [Σ⁻¹d]_j

       The signed feature contributions reconstruct D².

    2. SHAP attribution

       SHAP is applied to the same Mahalanobis squared-distance
       function.

    SHAP is used whenever possible, but the exact Mahalanobis
    decomposition is always available as the guaranteed fallback.

    IMPORTANT:
    This class does NOT perform anomaly detection.

    The actual Mahalanobis score supplied by multivariate.py is
    preserved and returned unchanged.
    """

    MAX_FEATURES = 3

    def __init__(
        self,
        dataframe: pd.DataFrame,
        used_columns: list[str],
    ):
        if dataframe is None:
            raise ValueError(
                "Preprocessed dataframe cannot be None."
            )

        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                "Expected a pandas DataFrame."
            )

        if dataframe.empty:
            raise ValueError(
                "Preprocessed dataframe is empty."
            )

        if not used_columns:
            raise ValueError(
                "At least one feature is required for explainability."
            )

        missing_columns = [
            column
            for column in used_columns
            if column not in dataframe.columns
        ]

        if missing_columns:
            raise ValueError(
                "The following explanation columns are missing from "
                f"the Phase 3 preprocessed dataframe: {missing_columns}"
            )

        self.dataframe = dataframe.copy()
        self.used_columns = list(used_columns)

        # --------------------------------------------------------------
        # Cached numerical calculation state.
        # --------------------------------------------------------------
        self._matrix: np.ndarray | None = None
        self._active_matrix: np.ndarray | None = None

        self._active_columns: list[str] | None = None
        self._excluded_columns: list[str] = []

        self._mean_vector: np.ndarray | None = None

        # IMPORTANT:
        # This is intentionally named differently from the
        # _inverse_covariance() method below.
        #
        # Previously both used the same name:
        #
        # self._inverse_covariance = ...
        # def _inverse_covariance(...):
        #
        # The instance attribute shadowed the method and caused:
        #
        # TypeError: 'NoneType' object is not callable
        #
        self._inverse_covariance_matrix: np.ndarray | None = None

        # --------------------------------------------------------------
        # SHAP cache.
        # --------------------------------------------------------------
        self._shap_explainer: Any | None = None
        self._shap_background: np.ndarray | None = None

        self._shap_values_cache: dict[int, np.ndarray] = {}
        self._shap_base_values_cache: dict[int, float] = {}

    # ==================================================================
    # NUMERICAL REPRESENTATION
    # ==================================================================

    def _build_matrix(self) -> np.ndarray:
        """
        Convert the Phase 3 preprocessed selected columns into a
        numerical matrix.

        Boolean columns are converted to 0/1.

        Non-numeric values are coerced to NaN and then replaced using
        the column median, followed by 0 where a median is unavailable.
        """

        converted: list[pd.Series] = []

        for column in self.used_columns:
            series = self.dataframe[column]

            if pd.api.types.is_bool_dtype(series):
                converted.append(
                    series.astype(int)
                )
                continue

            numeric = pd.to_numeric(
                series,
                errors="coerce",
            )

            converted.append(
                numeric
            )

        matrix_df = pd.concat(
            converted,
            axis=1,
        )

        matrix_df.columns = self.used_columns

        matrix_df = matrix_df.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        matrix_df = matrix_df.fillna(
            matrix_df.median(numeric_only=True)
        )

        matrix_df = matrix_df.fillna(
            0.0
        )

        matrix = matrix_df.to_numpy(
            dtype=float
        )

        return np.nan_to_num(
            matrix,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

    # ==================================================================
    # ACTIVE FEATURE PREPARATION
    # ==================================================================

    def _prepare_numeric_matrix(
        self,
    ) -> tuple[np.ndarray, list[str], list[str]]:
        """
        Prepare the matrix used for covariance calculations.

        Constant features cannot contribute to Mahalanobis distance
        because their deviation is always zero.

        They are therefore excluded from the covariance matrix but
        retained in the public explanation output with zero contribution.
        """

        matrix = self._build_matrix()

        if matrix.ndim != 2:
            raise ValueError(
                "Unable to create a valid numerical feature matrix."
            )

        if matrix.shape[1] == 0:
            raise ValueError(
                "No numerical features are available for explainability."
            )

        variances = np.var(
            matrix,
            axis=0,
        )

        active_indices = [
            index
            for index, variance in enumerate(variances)
            if np.isfinite(variance)
            and variance > 1e-15
        ]

        excluded_indices = [
            index
            for index in range(matrix.shape[1])
            if index not in active_indices
        ]

        if not active_indices:
            raise ValueError(
                "All selected features are constant. "
                "Mahalanobis explainability cannot be calculated."
            )

        active_matrix = matrix[
            :,
            active_indices,
        ]

        active_columns = [
            self.used_columns[index]
            for index in active_indices
        ]

        excluded_columns = [
            self.used_columns[index]
            for index in excluded_indices
        ]

        return (
            active_matrix,
            active_columns,
            excluded_columns,
        )

    # ==================================================================
    # COVARIANCE MATRIX
    # ==================================================================

    @staticmethod
    def _inverse_covariance(
        matrix: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate a numerically stable pseudo-inverse covariance matrix.

        Pseudo-inverse is intentionally used because anomaly datasets
        can contain:

        - highly correlated features
        - redundant features
        - more features than observations
        """

        matrix = np.asarray(
            matrix,
            dtype=float,
        )

        if matrix.ndim != 2:
            raise ValueError(
                "Covariance input must be a two-dimensional matrix."
            )

        feature_count = matrix.shape[1]

        # --------------------------------------------------------------
        # One-feature case.
        # --------------------------------------------------------------
        if feature_count == 1:
            variance = float(
                np.var(
                    matrix[:, 0],
                    ddof=1,
                )
            )

            if not np.isfinite(variance) or variance <= 1e-15:
                variance = float(
                    np.var(
                        matrix[:, 0]
                    )
                )

            if not np.isfinite(variance) or variance <= 1e-15:
                variance = 1.0

            return np.array(
                [[1.0 / variance]],
                dtype=float,
            )

        # --------------------------------------------------------------
        # Standard covariance calculation.
        # --------------------------------------------------------------
        covariance = np.cov(
            matrix,
            rowvar=False,
        )

        covariance = np.atleast_2d(
            np.asarray(
                covariance,
                dtype=float,
            )
        )

        covariance = np.nan_to_num(
            covariance,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        # Numerical symmetry.
        covariance = (
            covariance
            + covariance.T
        ) / 2.0

        inverse = np.linalg.pinv(
            covariance,
            hermitian=True,
        )

        inverse = np.nan_to_num(
            inverse,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        return inverse

    # ==================================================================
    # PREPARE CALCULATION STATE
    # ==================================================================

    def _ensure_calculation_state(self) -> None:
        """
        Prepare and cache:

        - original numerical matrix
        - active numerical matrix
        - active columns
        - excluded constant columns
        - mean vector
        - inverse covariance matrix
        """

        if (
            self._matrix is not None
            and self._active_matrix is not None
            and self._mean_vector is not None
            and self._inverse_covariance_matrix is not None
            and self._active_columns is not None
        ):
            return

        matrix = self._build_matrix()

        (
            active_matrix,
            active_columns,
            excluded_columns,
        ) = self._prepare_numeric_matrix()

        mean_vector = np.mean(
            active_matrix,
            axis=0,
        )

        # IMPORTANT:
        # Call the method _inverse_covariance().
        # The cached result is stored in the separately named
        # _inverse_covariance_matrix attribute.
        inverse_covariance = self._inverse_covariance(
            active_matrix
        )

        self._matrix = matrix
        self._active_matrix = active_matrix
        self._active_columns = active_columns
        self._excluded_columns = excluded_columns
        self._mean_vector = mean_vector
        self._inverse_covariance_matrix = inverse_covariance

    # ==================================================================
    # MAHALANOBIS SQUARED DISTANCE
    # ==================================================================

    def _mahalanobis_squared_batch(
        self,
        samples: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate D² for one or more active-feature vectors.

            D² = dᵀ Σ⁻¹ d

        This is the exact function that SHAP explains.
        """

        self._ensure_calculation_state()

        if (
            self._mean_vector is None
            or self._inverse_covariance_matrix is None
        ):
            raise RuntimeError(
                "Mahalanobis calculation state was not initialized."
            )

        samples = np.asarray(
            samples,
            dtype=float,
        )

        if samples.ndim == 1:
            samples = samples.reshape(
                1,
                -1,
            )

        if samples.shape[1] != len(
            self._mean_vector
        ):
            raise ValueError(
                "SHAP sample feature count does not match "
                "the active Mahalanobis feature count."
            )

        centered = (
            samples
            - self._mean_vector
        )

        weighted = (
            centered
            @ self._inverse_covariance_matrix
        )

        distances = np.sum(
            weighted * centered,
            axis=1,
        )

        distances = np.nan_to_num(
            distances,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        # D² cannot be negative mathematically.
        return np.maximum(
            distances,
            0.0,
        )

    # ==================================================================
    # EXACT FEATURE CONTRIBUTIONS
    # ==================================================================

    @staticmethod
    def _calculate_feature_contributions(
        record_vector: np.ndarray,
        mean_vector: np.ndarray,
        inverse_covariance: np.ndarray,
    ) -> np.ndarray:
        """
        Exact decomposition of the Mahalanobis squared distance.

            d = x - μ

            a = Σ⁻¹d

            C_j = d_j * a_j

        Therefore:

            D² = Σ C_j

        The signed contributions reconstruct D² up to numerical
        precision.
        """

        record_vector = np.asarray(
            record_vector,
            dtype=float,
        )

        mean_vector = np.asarray(
            mean_vector,
            dtype=float,
        )

        centered = (
            record_vector
            - mean_vector
        )

        adjusted = (
            inverse_covariance
            @ centered
        )

        contributions = (
            centered
            * adjusted
        )

        return np.nan_to_num(
            np.asarray(
                contributions,
                dtype=float,
            ),
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

    # ==================================================================
    # CONTRIBUTION PERCENTAGE
    # ==================================================================

    @staticmethod
    def _contribution_percentage(
        absolute_contributions: np.ndarray,
    ) -> np.ndarray:
        """
        Convert absolute feature contribution magnitudes into
        percentages.

            Importance_j =
                |C_j| / Σ|C_k| × 100
        """

        absolute_contributions = np.asarray(
            absolute_contributions,
            dtype=float,
        )

        total = float(
            np.sum(
                absolute_contributions
            )
        )

        if (
            not np.isfinite(total)
            or total <= 1e-12
        ):
            return np.zeros_like(
                absolute_contributions,
                dtype=float,
            )

        return (
            absolute_contributions
            / total
        ) * 100.0

    # ==================================================================
    # SHAP EXPLAINER CREATION
    # ==================================================================

    def _build_shap_explainer(self) -> Any | None:
        """
        Create and cache a SHAP PermutationExplainer.

        SHAP is only responsible for attribution.

        If SHAP cannot be initialized, None is returned and the caller
        automatically uses the exact Mahalanobis decomposition.
        """

        if not SHAP_AVAILABLE or shap is None:
            return None

        self._ensure_calculation_state()

        if (
            self._active_matrix is None
            or self._active_matrix.shape[1] == 0
        ):
            return None

        if self._shap_explainer is not None:
            return self._shap_explainer

        try:
            background = self._active_matrix

            # ----------------------------------------------------------
            # Limit background size for performance.
            #
            # This is especially important for datasets with many
            # records and 30+ features.
            # ----------------------------------------------------------
            max_background = 100

            if len(background) > max_background:
                indices = np.linspace(
                    0,
                    len(background) - 1,
                    max_background,
                    dtype=int,
                )

                background = background[
                    indices
                ]

            self._shap_background = np.asarray(
                background,
                dtype=float,
            )

            def prediction_function(
                samples: np.ndarray,
            ) -> np.ndarray:
                return self._mahalanobis_squared_batch(
                    np.asarray(
                        samples,
                        dtype=float,
                    )
                )

            # ----------------------------------------------------------
            # Use the explicit PermutationExplainer.
            #
            # This is preferable here because Mahalanobis distance is
            # not a trained tree/linear/neural model.
            # ----------------------------------------------------------
            self._shap_explainer = (
                shap.PermutationExplainer(
                    prediction_function,
                    self._shap_background,
                )
            )

            return self._shap_explainer

        except Exception:
            self._shap_explainer = None
            return None

    # ==================================================================
    # SHAP VALUES
    # ==================================================================

    def _calculate_shap_values(
        self,
        record_vector: np.ndarray,
        record_number: int,
    ) -> tuple[np.ndarray | None, float | None, str, str | None]:
        """
        Calculate SHAP attribution for one record.

        Returns:

            shap_values
            base_value
            method
            error_message

        method:

            "shap"
            "exact_fallback"
        """

        # --------------------------------------------------------------
        # Cached explanation.
        # --------------------------------------------------------------
        if record_number in self._shap_values_cache:
            return (
                self._shap_values_cache[
                    record_number
                ],
                self._shap_base_values_cache.get(
                    record_number
                ),
                "shap",
                None,
            )

        if not SHAP_AVAILABLE or shap is None:
            return (
                None,
                None,
                "exact_fallback",
                "SHAP is not installed.",
            )

        try:
            self._ensure_calculation_state()

            explainer = (
                self._build_shap_explainer()
            )

            if explainer is None:
                return (
                    None,
                    None,
                    "exact_fallback",
                    "SHAP explainer could not be initialized.",
                )

            active_record = np.asarray(
                record_vector,
                dtype=float,
            ).reshape(
                1,
                -1,
            )

            feature_count = active_record.shape[1]

            # ----------------------------------------------------------
            # Permutation SHAP requires at least 2*M + 1 evaluations.
            #
            # Keep the explanation practical for 30+ feature datasets.
            # ----------------------------------------------------------
            max_evals = max(
                2 * feature_count + 1,
                100,
            )

            # Prevent unnecessarily huge evaluation counts.
            max_evals = min(
                max_evals,
                1000,
            )

            shap_result = explainer(
                active_record,
                max_evals=max_evals,
            )

            values = np.asarray(
                shap_result.values,
                dtype=float,
            )

            # ----------------------------------------------------------
            # Normalize SHAP output shape.
            # ----------------------------------------------------------
            if values.ndim == 3:
                values = values[0, :, 0]

            elif values.ndim == 2:
                values = values[0]

            elif values.ndim == 1:
                values = values

            else:
                raise ValueError(
                    "Unexpected SHAP output shape."
                )

            values = np.nan_to_num(
                values,
                nan=0.0,
                posinf=0.0,
                neginf=0.0,
            )

            if len(values) != feature_count:
                raise ValueError(
                    "SHAP returned a feature count that does not "
                    "match the active Mahalanobis feature count."
                )

            # ----------------------------------------------------------
            # Extract base value.
            # ----------------------------------------------------------
            base_values = getattr(
                shap_result,
                "base_values",
                None,
            )

            if base_values is None:
                base_value = 0.0
            else:
                base_array = np.asarray(
                    base_values,
                    dtype=float,
                )

                if base_array.size == 0:
                    base_value = 0.0
                else:
                    base_value = float(
                        base_array.reshape(-1)[0]
                    )

            # ----------------------------------------------------------
            # Cache successful SHAP explanation.
            # ----------------------------------------------------------
            self._shap_values_cache[
                record_number
            ] = values

            self._shap_base_values_cache[
                record_number
            ] = base_value

            return (
                values,
                base_value,
                "shap",
                None,
            )

        except Exception as exc:
            # ----------------------------------------------------------
            # IMPORTANT:
            # Never allow SHAP failure to break the API.
            # ----------------------------------------------------------
            return (
                None,
                None,
                "exact_fallback",
                str(exc),
            )

    # ==================================================================
    # FORMATTING
    # ==================================================================

    @staticmethod
    def _format_number(
        value: float,
    ) -> str:
        """
        Format numerical values for readable explanations.
        """

        if not np.isfinite(value):
            return "0"

        return f"{float(value):.6g}"

    @staticmethod
    def _humanize_feature_name(
        feature_name: str,
    ) -> str:
        """
        Convert a backend column name into a readable UI label.
        """

        text = str(
            feature_name
        )

        text = text.replace(
            "_",
            " ",
        )

        text = text.replace(
            "-",
            " ",
        )

        return text.strip().title()

    # ==================================================================
    # FEATURE REASON
    # ==================================================================

    @classmethod
    def _build_feature_reason(
        cls,
        feature_name: str,
        actual_value: float,
        mean_value: float,
        contribution: float,
        contribution_percentage: float,
        shap_value: float | None = None,
    ) -> str:
        """
        Build a dynamic explanation using calculated values.

        No feature-specific wording is hard-coded.
        """

        actual_text = cls._format_number(
            actual_value
        )

        mean_text = cls._format_number(
            mean_value
        )

        contribution_text = cls._format_number(
            abs(contribution)
        )

        percentage_text = cls._format_number(
            contribution_percentage
        )

        if actual_value > mean_value:
            direction = "above"

        elif actual_value < mean_value:
            direction = "below"

        else:
            direction = "at"

        shap_sentence = ""

        if shap_value is not None:
            shap_sentence = (
                " SHAP attribution to the Mahalanobis "
                f"squared-distance function is "
                f"{cls._format_number(shap_value)}."
            )

        if direction == "at":
            return (
                f"{feature_name} is {actual_text}, which is at the "
                f"feature mean of {mean_text}. Its exact Mahalanobis "
                f"contribution magnitude is {contribution_text}, "
                f"representing {percentage_text}% of the total "
                f"absolute contribution."
                f"{shap_sentence}"
            )

        return (
            f"{feature_name} is {actual_text}, which is {direction} "
            f"the feature mean of {mean_text}. Its exact Mahalanobis "
            f"contribution magnitude is {contribution_text}, "
            f"representing {percentage_text}% of the total "
            f"absolute contribution."
            f"{shap_sentence}"
        )

    # ==================================================================
    # BUILD FEATURE RESULTS
    # ==================================================================

    def _build_feature_results(
        self,
        record_vector: np.ndarray,
        contributions: np.ndarray,
        percentages: np.ndarray,
        shap_values: np.ndarray | None,
        row_position: int,
    ) -> list[dict[str, Any]]:
        """
        Build the complete feature contribution list.

        IMPORTANT:
        Ranking is based on the exact Mahalanobis contribution.

        SHAP is provided as an additional attribution signal.

        This ensures the displayed "Top 3 Contributing Attributes"
        remains mathematically tied to the Mahalanobis score itself.
        """

        self._ensure_calculation_state()

        if (
            self._mean_vector is None
            or self._active_columns is None
        ):
            raise RuntimeError(
                "Mahalanobis calculation state was not initialized."
            )

        results: list[dict[str, Any]] = []

        # --------------------------------------------------------------
        # Active features.
        # --------------------------------------------------------------
        for index, feature_name in enumerate(
            self._active_columns
        ):
            actual_value = float(
                record_vector[index]
            )

            mean_value = float(
                self._mean_vector[index]
            )

            deviation = (
                actual_value
                - mean_value
            )

            contribution = float(
                contributions[index]
            )

            absolute_contribution = abs(
                contribution
            )

            contribution_percentage = float(
                percentages[index]
            )

            shap_value: float | None = None

            if (
                shap_values is not None
                and index < len(shap_values)
            ):
                shap_value = float(
                    shap_values[index]
                )

            if actual_value > mean_value:
                direction = "Above mean"

            elif actual_value < mean_value:
                direction = "Below mean"

            else:
                direction = "At mean"

            if abs(deviation) > 1e-15:
                covariance_adjusted_deviation = (
                    contribution
                    / deviation
                )
            else:
                covariance_adjusted_deviation = 0.0

            results.append(
                {
                    "feature_name": feature_name,
                    "feature": feature_name,
                    "label": self._humanize_feature_name(
                        feature_name
                    ),

                    "actual_value": actual_value,

                    "feature_mean": mean_value,
                    "mean_value": mean_value,

                    "deviation": float(
                        deviation
                    ),

                    "covariance_adjusted_deviation": float(
                        covariance_adjusted_deviation
                    ),

                    "contribution": contribution,
                    "signed_contribution": contribution,
                    "absolute_contribution": (
                        absolute_contribution
                    ),

                    "contribution_percentage": round(
                        contribution_percentage,
                        2,
                    ),

                    "shap_value": shap_value,

                    "absolute_shap_value": (
                        abs(shap_value)
                        if shap_value is not None
                        else None
                    ),

                    "shap_available": (
                        shap_value is not None
                    ),

                    "direction": direction,

                    "formula": (
                        "C_j = (x_j - μ_j) * "
                        "[Σ^-1(x - μ)]_j"
                    ),

                    "shap_formula": (
                        "D²(x) = E[D²(X)] + "
                        "Σ SHAP_j"
                    ),

                    "reason": self._build_feature_reason(
                        feature_name=feature_name,
                        actual_value=actual_value,
                        mean_value=mean_value,
                        contribution=contribution,
                        contribution_percentage=(
                            contribution_percentage
                        ),
                        shap_value=shap_value,
                    ),
                }
            )

        # --------------------------------------------------------------
        # Add excluded constant features.
        #
        # Their deviation is always zero, therefore their contribution
        # to Mahalanobis distance is exactly zero.
        # --------------------------------------------------------------
        for feature_name in self._excluded_columns:
            numeric_series = pd.to_numeric(
                self.dataframe[feature_name],
                errors="coerce",
            )

            mean_value = float(
                numeric_series.mean()
            ) if numeric_series.notna().any() else 0.0

            # Use the CURRENT record instead of always using row 0.
            actual_value = numeric_series.iloc[
                row_position
            ]

            if pd.isna(actual_value):
                actual_value = 0.0

            actual_value = float(
                actual_value
            )

            results.append(
                {
                    "feature_name": feature_name,
                    "feature": feature_name,
                    "label": self._humanize_feature_name(
                        feature_name
                    ),

                    "actual_value": actual_value,
                    "feature_mean": mean_value,
                    "mean_value": mean_value,

                    "deviation": 0.0,

                    "covariance_adjusted_deviation": 0.0,

                    "contribution": 0.0,
                    "signed_contribution": 0.0,
                    "absolute_contribution": 0.0,

                    "contribution_percentage": 0.0,

                    "shap_value": 0.0,
                    "absolute_shap_value": 0.0,

                    "shap_available": (
                        shap_values is not None
                    ),

                    "direction": "At mean",

                    "formula": (
                        "C_j = (x_j - μ_j) * "
                        "[Σ^-1(x - μ)]_j"
                    ),

                    "shap_formula": (
                        "D²(x) = E[D²(X)] + "
                        "Σ SHAP_j"
                    ),

                    "reason": (
                        f"{feature_name} is constant in the selected "
                        "dataset, so its Mahalanobis contribution is "
                        "0."
                    ),
                }
            )

        # --------------------------------------------------------------
        # Exact Mahalanobis contribution ranking.
        # --------------------------------------------------------------
        results.sort(
            key=lambda item: float(
                item["absolute_contribution"]
            ),
            reverse=True,
        )

        for rank, item in enumerate(
            results,
            start=1,
        ):
            item["rank"] = rank

        return results

    # ==================================================================
    # EXPLAIN ONE RECORD
    # ==================================================================

    def explain_record(
        self,
        record_number: int,
        mah_distance: float | None = None,
        threshold: float | None = None,
        top_n: int = MAX_FEATURES,
    ) -> dict[str, Any]:
        """
        Explain one record.

        record_number is 1-based.

        mah_distance is the REAL Mahalanobis distance from the
        detection backend.

        It is NEVER replaced by a newly calculated value.

        SHAP is attempted for additional explainability.

        Exact Mahalanobis decomposition is always calculated.
        """

        if record_number < 1:
            raise ValueError(
                "record_number must be at least 1."
            )

        if record_number > len(
            self.dataframe
        ):
            raise ValueError(
                f"record_number {record_number} is outside the dataset."
            )

        if top_n < 1:
            raise ValueError(
                "top_n must be at least 1."
            )

        self._ensure_calculation_state()

        if (
            self._active_matrix is None
            or self._mean_vector is None
            or self._inverse_covariance_matrix is None
            or self._active_columns is None
        ):
            raise RuntimeError(
                "Unable to initialize Mahalanobis explainability."
            )

        top_n = min(
            int(top_n),
            len(self.used_columns),
        )

        row_position = (
            record_number - 1
        )

        # --------------------------------------------------------------
        # Active feature vector.
        # --------------------------------------------------------------
        record_vector = self._active_matrix[
            row_position
        ]

        # --------------------------------------------------------------
        # Exact Mahalanobis contribution.
        # --------------------------------------------------------------
        contributions = (
            self._calculate_feature_contributions(
                record_vector=record_vector,
                mean_vector=self._mean_vector,
                inverse_covariance=(
                    self._inverse_covariance_matrix
                ),
            )
        )

        absolute_contributions = np.abs(
            contributions
        )

        percentages = (
            self._contribution_percentage(
                absolute_contributions
            )
        )

        # --------------------------------------------------------------
        # SHAP attribution.
        #
        # Failure here does NOT fail the whole explanation.
        # --------------------------------------------------------------
        (
            shap_values,
            shap_base_value,
            explanation_method,
            shap_error,
        ) = self._calculate_shap_values(
            record_vector=record_vector,
            record_number=record_number,
        )

        # --------------------------------------------------------------
        # Complete feature list.
        # --------------------------------------------------------------
        feature_results = (
            self._build_feature_results(
                record_vector=record_vector,
                contributions=contributions,
                percentages=percentages,
                shap_values=shap_values,
                row_position=row_position,
            )
        )

        top_features = feature_results[
            :top_n
        ]

        # --------------------------------------------------------------
        # Mathematical validation.
        #
        # This is only for verification.
        # It does not replace the backend detection score.
        # --------------------------------------------------------------
        centered = (
            record_vector
            - self._mean_vector
        )

        calculated_squared_distance = float(
            centered
            @ self._inverse_covariance_matrix
            @ centered
        )

        calculated_squared_distance = max(
            calculated_squared_distance,
            0.0,
        )

        calculated_distance = float(
            np.sqrt(
                calculated_squared_distance
            )
        )

        signed_contribution_sum = float(
            np.sum(
                contributions
            )
        )

        # --------------------------------------------------------------
        # SHAP reconstruction.
        #
        # SHAP explains D², not D.
        # --------------------------------------------------------------
        shap_reconstructed_score: float | None = None
        shap_score_difference: float | None = None

        if shap_values is not None:
            shap_reconstructed_score = float(
                (
                    shap_base_value
                    if shap_base_value is not None
                    else 0.0
                )
                + np.sum(
                    shap_values
                )
            )

            shap_score_difference = float(
                shap_reconstructed_score
                - calculated_squared_distance
            )

        # --------------------------------------------------------------
        # Real backend status.
        # --------------------------------------------------------------
        status = None

        if (
            mah_distance is not None
            and threshold is not None
        ):
            status = (
                "Anomaly"
                if float(mah_distance)
                > float(threshold)
                else "Normal"
            )

        # --------------------------------------------------------------
        # Threshold gap.
        # --------------------------------------------------------------
        threshold_gap = None

        if (
            mah_distance is not None
            and threshold is not None
        ):
            threshold_gap = (
                float(mah_distance)
                - float(threshold)
            )

        # --------------------------------------------------------------
        # Calculation steps for the UI.
        # --------------------------------------------------------------
        calculation_summary = {
            "step_1": {
                "title": "Feature Value and Mean",
                "formula": "d = x - μ",
                "explanation": (
                    "For each numerical feature, the selected "
                    "record value is compared with the feature "
                    "mean calculated from the Phase 3 preprocessed "
                    "dataset."
                ),
            },

            "step_2": {
                "title": "Covariance Adjustment",
                "formula": "a = Σ^-1 d",
                "explanation": (
                    "The inverse covariance matrix adjusts each "
                    "feature deviation according to the relationships "
                    "and correlations among the selected features."
                ),
            },

            "step_3": {
                "title": "Raw Mahalanobis Contribution",
                "formula": "C_j = d_j * a_j",
                "explanation": (
                    "Each feature receives a signed contribution "
                    "to the squared Mahalanobis distance."
                ),
            },

            "step_4": {
                "title": "Mahalanobis Distance",
                "formula": "D² = Σ C_j ; D = sqrt(D²)",
                "explanation": (
                    "The signed feature contributions reconstruct "
                    "the squared Mahalanobis distance up to numerical "
                    "precision."
                ),
            },

            "step_5": {
                "title": "Relative Feature Contribution",
                "formula": (
                    "Importance_j = "
                    "|C_j| / Σ|C_k| × 100"
                ),
                "explanation": (
                    "Absolute contribution magnitude is converted "
                    "to a percentage so features can be ranked "
                    "without allowing negative covariance terms "
                    "to cancel positive terms."
                ),
            },

            "step_6": {
                "title": "SHAP Attribution",
                "formula": (
                    "D²(x) = E[D²(X)] + Σ SHAP_j"
                ),
                "explanation": (
                    "SHAP independently attributes the same "
                    "Mahalanobis squared-distance function to "
                    "individual features. SHAP values are supplied "
                    "as an additional explainability signal."
                ),
            },
        }

        # --------------------------------------------------------------
        # Actual feature values.
        # --------------------------------------------------------------
        actual_feature_values: dict[str, float] = {}

        for index, feature_name in enumerate(
            self._active_columns
        ):
            actual_feature_values[
                feature_name
            ] = float(
                record_vector[index]
            )

        for feature_name in self._excluded_columns:
            series = pd.to_numeric(
                self.dataframe[feature_name],
                errors="coerce",
            )

            value = series.iloc[
                row_position
            ]

            if pd.isna(value):
                value = 0.0

            actual_feature_values[
                feature_name
            ] = float(value)

        # --------------------------------------------------------------
        # Final result.
        # --------------------------------------------------------------
        result: dict[str, Any] = {
            "record_number": record_number,

            # Existing-compatible top feature field.
            "feature_contributions": top_features,

            # New requested fields.
            "top_contributors": top_features,
            "all_feature_contributions": feature_results,

            # Real backend score.
            "mah_distance": (
                float(mah_distance)
                if mah_distance is not None
                else None
            ),

            "mahalanobis_score": (
                float(mah_distance)
                if mah_distance is not None
                else None
            ),

            # Independent mathematical validation.
            "calculated_mahalanobis_distance": (
                calculated_distance
            ),

            "calculated_mahalanobis_squared_distance": (
                calculated_squared_distance
            ),

            # Threshold information.
            "threshold": (
                float(threshold)
                if threshold is not None
                else None
            ),

            "threshold_gap": threshold_gap,

            "status": status,

            "is_anomaly": (
                status == "Anomaly"
                if status is not None
                else None
            ),

            # Feature information.
            "columns_involved": list(
                self._active_columns
            ),

            "excluded_constant_columns": list(
                self._excluded_columns
            ),

            "actual_feature_values": (
                actual_feature_values
            ),

            # Explainability method.
            "explanation_method": (
                explanation_method
            ),

            "shap_available": (
                shap_values is not None
            ),

            "shap_library_available": (
                SHAP_AVAILABLE
            ),

            "shap_base_value": (
                shap_base_value
            ),

            "shap_reconstructed_squared_score": (
                shap_reconstructed_score
            ),

            "shap_score_difference": (
                shap_score_difference
            ),

            "shap_error": (
                shap_error
            ),

            # Exact mathematical validation.
            "signed_contribution_sum": (
                signed_contribution_sum
            ),

            "score_consistency": {
                "calculated_squared_distance": (
                    calculated_squared_distance
                ),

                "signed_contribution_sum": (
                    signed_contribution_sum
                ),

                "difference": (
                    signed_contribution_sum
                    - calculated_squared_distance
                ),

                "consistent": bool(
                    np.isclose(
                        signed_contribution_sum,
                        calculated_squared_distance,
                        rtol=1e-5,
                        atol=1e-7,
                    )
                ),
            },

            # Calculation explanation.
            "calculation_summary": (
                calculation_summary
            ),

            # High-level explanation.
            "explanation": (
                "Feature contributions were calculated from the "
                "Mahalanobis quadratic form. "
                + (
                    "SHAP was successfully applied to the same "
                    "Mahalanobis squared-distance function."
                    if shap_values is not None
                    else
                    "SHAP was unavailable or could not be calculated, "
                    "so the exact Mahalanobis feature decomposition "
                    "was used as the guaranteed fallback."
                )
            ),
        }

        return result

    # ==================================================================
    # EXPLAIN ALL RECORDS
    # ==================================================================

    def explain_all(
        self,
        scores: list[float] | np.ndarray | None = None,
        threshold: float | None = None,
        top_n: int = MAX_FEATURES,
    ) -> list[dict[str, Any]]:
        """
        Generate explanations for all records.

        SHAP is attempted for each record.

        If SHAP fails for any record, that record automatically falls
        back to the exact Mahalanobis decomposition.
        """

        if scores is not None:
            scores = np.asarray(
                scores,
                dtype=float,
            )

            if len(scores) != len(
                self.dataframe
            ):
                raise ValueError(
                    "The number of scores must match the number "
                    "of dataframe records."
                )

        results: list[dict[str, Any]] = []

        for record_number in range(
            1,
            len(self.dataframe) + 1,
        ):
            score = (
                float(
                    scores[
                        record_number - 1
                    ]
                )
                if scores is not None
                else None
            )

            results.append(
                self.explain_record(
                    record_number=record_number,
                    mah_distance=score,
                    threshold=threshold,
                    top_n=top_n,
                )
            )

        return results


# ======================================================================
# PUBLIC API HELPER
# ======================================================================

def explain_mahalanobis_record(
    preprocessed_df: pd.DataFrame,
    used_columns: list[str],
    record_number: int,
    mah_distance: float | None = None,
    threshold: float | None = None,
    top_n: int = 3,
) -> dict[str, Any]:
    """
    Public helper used by the statistical API layer.

    The supplied mah_distance is the actual detection-backend
    Mahalanobis distance.

    SHAP is used only for explainability.

    SHAP failure never replaces or invalidates the real detection
    score.
    """

    explainer = MahalanobisExplainability(
        dataframe=preprocessed_df,
        used_columns=used_columns,
    )

    return explainer.explain_record(
        record_number=record_number,
        mah_distance=mah_distance,
        threshold=threshold,
        top_n=top_n,
    )