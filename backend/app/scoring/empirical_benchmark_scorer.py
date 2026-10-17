from __future__ import annotations

import numpy as np


# =========================================================
# BENCHMARK METRIC WEIGHTS
# =========================================================
#
# Combined Score uses all four benchmark metrics.
#
# Stability    -> 40%
# Agreement    -> 30%
# Speed        -> 20%
# Reliability  -> 10%
#
# If one metric is unavailable, the available weights
# are automatically renormalized.
#

WEIGHTS = {
    "stability_score": 0.40,
    "agreement_score": 0.30,
    "speed_score": 0.20,
    "reliability_score": 0.10,
}


# =========================================================
# JACCARD SCORE
# =========================================================

def jaccard_score(first, second) -> float:
    """
    Calculate Jaccard similarity between two binary
    anomaly-label arrays.

    Jaccard =
        intersection / union

    If both arrays contain no anomalies, return 0.0
    instead of treating them as a perfect agreement.
    """

    first = np.asarray(
        first,
        dtype=bool,
    )

    second = np.asarray(
        second,
        dtype=bool,
    )

    union = int(
        np.logical_or(
            first,
            second,
        ).sum()
    )

    if union == 0:
        return 0.0

    intersection = int(
        np.logical_and(
            first,
            second,
        ).sum()
    )

    return float(
        intersection / union
    )


# =========================================================
# STABILITY SCORE
# =========================================================

def calculate_stability(
    label_runs: list[np.ndarray],
) -> float | None:
    """
    Measure how consistently a model produces the same
    anomaly labels across repeated benchmark runs.

    Higher value = more stable.

    Stability is calculated using the average pairwise
    Jaccard similarity between repeated runs.
    """

    if len(label_runs) < 2:
        return None

    values = [
        jaccard_score(
            label_runs[i],
            label_runs[j],
        )
        for i in range(len(label_runs))
        for j in range(
            i + 1,
            len(label_runs),
        )
    ]

    return (
        float(np.mean(values))
        if values
        else None
    )


# =========================================================
# BENCHMARK SCORE CALCULATION
# =========================================================

def score_benchmarks(
    rows: list[dict],
) -> list[dict]:
    """
    Calculate the four benchmark metrics and the two
    final benchmark scores for every model.

    Four metrics:

        1. Stability
        2. Agreement
        3. Speed
        4. Reliability

    Best Score:

        The strongest individual benchmark metric
        achieved by the model.

        Best Score =
            max(
                Stability,
                Agreement,
                Speed,
                Reliability
            )

    Combined Score:

        Weighted combination of all available metrics.

        Combined Score =
            0.40 * Stability
          + 0.30 * Agreement
          + 0.20 * Speed
          + 0.10 * Reliability

        If a metric is unavailable, its weight is
        removed and the remaining weights are
        renormalized.

    IMPORTANT:

    Best Score and Combined Score are intentionally
    different measures.

    Best Score answers:
        "What is the strongest individual benchmark
         characteristic of this model?"

    Combined Score answers:
        "How strong is this model when all benchmark
         characteristics are considered together?"
    """

    # -----------------------------------------------------
    # Find models with usable runtime information.
    # -----------------------------------------------------

    successful = [
        row
        for row in rows
        if int(
            row.get(
                "successful_runs",
                0,
            )
        ) > 0
        and row.get(
            "runtime_ms"
        ) is not None
        and np.isfinite(
            float(
                row["runtime_ms"]
            )
        )
    ]

    # -----------------------------------------------------
    # If no successful benchmark has a valid runtime,
    # score calculation cannot be performed.
    # -----------------------------------------------------

    if not successful:
        for row in rows:
            row.update(
                {
                    "speed_score": None,
                    "combined_score": None,
                    "best_score": None,
                }
            )

        return rows

    # -----------------------------------------------------
    # Runtime range used for speed normalization.
    #
    # Faster model -> higher speed score.
    # -----------------------------------------------------

    runtimes = [
        max(
            float(
                row["runtime_ms"]
            ),
            0.0,
        )
        for row in successful
    ]

    minimum = min(runtimes)
    maximum = max(runtimes)

    successful_ids = {
        id(row)
        for row in successful
    }

    # -----------------------------------------------------
    # Calculate scores for every model.
    # -----------------------------------------------------

    for row in rows:

        # -------------------------------------------------
        # Models without successful benchmark runs
        # receive no score.
        # -------------------------------------------------

        if id(row) not in successful_ids:

            row.update(
                {
                    "speed_score": None,
                    "combined_score": None,
                    "best_score": None,
                }
            )

            continue

        # =================================================
        # 1. SPEED SCORE
        # =================================================
        #
        # Fastest model gets 1.0.
        # Slowest model gets 0.0.
        #
        # If all models have the same runtime,
        # every model receives 1.0.
        #

        runtime = max(
            float(
                row["runtime_ms"]
            ),
            0.0,
        )

        if maximum == minimum:

            row["speed_score"] = 1.0

        else:

            row["speed_score"] = (
                1.0
                - (
                    runtime
                    - minimum
                )
                / (
                    maximum
                    - minimum
                )
            )

        # =================================================
        # 2. RELIABILITY SCORE
        # =================================================
        #
        # Reliability =
        #
        # successful runs
        # ----------------
        # attempted runs
        #

        row["reliability_score"] = (
            float(
                row.get(
                    "successful_runs",
                    0,
                )
            )
            /
            max(
                int(
                    row.get(
                        "attempted_runs",
                        0,
                    )
                ),
                1,
            )
        )

        # =================================================
        # 3. COLLECT THE FOUR METRICS
        # =================================================

        metrics = {
            key: row.get(key)
            for key in WEIGHTS
        }

        # -------------------------------------------------
        # Keep only finite, available metric values.
        # -------------------------------------------------

        available = {
            key: float(value)
            for key, value in metrics.items()
            if value is not None
            and np.isfinite(
                float(value)
            )
        }

        # =================================================
        # 4. COMBINED SCORE
        # =================================================
        #
        # Weighted combination:
        #
        # Stability   -> 40%
        # Agreement   -> 30%
        # Speed       -> 20%
        # Reliability -> 10%
        #
        # Missing metrics are excluded and the remaining
        # weights are renormalized.
        #

        available_weight = sum(
            WEIGHTS[key]
            for key in available
        )

        if available_weight:

            row["combined_score"] = (
                sum(
                    available[key]
                    * WEIGHTS[key]
                    for key in available
                )
                /
                available_weight
            )

        else:

            row["combined_score"] = None

        # =================================================
        # 5. BEST SCORE
        # =================================================
        #
        # Best Score is the strongest individual benchmark
        # metric among the four available metrics.
        #
        # This is intentionally different from Combined
        # Score.
        #

        if available:

            row["best_score"] = max(
                available.values()
            )

        else:

            row["best_score"] = None

    return rows


# =========================================================
# RANK MODELS
# =========================================================

def rank_models(
    rows: list[dict],
    method: str,
) -> list[dict]:
    """
    Rank models using the requested benchmark score.

    method:
        "best_score"
        "combined_score"

    This function is available for score-specific ranking,
    but Automatic Discovery recommendation membership/order
    is fixed separately by fixed_recommendations().
    """

    if method not in {
        "best_score",
        "combined_score",
    }:

        raise ValueError(
            "score_method must be "
            "'best_score' or "
            "'combined_score'."
        )

    ranked = [
        dict(row)
        for row in rows
        if row.get(method) is not None
        and int(
            row.get(
                "successful_runs",
                0,
            )
        ) > 0
    ]

    ranked.sort(
        key=lambda row: (
            float(
                row[method]
            ),
            float(
                row.get(
                    "reliability_score",
                    0.0,
                )
                or 0.0
            ),
            -float(
                row.get(
                    "runtime_ms",
                    0.0,
                )
                or 0.0
            ),
            str(
                row.get(
                    "model",
                    "",
                )
            ),
        ),
        reverse=True,
    )

    for position, row in enumerate(
        ranked,
        start=1,
    ):

        row["rank"] = position

        row["display_score"] = float(
            row[method]
        )

    return ranked


# =========================================================
# FIXED RECOMMENDATIONS
# =========================================================

def fixed_recommendations(
    rows: list[dict],
    limit: int = 3,
) -> list[dict]:
    """
    Return the fixed Top-3 recommendation list.

    IMPORTANT:

    Automatic Discovery fixes recommendation membership
    and order using Combined Score.

    Therefore:

        Best Score selector
        -------------------
        changes only the displayed score.

        Combined Score selector
        -----------------------
        changes only the displayed score.

    The Top-3 models themselves do NOT change.
    """

    ranked = rank_models(
        rows,
        "combined_score",
    )

    return ranked[
        : max(
            0,
            int(limit),
        )
    ]