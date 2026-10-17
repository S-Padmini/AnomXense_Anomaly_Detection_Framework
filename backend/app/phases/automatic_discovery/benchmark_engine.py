
from __future__ import annotations

import time
from typing import Any

import numpy as np

from app.phases.automatic_discovery.detection_engine import fit_score_batched
from app.phases.automatic_discovery.model_compatibility import get_available_models
from app.scoring.empirical_benchmark_scorer import (
    calculate_stability,
    jaccard_score,
    score_benchmarks,
)

BASE_SEED = 9100
REPEATS = 2
BENCHMARK_CONTAMINATION = 0.10
MAX_BENCHMARK_ROWS = 3000
MAX_UNIVARIATE_BENCHMARK_UNITS = 8


def evaluation_indices(n_rows: int, max_rows: int = MAX_BENCHMARK_ROWS) -> np.ndarray:
    if n_rows <= max_rows:
        return np.arange(n_rows, dtype=np.int64)
    rng = np.random.default_rng(BASE_SEED)
    return np.sort(rng.choice(n_rows, size=max_rows, replace=False)).astype(np.int64)


def _bounded_training_indices(
    n_rows: int,
    repeat: int,
    unit_index: int,
    model_name: str,
) -> np.ndarray:
    if model_name in {"KNN", "LOF"}:
        limit = 1200
    elif model_name == "CBLOF":
        limit = 2500
    else:
        limit = 2500

    sample_size = min(n_rows, limit)
    if sample_size == n_rows:
        return np.arange(n_rows, dtype=np.int64)

    rng = np.random.default_rng(
        BASE_SEED + unit_index * 101 + repeat * 1009
    )
    return np.sort(
        rng.choice(n_rows, size=sample_size, replace=False)
    ).astype(np.int64)


def _fixed_top_three(
    rows: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    eligible = [
        row for row in rows
        if int(row.get("successful_runs", 0)) > 0
        and row.get("combined_score") is not None
        and np.isfinite(float(row["combined_score"]))
    ]
    eligible.sort(
        key=lambda row: (
            float(row.get("combined_score") or 0.0),
            float(row.get("best_score") or 0.0),
            float(row.get("reliability_score") or 0.0),
            -float(row.get("runtime_ms") or 0.0),
            str(row.get("model", "")),
        ),
        reverse=True,
    )
    selected = eligible[:limit]
    for position, row in enumerate(selected, start=1):
        row["fixed_recommendation_rank"] = position
    return selected


def _successful_rows_only(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if int(row.get("successful_runs", 0)) > 0
    ]


def run_benchmark(units: list[dict[str, Any]]) -> dict[str, Any]:
    if not units:
        raise ValueError("No compatible analysis units are available.")

    n_rows = len(units[0]["X"])
    if n_rows < 5:
        raise ValueError("At least five records are required for benchmarking.")
    if any(len(unit["X"]) != n_rows for unit in units):
        raise ValueError("All benchmark units must contain the same number of rows.")

    available, unavailable = get_available_models()
    attempted_per_model = len(units) * REPEATS
    rows: list[dict[str, Any]] = []
    predictions: dict[str, dict[str, np.ndarray]] = {
        str(unit["unit"]): {} for unit in units
    }
    errors: list[dict[str, str]] = list(unavailable)

    for model_name in available:
        runtimes: list[float] = []
        stability_values: list[float] = []
        successful_runs = 0

        for unit_index, unit in enumerate(units):
            X = np.asarray(unit["X"], dtype=np.float64)
            run_labels: list[np.ndarray] = []

            for repeat in range(REPEATS):
                started = time.perf_counter()
                try:
                    train_idx = _bounded_training_indices(
                        len(X), repeat, unit_index, model_name
                    )
                    _, _, labels, _, _ = fit_score_batched(
                        model_name,
                        X,
                        BENCHMARK_CONTAMINATION,
                        training_indices=train_idx,
                        random_seed=BASE_SEED + unit_index * 101 + repeat * 1009,
                    )
                    run_labels.append(labels.astype(bool, copy=False))
                    runtimes.append(
                        (time.perf_counter() - started) * 1000.0
                    )
                    successful_runs += 1
                except Exception as exc:
                    errors.append(
                        {
                            "model": model_name,
                            "unit": str(unit["unit"]),
                            "repeat": str(repeat + 1),
                            "reason": f"{type(exc).__name__}: {exc}"[:500],
                        }
                    )

            if len(run_labels) >= 2:
                value = calculate_stability(run_labels)
                if value is not None:
                    stability_values.append(value)

            if run_labels:
                predictions[str(unit["unit"])][model_name] = (
                    np.mean(np.vstack(run_labels), axis=0) > 0.5
                )
            del X

        rows.append(
            {
                "model": model_name,
                "attempted_runs": attempted_per_model,
                "successful_runs": successful_runs,
                "runtime_ms": (
                    float(np.mean(runtimes)) if runtimes else None
                ),
                "stability_score": (
                    float(np.mean(stability_values))
                    if stability_values else None
                ),
                "agreement_score": None,
                "reliability_score": (
                    successful_runs / max(attempted_per_model, 1)
                ),
            }
        )

    for row in rows:
        agreements: list[float] = []
        for unit in units:
            per_model = predictions[str(unit["unit"])]
            own = per_model.get(row["model"])
            others = [
                value
                for name, value in per_model.items()
                if name != row["model"]
            ]
            if own is None or not others:
                continue
            consensus = np.mean(np.vstack(others), axis=0) > 0.5
            agreements.append(jaccard_score(own, consensus))
        row["agreement_score"] = (
            float(np.mean(agreements)) if agreements else None
        )

    successful_rows = _successful_rows_only(rows)
    if not successful_rows:
        reasons = "; ".join(
            f"{item.get('model')}: {item.get('reason')}"
            for item in errors[:10]
        )
        raise RuntimeError(
            "No compatible PyOD model completed a benchmark run successfully. "
            + reasons
        )

    scored = score_benchmarks(successful_rows)
    scored = [
        row for row in scored
        if row.get("combined_score") is not None
        and np.isfinite(float(row["combined_score"]))
        and float(row["combined_score"]) >= 0.0
    ]
    if not scored:
        raise RuntimeError(
            "The benchmark completed, but no model received a valid empirical score."
        )

    fixed_top_three = _fixed_top_three(scored, 3)
    if len(fixed_top_three) < 3:
        raise RuntimeError(
            "At least three successfully benchmarked models are required "
            "for the Automatic Discovery ensemble."
        )

    return {
        "benchmark_method": (
            "Dataset-specific empirical benchmark on a deterministic "
            "bounded sample"
        ),
        "benchmark_rows": n_rows,
        "benchmark_units": [str(unit["unit"]) for unit in units],
        "benchmark_contamination": BENCHMARK_CONTAMINATION,
        "repeats_per_model_per_unit": REPEATS,
        "results": scored,
        "top_three_recommendations": fixed_top_three,
        "metrics": {
            "weights": {
                "stability_score": 0.40,
                "agreement_score": 0.30,
                "speed_score": 0.20,
                "reliability_score": 0.10,
            },
            "fixed_recommendation_rule": (
                "The top-three membership and order are established once "
                "from the dataset-specific empirical Combined Score. "
                "The score-method selector does not rerank or replace the "
                "fixed three recommended models."
            ),
            "best_score_definition": (
                "Overall empirical benchmark score calculated from stability, "
                "agreement, speed, and reliability. Stability remains available "
                "separately as stability_score. Best Score is used for single-model "
                "detection, while Combined Score uses the fixed top three models "
                "as an ensemble."
            ),
            "combined_score_definition": (
                "Weighted mean of available benchmark metrics; weights are "
                "renormalized when a metric is unavailable."
            ),
            "ensemble_weight_definition": (
                "For final ensemble detection, each fixed top-three model's "
                "benchmark Combined Score B is converted to W=B/sum(B)."
            ),
            "warning": (
                "No ground-truth anomaly labels are used. Benchmark scores "
                "are model-selection signals, not accuracy, precision, "
                "recall, or proof that an individual record is anomalous."
            ),
            "sampling_note": (
                "Large datasets use deterministic bounded benchmark samples. "
                "Final detection scores every selected Phase-3 record in "
                "batches. Univariate fits each selected column independently; "
                "multivariate fits all selected columns jointly."
            ),
        },
        "errors": errors[:100],
    }
