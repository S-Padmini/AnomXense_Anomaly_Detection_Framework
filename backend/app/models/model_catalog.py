from __future__ import annotations

"""
Phase 5 model catalog.

Contains ONLY model metadata.
It does not decide which model wins.

The actual recommendation is produced by:
    statistical_scorer.py
    objective_scorer.py
    phase5_service.py
"""

MODEL_CATALOG = [
    {
        "name": "ECOD",
        "display_name": "ECOD",
        "category": "Tabular",
        "description": (
            "Empirical Cumulative Distribution-based Outlier Detection. "
            "A statistical detector that evaluates how unusual observations "
            "are within individual feature distributions."
        ),
        "strengths": [
            "Works well with numerical tabular data",
            "Distribution-aware",
            "Simple and interpretable",
            "Does not require cluster labels",
        ],
        "limitations": [
            "Primarily suited to numerical features",
            "Does not explicitly model complex temporal sequences",
        ],
        "capabilities": {
            "distribution": 0.95,
            "extreme_values": 0.90,
            "scale": 0.70,
            "correlation": 0.45,
            "clusters": 0.30,
            "local_density": 0.35,
            "temporal_structure": 0.10,
            "time_series_pattern": 0.10,
            "mixed_features": 0.35,
            "small_data": 0.90,
        },
    },
    {
        "name": "IForest",
        "display_name": "Isolation Forest (IForest)",
        "category": "Tabular",
        "description": (
            "Isolation Forest isolates observations using randomized "
            "partitioning and is effective for general-purpose tabular "
            "anomaly detection."
        ),
        "strengths": [
            "General-purpose tabular detector",
            "Handles nonlinear relationships",
            "Works well with moderate and large datasets",
            "Useful for multidimensional anomalies",
        ],
        "limitations": [
            "Less directly interpretable than purely distributional methods",
            "Usually benefits from numerical feature representation",
        ],
        "capabilities": {
            "distribution": 0.65,
            "extreme_values": 0.80,
            "scale": 0.65,
            "correlation": 0.75,
            "clusters": 0.75,
            "local_density": 0.60,
            "temporal_structure": 0.15,
            "time_series_pattern": 0.15,
            "mixed_features": 0.55,
            "small_data": 0.60,
        },
    },
    {
        "name": "COPOD",
        "display_name": "COPOD",
        "category": "Tabular",
        "description": (
            "Copula-Based Outlier Detection. Uses feature-wise empirical "
            "distributions and tail probabilities to identify unusual "
            "observations."
        ),
        "strengths": [
            "Strong distributional interpretation",
            "Good for tail and extreme observations",
            "Fast for numerical tabular data",
        ],
        "limitations": [
            "Primarily numerical",
            "Does not explicitly model temporal sequences",
        ],
        "capabilities": {
            "distribution": 0.98,
            "extreme_values": 0.95,
            "scale": 0.70,
            "correlation": 0.55,
            "clusters": 0.25,
            "local_density": 0.30,
            "temporal_structure": 0.10,
            "time_series_pattern": 0.10,
            "mixed_features": 0.35,
            "small_data": 0.85,
        },
    },
    {
        "name": "KNN",
        "display_name": "KNN",
        "category": "Tabular",
        "description": (
            "K-nearest-neighbor anomaly detection. Observations that are "
            "far from their nearest neighbors can receive higher anomaly "
            "scores."
        ),
        "strengths": [
            "Neighborhood-aware",
            "Useful when local structure matters",
            "Can identify isolated observations",
        ],
        "limitations": [
            "Sensitive to feature scaling",
            "Distance calculations can become expensive",
        ],
        "capabilities": {
            "distribution": 0.45,
            "extreme_values": 0.65,
            "scale": 0.95,
            "correlation": 0.70,
            "clusters": 0.80,
            "local_density": 0.98,
            "temporal_structure": 0.10,
            "time_series_pattern": 0.10,
            "mixed_features": 0.40,
            "small_data": 0.70,
        },
    },
    {
        "name": "LOF",
        "display_name": "LOF",
        "category": "Tabular",
        "description": (
            "Local Outlier Factor compares the local density of observations "
            "with the density of their neighboring observations."
        ),
        "strengths": [
            "Strong local-density modeling",
            "Useful for contextual and local anomalies",
            "Effective when normal observations form heterogeneous regions",
        ],
        "limitations": [
            "Sensitive to neighborhood configuration",
            "Sensitive to feature scaling",
        ],
        "capabilities": {
            "distribution": 0.45,
            "extreme_values": 0.60,
            "scale": 0.95,
            "correlation": 0.70,
            "clusters": 0.90,
            "local_density": 1.00,
            "temporal_structure": 0.10,
            "time_series_pattern": 0.10,
            "mixed_features": 0.40,
            "small_data": 0.65,
        },
    },
    {
        "name": "CBLOF",
        "display_name": "CBLOF",
        "category": "Tabular",
        "description": (
            "Cluster-Based Local Outlier Factor. Uses cluster structure "
            "and distance from representative clusters to identify anomalies."
        ),
        "strengths": [
            "Useful when cluster structure exists",
            "Can detect observations distant from normal clusters",
            "Works well with structured numerical data",
        ],
        "limitations": [
            "Depends on meaningful cluster structure",
            "Sensitive to preprocessing and scaling",
        ],
        "capabilities": {
            "distribution": 0.40,
            "extreme_values": 0.55,
            "scale": 0.90,
            "correlation": 0.75,
            "clusters": 1.00,
            "local_density": 0.75,
            "temporal_structure": 0.10,
            "time_series_pattern": 0.10,
            "mixed_features": 0.35,
            "small_data": 0.55,
        },
    },
    {
        "name": "HBOS",
        "display_name": "HBOS",
        "category": "Tabular",
        "description": (
            "Histogram-Based Outlier Score. Estimates feature distributions "
            "using histograms and identifies observations occupying unusual "
            "regions."
        ),
        "strengths": [
            "Fast",
            "Distribution-aware",
            "Useful for large numerical datasets",
            "Easy to interpret",
        ],
        "limitations": [
            "Primarily distribution-based",
            "Less effective for complex multivariate relationships",
        ],
        "capabilities": {
            "distribution": 0.98,
            "extreme_values": 0.90,
            "scale": 0.70,
            "correlation": 0.35,
            "clusters": 0.30,
            "local_density": 0.35,
            "temporal_structure": 0.10,
            "time_series_pattern": 0.10,
            "mixed_features": 0.30,
            "small_data": 0.80,
        },
    },
    {
        "name": "MatrixProfile",
        "display_name": "MatrixProfile",
        "category": "Time Series",
        "description": (
            "A time-series method for identifying unusual subsequences and "
            "discord-like behavior in ordered temporal data."
        ),
        "strengths": [
            "Designed for temporal sequences",
            "Useful for subsequence anomalies",
            "Can detect unusual temporal patterns",
        ],
        "limitations": [
            "Requires meaningful ordered time-series data",
            "Not intended as a general tabular detector",
        ],
        "capabilities": {
            "distribution": 0.25,
            "extreme_values": 0.35,
            "scale": 0.40,
            "correlation": 0.40,
            "clusters": 0.20,
            "local_density": 0.20,
            "temporal_structure": 1.00,
            "time_series_pattern": 1.00,
            "mixed_features": 0.10,
            "small_data": 0.25,
        },
    },
    {
        "name": "SpectralResidual",
        "display_name": "SpectralResidual",
        "category": "Time Series",
        "description": (
            "A spectral-residual time-series anomaly detector that identifies "
            "unusual points from their spectral characteristics."
        ),
        "strengths": [
            "Designed for time-series anomaly detection",
            "Useful for unusual temporal signals",
            "Can detect deviations in sequential behavior",
        ],
        "limitations": [
            "Requires meaningful temporal ordering",
            "Not a general-purpose tabular detector",
        ],
        "capabilities": {
            "distribution": 0.20,
            "extreme_values": 0.35,
            "scale": 0.35,
            "correlation": 0.30,
            "clusters": 0.15,
            "local_density": 0.15,
            "temporal_structure": 0.95,
            "time_series_pattern": 0.95,
            "mixed_features": 0.10,
            "small_data": 0.25,
        },
    },
    {
        "name": "KShape",
        "display_name": "KShape",
        "category": "Time Series",
        "description": (
            "A shape-based clustering method for time-series data. It can "
            "help identify unusual sequence shapes by comparing temporal "
            "patterns."
        ),
        "strengths": [
            "Shape-aware time-series analysis",
            "Useful when multiple time-series patterns exist",
            "Can identify unusual temporal behavior",
        ],
        "limitations": [
            "Requires sufficiently structured time-series data",
            "Not intended for ordinary tabular anomaly detection",
        ],
        "capabilities": {
            "distribution": 0.15,
            "extreme_values": 0.25,
            "scale": 0.35,
            "correlation": 0.35,
            "clusters": 0.80,
            "local_density": 0.25,
            "temporal_structure": 0.95,
            "time_series_pattern": 1.00,
            "mixed_features": 0.05,
            "small_data": 0.20,
        },
    },
]


def get_model_catalog() -> list[dict]:
    return MODEL_CATALOG.copy()


def get_model(name: str) -> dict | None:
    for model in MODEL_CATALOG:
        if model["name"].lower() == str(name).lower():
            return model
    return None