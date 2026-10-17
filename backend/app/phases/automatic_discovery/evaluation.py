from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phases.automatic_discovery.detection_engine import run_detection


RANDOM_SEED = 42
INJECTION_FRACTION = 0.05
PERTURBATION_MULTIPLIER = 2.75


def _select_numeric_column(
    dataframe: pd.DataFrame,
) -> str:
    """
    Select a suitable numerical column for controlled evaluation.
    """

    numeric_columns = dataframe.select_dtypes(
        include=[np.number]
    ).columns.tolist()

    if not numeric_columns:
        raise ValueError(
            "No numerical column is available for ML accuracy evaluation."
        )

    for column in numeric_columns:
        values = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

        valid_count = int(
            np.isfinite(
                values.to_numpy(dtype=np.float64)
            ).sum()
        )

        if valid_count >= 5:
            return column

    raise ValueError(
        "No numerical column contains enough valid observations for ML accuracy evaluation."
    )


def _inject_controlled_anomalies(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, list[int], str]:
    """
    Create a controlled evaluation copy of the dataframe.

    Approximately 5% of valid numerical observations are
    statistically perturbed and marked as ground-truth anomalies.

    The original dataframe is never modified.

    Returns:
        evaluation_dataframe
        ground_truth_labels
        selected_numeric_column
    """

    if dataframe.empty:
        raise ValueError(
            "Cannot create an evaluation dataset from an empty dataframe."
        )

    numeric_column = _select_numeric_column(
        dataframe
    )

    # Work only on a deep copy.
    evaluation_dataframe = dataframe.copy(
        deep=True
    )

    # The original column may be int64.
    # The statistical perturbation is a float.
    # Convert only the evaluation copy to float64.
    evaluation_dataframe[
        numeric_column
    ] = pd.to_numeric(
        evaluation_dataframe[
            numeric_column
        ],
        errors="coerce",
    ).astype(
        np.float64
    )

    values = evaluation_dataframe[
        numeric_column
    ].to_numpy(
        dtype=np.float64,
        copy=True,
    )

    valid_positions = np.flatnonzero(
        np.isfinite(values)
    )

    if len(valid_positions) < 5:
        raise ValueError(
            f"Column '{numeric_column}' does not contain enough valid numerical observations for evaluation."
        )

    valid_values = values[
        valid_positions
    ]

    # ---------------------------------------------------------
    # Calculate statistically meaningful perturbation scale
    # ---------------------------------------------------------

    median = float(
        np.median(
            valid_values
        )
    )

    absolute_deviation = np.abs(
        valid_values - median
    )

    mad = float(
        np.median(
            absolute_deviation
        )
    )

    q1 = float(
        np.percentile(
            valid_values,
            25
        )
    )

    q3 = float(
        np.percentile(
            valid_values,
            75
        )
    )

    iqr = float(
        q3 - q1
    )

    standard_deviation = float(
        np.std(
            valid_values,
            ddof=1,
        )
    )

    value_range = float(
        np.max(valid_values)
        - np.min(valid_values)
    )

    robust_scales: list[float] = []

    if (
        np.isfinite(mad)
        and mad > 0
    ):
        robust_scales.append(
            mad * 1.4826
        )

    if (
        np.isfinite(iqr)
        and iqr > 0
    ):
        robust_scales.append(
            iqr / 1.349
        )

    if (
        np.isfinite(
            standard_deviation
        )
        and standard_deviation > 0
    ):
        robust_scales.append(
            standard_deviation
        )

    if (
        np.isfinite(value_range)
        and value_range > 0
    ):
        robust_scales.append(
            value_range * 0.01
        )

    if not robust_scales:
        raise ValueError(
            f"Column '{numeric_column}' has no usable statistical scale for controlled anomaly injection."
        )

    robust_scale = max(
        robust_scales
    )

    # ---------------------------------------------------------
    # Select approximately 5% of valid observations
    # ---------------------------------------------------------

    anomaly_count = max(
        1,
        int(
            round(
                INJECTION_FRACTION
                * len(valid_positions)
            )
        ),
    )

    anomaly_count = min(
        anomaly_count,
        len(valid_positions),
    )

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    selected_positions = rng.choice(
        valid_positions,
        size=anomaly_count,
        replace=False,
    )

    selected_positions = np.sort(
        selected_positions
    )

    perturbation = (
        PERTURBATION_MULTIPLIER
        * robust_scale
    )

    # 0 = normal
    # 1 = injected anomaly
    ground_truth = np.zeros(
        len(evaluation_dataframe),
        dtype=np.uint8,
    )

    # ---------------------------------------------------------
    # Inject controlled anomalies
    # ---------------------------------------------------------

    for position_number, position in enumerate(
        selected_positions
    ):
        original_value = float(
            values[position]
        )

        direction = (
            1.0
            if position_number % 2 == 0
            else -1.0
        )

        modified_value = (
            original_value
            + direction
            * perturbation
        )

        values[position] = float(
            modified_value
        )

        ground_truth[position] = 1

    evaluation_dataframe[
        numeric_column
    ] = values

    return (
        evaluation_dataframe,
        ground_truth.tolist(),
        numeric_column,
    )


def _build_evaluation_models(
    detection: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Convert the models returned by the benchmark/detection
    pipeline into the format expected by run_detection().
    """

    models = detection.get(
        "models",
        []
    )

    if not models:
        raise ValueError(
            "No benchmark models are available for ML accuracy evaluation."
        )

    evaluation_models: list[dict[str, Any]] = []

    for item in models:
        model_name = item.get(
            "model"
        )

        combined_score = item.get(
            "benchmark_combined_score"
        )

        if combined_score is None:
            combined_score = item.get(
                "combined_score"
            )

        if not model_name:
            continue

        if combined_score is None:
            continue

        try:
            combined_score = float(
                combined_score
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if not np.isfinite(
            combined_score
        ):
            continue

        evaluation_models.append(
            {
                "model": str(
                    model_name
                ),
                "combined_score": combined_score,
            }
        )

    if not evaluation_models:
        raise ValueError(
            "No valid benchmark model scores are available for ML accuracy evaluation."
        )

    return evaluation_models


def _run_same_ml_detection(
    dataframe: pd.DataFrame,
    detection: dict[str, Any],
) -> np.ndarray:
    """
    Run the same ML detection approach on the controlled
    evaluation dataframe.

    Ground-truth labels are never supplied to the detector.
    """

    approach = str(
        detection.get(
            "approach",
            ""
        )
    )

    score_method = str(
        detection.get(
            "score_method",
            "combined_score"
        )
    ).lower()

    columns = detection.get(
        "columns",
        []
    )

    if not columns:
        raise ValueError(
            "No detection columns are available for ML accuracy evaluation."
        )

    contamination = float(
        detection.get(
            "contamination",
            0.05
        )
    )

    if contamination <= 0:
        contamination = 0.05

    if contamination >= 1:
        contamination = 0.05

    available_columns = [
        column
        for column in columns
        if column in dataframe.columns
    ]

    if not available_columns:
        raise ValueError(
            "None of the selected detection columns are available in the evaluation dataframe."
        )

    benchmark_models = _build_evaluation_models(
        detection
    )

    # ---------------------------------------------------------
    # Best Score
    # ---------------------------------------------------------

    if score_method == "best_score":
        selected_model = detection.get(
            "selected_model"
        )

        if not selected_model:
            selected_model = detection.get(
                "model_name"
            )

        if selected_model:
            selected = [
                item
                for item in benchmark_models
                if item["model"] == selected_model
            ]

            if selected:
                benchmark_models = selected

        # Best Score requires exactly one model.
        benchmark_models = benchmark_models[:1]

    # ---------------------------------------------------------
    # Combined Score
    # ---------------------------------------------------------

    else:
        # The production Combined Score uses the fixed
        # recommended top-three models.
        benchmark_models = benchmark_models[:3]

        if len(benchmark_models) < 3:
            raise ValueError(
                "Combined Score evaluation requires three benchmark models."
            )

    result = run_detection(
        dataframe=dataframe,
        approach=approach,
        columns=available_columns,
        models=benchmark_models,
        contamination=contamination,
        score_method=score_method,
    )

    predicted_labels = np.asarray(
        result.get(
            "combined_labels",
            []
        ),
        dtype=np.uint8,
    )

    if len(predicted_labels) != len(
        dataframe
    ):
        raise ValueError(
            "ML detection returned an invalid number of prediction labels for accuracy evaluation."
        )

    return predicted_labels


def _calculate_accuracy(
    actual_labels: list[int] | np.ndarray,
    predicted_labels: list[int] | np.ndarray,
) -> dict[str, Any]:
    """
    Calculate classification accuracy from ground-truth and
    predicted anomaly labels.

    Label convention:
        0 = Normal
        1 = Anomaly
    """

    actual = np.asarray(
        actual_labels,
        dtype=np.uint8,
    )

    predicted = np.asarray(
        predicted_labels,
        dtype=np.uint8,
    )

    if len(actual) != len(predicted):
        raise ValueError(
            "Actual and predicted labels must contain the same number of records."
        )

    if len(actual) == 0:
        raise ValueError(
            "At least one record is required to calculate ML accuracy."
        )

    true_positive = int(
        np.sum(
            (actual == 1)
            & (predicted == 1)
        )
    )

    true_negative = int(
        np.sum(
            (actual == 0)
            & (predicted == 0)
        )
    )

    false_positive = int(
        np.sum(
            (actual == 0)
            & (predicted == 1)
        )
    )

    false_negative = int(
        np.sum(
            (actual == 1)
            & (predicted == 0)
        )
    )

    correct_predictions = (
        true_positive
        + true_negative
    )

    total_records = len(
        actual
    )

    accuracy = (
        correct_predictions
        / total_records
    ) * 100.0

    return {
        "accuracy": round(
            float(accuracy),
            2,
        ),
        "total_records": int(
            total_records
        ),
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
    }


def evaluate_ml_detection(
    dataframe: pd.DataFrame,
    detection: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate the actual ML anomaly-detection approach using
    controlled statistically perturbed anomalies.

    The production dataframe and production detection result
    are never modified.

    The evaluation process is:

        1. Copy the preprocessed dataframe.
        2. Inject approximately 5% controlled anomalies.
        3. Store those injected positions as ground truth.
        4. Run the same ML detection configuration.
        5. Compare predicted labels with ground truth.
        6. Calculate classification accuracy.
    """

    if dataframe is None:
        raise ValueError(
            "A dataframe is required for ML accuracy evaluation."
        )

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):
        raise TypeError(
            "ML accuracy evaluation requires a pandas DataFrame."
        )

    if dataframe.empty:
        raise ValueError(
            "Cannot evaluate ML detection on an empty dataframe."
        )

    # ---------------------------------------------------------
    # Create independent evaluation dataset
    # ---------------------------------------------------------

    (
        evaluation_dataframe,
        ground_truth_labels,
        evaluated_column,
    ) = _inject_controlled_anomalies(
        dataframe
    )

    # ---------------------------------------------------------
    # Run the actual ML detection approach
    # ---------------------------------------------------------

    predicted_labels = _run_same_ml_detection(
        dataframe=evaluation_dataframe,
        detection=detection,
    )

    # ---------------------------------------------------------
    # Calculate final accuracy
    # ---------------------------------------------------------

    metrics = _calculate_accuracy(
        actual_labels=ground_truth_labels,
        predicted_labels=predicted_labels,
    )

    return {
        "accuracy": float(
            metrics["accuracy"]
        ),
        "total_records": int(
            metrics["total_records"]
        ),
        "confusion_matrix": {
            "true_positive": int(
                metrics["true_positive"]
            ),
            "true_negative": int(
                metrics["true_negative"]
            ),
            "false_positive": int(
                metrics["false_positive"]
            ),
            "false_negative": int(
                metrics["false_negative"]
            ),
        },
        "evaluation": {
            "injection_fraction": float(
                INJECTION_FRACTION
            ),
            "injected_anomalies": int(
                sum(ground_truth_labels)
            ),
            "evaluated_column": str(
                evaluated_column
            ),
            "perturbation_multiplier": float(
                PERTURBATION_MULTIPLIER
            ),
        },
        "score_method": str(
            detection.get(
                "score_method",
                "combined_score",
            )
        ),
        "approach": str(
            detection.get(
                "approach",
                "",
            )
        ),
    }