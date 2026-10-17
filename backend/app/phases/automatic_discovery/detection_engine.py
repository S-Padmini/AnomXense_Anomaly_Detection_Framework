from __future__ import annotations

import inspect
from typing import Any

import numpy as np
import pandas as pd

from app.phases.phase6.detection_engine import (
    _build_features,
    _import_model_class,
    _make_model,
    _model_fit_input,
)

SCORE_BATCH_ROWS = 8192
TRAIN_LIMIT_DEFAULT = 5000
TRAIN_LIMIT_CLUSTER = 2500
TRAIN_LIMIT_NEIGHBOR = 1500
RANDOM_SEED = 9100


def _train_limit(model_name: str, n_rows: int) -> int:
    name = str(model_name).strip()
    if name == "CBLOF":
        limit = TRAIN_LIMIT_CLUSTER
    elif name in {"KNN", "LOF"}:
        limit = TRAIN_LIMIT_NEIGHBOR
    else:
        limit = TRAIN_LIMIT_DEFAULT
    return max(2, min(int(n_rows), limit))


def _training_indices(n_rows: int, limit: int, seed: int = RANDOM_SEED) -> np.ndarray:
    if n_rows <= limit:
        return np.arange(n_rows, dtype=np.int64)
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(n_rows, size=limit, replace=False)).astype(np.int64)


def _finite_matrix(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float64)
    if X.ndim != 2 or X.shape[0] < 5 or X.shape[1] < 1:
        raise ValueError("At least five records and one prepared feature are required.")
    if not np.isfinite(X).all():
        raise ValueError("Prepared features contain non-finite values.")
    return X


def _fit_cblof(X: np.ndarray, contamination: float, training_rows: int) -> Any:
    try:
        CBLOF = _import_model_class("CBLOF")
        from sklearn.cluster import KMeans, MiniBatchKMeans
    except Exception as exc:
        raise RuntimeError(f"CBLOF is unavailable: {exc}") from exc

    try:
        parameters = inspect.signature(CBLOF).parameters
    except (TypeError, ValueError):
        parameters = {}

    unique_rows = int(np.unique(X, axis=0).shape[0])
    max_k = min(8, len(X) - 1, unique_rows)
    if max_k < 2:
        raise RuntimeError("CBLOF requires at least two distinct training rows.")

    last_error: Exception | None = None
    for k in range(2, max_k + 1):
        clusterer = (
            MiniBatchKMeans(
                n_clusters=k,
                random_state=RANDOM_SEED,
                batch_size=min(1024, max(128, training_rows)),
                n_init=2,
                max_iter=100,
            )
            if training_rows > 1500
            else KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=2, max_iter=100)
        )
        labels = clusterer.fit_predict(X)
        counts = np.bincount(labels, minlength=k)
        if np.count_nonzero(counts) < 2 or counts.min() == 0:
            continue

        sorted_counts = np.sort(counts[counts > 0])[::-1]
        for split in range(1, len(sorted_counts)):
            alpha = max(
                0.01,
                min(0.99, float(sorted_counts[:split].sum()) / len(X) - 1e-3),
            )
            kwargs: dict[str, Any] = {"n_clusters": k, "alpha": alpha, "beta": 1.0}
            if "clustering_estimator" in parameters:
                kwargs["clustering_estimator"] = clusterer
            if "contamination" in parameters:
                kwargs["contamination"] = float(contamination)
            if "random_state" in parameters:
                kwargs["random_state"] = RANDOM_SEED
            if "n_jobs" in parameters:
                kwargs["n_jobs"] = 1
            if "check_estimator" in parameters:
                kwargs["check_estimator"] = False
            try:
                model = CBLOF(**kwargs)
                model.fit(X)
                threshold = getattr(model, "threshold_", None)
                if threshold is not None and np.isfinite(float(threshold)):
                    return model
            except Exception as exc:
                last_error = exc

    raise RuntimeError(f"PyOD CBLOF could not form a valid cluster separation: {last_error}")


def _fit_selected_model(model_name: str, fit_X: np.ndarray, contamination: float, training_rows: int) -> Any:
    if str(model_name).strip() == "CBLOF":
        return _fit_cblof(fit_X, contamination, training_rows)
    try:
        model = _make_model(model_name, training_rows, contamination)
        model.fit(fit_X)
        return model
    except Exception as exc:
        raise RuntimeError(f"Unable to fit selected PyOD model {model_name}: {exc}") from exc


def fit_score_batched(
    model_name: str,
    X: np.ndarray,
    contamination: float,
    *,
    training_indices: np.ndarray | None = None,
    batch_rows: int = SCORE_BATCH_ROWS,
    random_seed: int = RANDOM_SEED,
) -> tuple[Any, np.ndarray, np.ndarray, float, float]:
    contamination = float(contamination)
    if not 0.01 <= contamination <= 0.50:
        raise ValueError("Contamination must be between 0.01 and 0.50.")

    X = _finite_matrix(X)
    limit = _train_limit(model_name, len(X))
    train_idx = (
        _training_indices(len(X), limit, random_seed)
        if training_indices is None
        else np.unique(np.asarray(training_indices, dtype=np.int64).reshape(-1))
    )
    if len(train_idx) < 2:
        raise ValueError("The model training sample must contain at least two records.")
    if np.any(train_idx < 0) or np.any(train_idx >= len(X)):
        raise ValueError("Training indices are outside the feature matrix.")
    if len(train_idx) > limit:
        train_idx = train_idx[_training_indices(len(train_idx), limit, random_seed)]

    fit_X = _model_fit_input(model_name, X[train_idx])
    model = _fit_selected_model(model_name, fit_X, contamination, len(train_idx))

    threshold_value = getattr(model, "threshold_", None)
    if threshold_value is None or not np.isfinite(float(threshold_value)):
        raise RuntimeError(f"{model_name} did not produce a finite anomaly threshold.")
    threshold = float(threshold_value)

    scores = np.empty(len(X), dtype=np.float64)
    batch_rows = max(256, int(batch_rows))
    for start in range(0, len(X), batch_rows):
        end = min(start + batch_rows, len(X))
        batch_X = _model_fit_input(model_name, X[start:end])
        batch_scores = np.asarray(model.decision_function(batch_X), dtype=np.float64).reshape(-1)
        if len(batch_scores) != end - start or not np.isfinite(batch_scores).all():
            raise RuntimeError(f"{model_name} returned invalid anomaly scores.")
        scores[start:end] = batch_scores

    labels = (scores > threshold).astype(np.uint8)
    return model, scores, labels, threshold, contamination


def _prepare_unit(dataframe: pd.DataFrame, columns: list[str], unit_name: str) -> dict[str, Any]:
    feature_matrix = _build_features(dataframe, columns)
    X = _finite_matrix(feature_matrix.X)
    if len(X) != len(dataframe):
        raise ValueError(f"Feature preparation returned an invalid row count for {unit_name!r}.")
    return {
        "unit": unit_name,
        "columns": list(columns),
        "X": X,
        "feature_names": list(feature_matrix.feature_names),
        "feature_sources": list(feature_matrix.feature_sources),
    }


def _minmax_normalize(scores: np.ndarray) -> tuple[np.ndarray, float, float]:
    scores = np.asarray(scores, dtype=np.float64)
    if scores.ndim != 1 or not np.isfinite(scores).all():
        raise ValueError("Model scores must be a finite one-dimensional array.")
    minimum = float(np.min(scores))
    maximum = float(np.max(scores))
    span = maximum - minimum
    if span <= 0.0:
        return np.zeros_like(scores), minimum, maximum
    return (scores - minimum) / span, minimum, maximum


def _record_score_table(dataframe: pd.DataFrame, model_outputs: list[dict[str, Any]],
                       final_scores: np.ndarray, final_thresholds: np.ndarray,
                       labels: np.ndarray) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index in range(len(dataframe)):
        item: dict[str, Any] = {"record_index": int(index)}
        for output in model_outputs:
            name = output["model"]
            item[f"{name}_raw_score"] = float(output["raw_scores"][index])
            if output.get("normalized_scores") is not None:
                item[f"{name}_normalized_score"] = float(output["normalized_scores"][index])
            item[f"{name}_weight"] = float(output["weight"])
        item["anomaly_score"] = float(final_scores[index])
        item["threshold"] = float(final_thresholds[index]) if np.isfinite(final_thresholds[index]) else None
        item["status"] = "Anomaly" if int(labels[index]) else "Normal"
        records.append(item)
    return records


def run_detection(
    dataframe: pd.DataFrame,
    approach: str,
    columns: list[str],
    models: list[dict[str, Any]],
    contamination: float,
    *,
    score_method: str = "combined_score",
) -> dict[str, Any]:
    """Run Automatic Discovery final detection.

    combined_score: all three fixed top-three models are fitted independently.
    Their raw PyOD scores are min-max normalized per model and combined using
    normalized benchmark Combined Scores as weights.

    best_score: exactly one user-selected top-three model is fitted and used.
    """
    if dataframe is None or len(dataframe) < 5:
        raise ValueError("At least five preprocessed records are required.")
    if not columns:
        raise ValueError("Select at least one feature for anomaly detection.")
    missing = [column for column in columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Selected columns are missing from Phase 3 data: {missing}")
    if approach not in {"univariate", "multivariate"}:
        raise ValueError("Approach must be univariate or multivariate.")
    if score_method not in {"best_score", "combined_score"}:
        raise ValueError("Choose best_score or combined_score.")
    contamination = float(contamination)
    if not 0.01 <= contamination <= 0.50:
        raise ValueError("Contamination must be between 0.01 and 0.50.")

    if score_method == "combined_score":
        if len(models) != 3:
            raise ValueError("Combined Score requires exactly the three fixed top-three recommended models.")
    elif len(models) != 1:
        raise ValueError("Best Score detection requires exactly one selected model.")

    names = [str(item.get("model", "")).strip() for item in models]
    if len(set(names)) != len(names) or any(not name for name in names):
        raise ValueError("Detection models must be distinct and valid.")

    benchmark_scores = np.asarray(
        [float(item.get("combined_score")) for item in models], dtype=np.float64
    )
    if not np.isfinite(benchmark_scores).all() or np.any(benchmark_scores < 0):
        raise ValueError("Each selected model must have a valid non-negative benchmark Combined Score.")

    if score_method == "combined_score":
        weight_total = float(benchmark_scores.sum())
        if weight_total <= 0:
            raise ValueError("The three recommended models have no positive benchmark Combined Score.")
        weights = benchmark_scores / weight_total
    else:
        weights = np.array([1.0], dtype=np.float64)

    units = (
        [_prepare_unit(dataframe, columns, "__multivariate__")]
        if approach == "multivariate"
        else [_prepare_unit(dataframe, [column], column) for column in columns]
    )

    model_outputs: list[dict[str, Any]] = []
    for model_index, model_item in enumerate(models):
        model_name = names[model_index]
        _import_model_class(model_name)
        unit_outputs: list[dict[str, Any]] = []
        for unit_index, unit in enumerate(units):
            fitted_model, raw_scores, model_labels, model_threshold, _ = fit_score_batched(
                model_name,
                unit["X"],
                contamination,
                random_seed=RANDOM_SEED + model_index * 1000 + unit_index,
            )
            unit_outputs.append({
                "unit": unit["unit"],
                "columns": unit["columns"],
                "raw_scores": raw_scores,
                "labels": model_labels,
                "threshold": float(model_threshold),
                "training_rows": min(len(unit["X"]), _train_limit(model_name, len(unit["X"]))),
                "model": fitted_model,
                "X": unit["X"],
                "feature_names": unit["feature_names"],
                "feature_sources": unit["feature_sources"],
            })

        # A selected model's univariate overall score is the maximum score
        # across its independent column units. This preserves the fact that
        # each column is detected independently while providing one record view.
        raw_scores = (
            unit_outputs[0]["raw_scores"].copy()
            if len(unit_outputs) == 1
            else np.max(np.vstack([u["raw_scores"] for u in unit_outputs]), axis=0)
        )
        normalized_scores, raw_min, raw_max = _minmax_normalize(raw_scores)

        model_outputs.append({
            "model": model_name,
            "benchmark_combined_score": float(benchmark_scores[model_index]),
            "weight": float(weights[model_index]),
            "raw_scores": raw_scores,
            "normalized_scores": normalized_scores if score_method == "combined_score" else None,
            "raw_min": raw_min,
            "raw_max": raw_max,
            "unit_results": unit_outputs,
        })

    if score_method == "combined_score":
        # Multivariate has one analysis unit, so one ensemble score/threshold
        # applies to the whole dataset. Univariate keeps every selected column
        # independent: each column gets its own three-model ensemble and its own
        # contamination threshold; the overall record status is the union of
        # those column-level anomaly decisions.
        if approach == "multivariate":
            final_scores = np.zeros(len(dataframe), dtype=np.float64)
            for output in model_outputs:
                final_scores += output["weight"] * output["normalized_scores"]
            final_threshold = float(np.quantile(final_scores, 1.0 - contamination))
            labels = (final_scores > final_threshold).astype(np.uint8)
            final_thresholds = np.full(len(dataframe), final_threshold, dtype=np.float64)
        else:
            unit_ensemble_scores: list[np.ndarray] = []
            unit_thresholds: list[float] = []
            unit_labels: list[np.ndarray] = []
            for unit_index, unit in enumerate(units):
                ensemble_scores_for_unit = np.zeros(len(dataframe), dtype=np.float64)
                for model_index, output in enumerate(model_outputs):
                    raw = np.asarray(output["unit_results"][unit_index]["raw_scores"], dtype=np.float64)
                    normalized, _, _ = _minmax_normalize(raw)
                    output["unit_results"][unit_index]["normalized_scores"] = normalized
                    ensemble_scores_for_unit += output["weight"] * normalized
                threshold_for_unit = float(np.quantile(ensemble_scores_for_unit, 1.0 - contamination))
                labels_for_unit = (ensemble_scores_for_unit > threshold_for_unit).astype(np.uint8)
                output_unit = {
                    "ensemble_scores": ensemble_scores_for_unit,
                    "ensemble_threshold": threshold_for_unit,
                    "ensemble_labels": labels_for_unit,
                }
                for output in model_outputs:
                    output["unit_results"][unit_index].update(output_unit)
                unit_ensemble_scores.append(ensemble_scores_for_unit)
                unit_thresholds.append(threshold_for_unit)
                unit_labels.append(labels_for_unit)

            final_scores = np.max(np.vstack(unit_ensemble_scores), axis=0)
            labels = (np.max(np.vstack(unit_labels), axis=0) > 0).astype(np.uint8)
            # There is no single mathematically correct threshold for the union
            # of independent column-level ensembles, so record-level threshold is
            # intentionally left undefined. Column endpoints expose each real
            # threshold.
            final_threshold = float(np.max(unit_thresholds))
            final_thresholds = np.full(len(dataframe), np.nan, dtype=np.float64)

        ensemble = {
            "normalization": "min_max_per_model_per_unit",
            "formula": "N=(S-S_min)/(S_max-S_min)",
            "weight_formula": "W=B/sum(B)",
            "score_formula": "E=sum(W*N)",
            "threshold_formula": "T=quantile(E, 1-contamination)",
            "weights_sum": float(weights.sum()),
            "scores": final_scores,
            "threshold": final_threshold,
            "contamination": contamination,
        }
        score_source = (
            "All three fixed top-three PyOD detectors were trained independently. "
            "Each model's raw anomaly scores were normalized independently, then "
            "combined using normalized benchmark Combined Scores as ensemble weights."
        )
    else:
        output = model_outputs[0]
        final_scores = output["raw_scores"].copy()
        if approach == "multivariate":
            final_thresholds = np.full(len(dataframe), output["unit_results"][0]["threshold"])
            labels = output["unit_results"][0]["labels"].copy()
        else:
            unit_labels = np.vstack([u["labels"] for u in output["unit_results"]])
            unit_thresholds = np.vstack([
                np.full(len(dataframe), u["threshold"]) for u in output["unit_results"]
            ])
            labels = (unit_labels.max(axis=0) > 0).astype(np.uint8)
            winning_unit = np.argmax(
                np.where(unit_labels.astype(bool), unit_labels.astype(float), -1.0), axis=0
            )
            final_thresholds = np.max(
                np.where(unit_labels.astype(bool), unit_thresholds, -np.inf), axis=0
            )
            final_thresholds[~np.isfinite(final_thresholds)] = float(np.max(unit_thresholds))
            # When a record is normal in every column, the displayed threshold
            # is the largest unit threshold simply to keep the record table coherent.
        ensemble = None
        score_source = (
            f"Only the user-selected PyOD model {output['model']} was trained for Best Score detection."
        )

    anomaly_count = int(labels.sum())
    records = _record_score_table(
        dataframe, model_outputs, final_scores, final_thresholds, labels
    )

    return {
        "approach": approach,
        "score_method": score_method,
        "model_name": model_outputs[0]["model"] if score_method == "best_score" else None,
        "selected_model": model_outputs[0]["model"] if score_method == "best_score" else None,
        "models": [
            {
                "model": output["model"],
                "benchmark_combined_score": output["benchmark_combined_score"],
                "weight": output["weight"],
                "raw_min": output["raw_min"],
                "raw_max": output["raw_max"],
                "raw_score_direction": "Higher values are treated as more anomalous.",
                "unit_results": output["unit_results"],
            }
            for output in model_outputs
        ],
        "ensemble": ensemble,
        "total_records_processed": int(len(dataframe)),
        "anomaly_records_count": anomaly_count,
        "normal_record_count": int(len(dataframe) - anomaly_count),
        "anomaly_rate": 100.0 * anomaly_count / len(dataframe),
        "contamination": float(contamination),
        "records": records,
        "combined_labels": labels,
        "dataframe": dataframe,
        "columns": list(columns),
        "score_source": score_source,
        "scoring_batch_rows": SCORE_BATCH_ROWS,
    }
