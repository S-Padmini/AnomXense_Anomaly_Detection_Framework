from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phases.phase6.detection_engine import _build_features, _import_model_class

# Keep a neutral candidate catalogue: every importable candidate receives the
# same bounded benchmark protocol. A model is omitted only when unavailable or
# when its fit/score operation fails during empirical benchmarking.
MODEL_NAMES = ("ECOD", "IForest", "COPOD", "KNN", "LOF", "CBLOF", "HBOS")


def build_analysis_units(
    dataframe: pd.DataFrame,
    approach: str,
    columns: list[str],
) -> list[dict[str, Any]]:
    if dataframe is None or len(dataframe) == 0:
        raise ValueError("No preprocessed records are available.")
    if not columns:
        raise ValueError("Select at least one feature.")
    missing = [column for column in columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Selected features are missing from Phase 3 data: {missing}")
    if approach not in {"univariate", "multivariate"}:
        raise ValueError("Approach must be univariate or multivariate.")

    if approach == "multivariate":
        matrix = _build_features(dataframe, columns)
        X = np.asarray(matrix.X, dtype=np.float32)
        _validate_matrix(X, len(dataframe), "multivariate features")
        return [{"unit": "__multivariate__", "columns": list(columns), "X": X}]

    units: list[dict[str, Any]] = []
    for column in columns:
        matrix = _build_features(dataframe, [column])
        X = np.asarray(matrix.X, dtype=np.float32)
        _validate_matrix(X, len(dataframe), f"column {column!r}")
        units.append({"unit": str(column), "columns": [column], "X": X})
    return units


def get_available_models() -> tuple[list[str], list[dict[str, str]]]:
    available: list[str] = []
    unavailable: list[dict[str, str]] = []
    for name in MODEL_NAMES:
        try:
            cls = _import_model_class(name)
            if not str(getattr(cls, "__module__", "")).startswith("pyod."):
                raise ImportError("Resolved class is not a PyOD estimator.")
            available.append(name)
        except Exception as exc:
            unavailable.append({
                "model": name,
                "reason": f"{type(exc).__name__}: {exc}"[:300],
            })
    if not available:
        raise RuntimeError(
            "No supported PyOD models are importable. Install PyOD in the active backend environment."
        )
    return available, unavailable


def _validate_matrix(X: np.ndarray, expected_rows: int, label: str) -> None:
    if X.ndim != 2 or X.shape[0] != expected_rows or X.shape[1] == 0:
        raise ValueError(f"Feature preparation returned an invalid matrix for {label}.")
    for start in range(0, len(X), 65536):
        if not np.isfinite(X[start:start + 65536]).all():
            raise ValueError(f"Feature preparation produced non-finite values for {label}.")
