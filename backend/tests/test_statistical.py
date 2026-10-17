from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.phases.statistical.explainability import (
    MahalanobisExplainability,
)
from app.phases.statistical.multivariate import (
    MultivariateDetector,
)
from app.phases.statistical.univariate import (
    UnivariateDetector,
)


# ======================================================================
# Test data
# ======================================================================


@pytest.fixture
def sample_preprocessed_data() -> pd.DataFrame:
    """
    Small dataframe representing Phase 3 preprocessed data.

    The tests intentionally use generic feature names so that the
    implementation cannot depend on the current project dataset.
    """

    return pd.DataFrame(
        {
            "feature_a": [
                10.0,
                11.0,
                12.0,
                13.0,
                14.0,
                100.0,
            ],
            "feature_b": [
                20.0,
                21.0,
                22.0,
                23.0,
                24.0,
                25.0,
            ],
            "feature_c": [
                100.0,
                101.0,
                102.0,
                103.0,
                104.0,
                105.0,
            ],
        }
    )


@pytest.fixture
def simple_univariate_data() -> pd.DataFrame:
    """
    Dataset with an obvious IQR anomaly.
    """

    return pd.DataFrame(
        {
            "amount": [
                10.0,
                11.0,
                12.0,
                13.0,
                14.0,
                100.0,
            ],
            "quantity": [
                1.0,
                2.0,
                2.0,
                3.0,
                3.0,
                4.0,
            ],
        }
    )


# ======================================================================
# Univariate tests
# ======================================================================


def test_univariate_detects_numeric_columns(
    simple_univariate_data: pd.DataFrame,
):
    detector = UnivariateDetector(
        simple_univariate_data
    )

    columns = detector.get_eligible_columns()

    assert "amount" in columns
    assert "quantity" in columns


def test_univariate_excludes_boolean_columns():
    dataframe = pd.DataFrame(
        {
            "amount": [
                10.0,
                11.0,
                12.0,
                13.0,
            ],
            "is_active": [
                True,
                True,
                False,
                True,
            ],
        }
    )

    detector = UnivariateDetector(
        dataframe
    )

    columns = detector.get_eligible_columns()

    assert "amount" in columns
    assert "is_active" not in columns


def test_univariate_calculates_iqr_boundaries(
    simple_univariate_data: pd.DataFrame,
):
    detector = UnivariateDetector(
        simple_univariate_data
    )

    result = detector.detect_column(
        "amount"
    )

    assert result["method_used"] == "IQR"

    assert result["q1"] == pytest.approx(
        simple_univariate_data["amount"].quantile(
            0.25
        )
    )

    assert result["q3"] == pytest.approx(
        simple_univariate_data["amount"].quantile(
            0.75
        )
    )

    expected_iqr = (
        result["q3"] - result["q1"]
    )

    assert result["iqr"] == pytest.approx(
        expected_iqr
    )

    assert result["lower_boundary"] == pytest.approx(
        result["q1"] - 1.5 * expected_iqr
    )

    assert result["upper_boundary"] == pytest.approx(
        result["q3"] + 1.5 * expected_iqr
    )


def test_univariate_detects_outside_boundary_record(
    simple_univariate_data: pd.DataFrame,
):
    detector = UnivariateDetector(
        simple_univariate_data
    )

    result = detector.detect_column(
        "amount"
    )

    anomaly_records = [
        record
        for record in result["records"]
        if record["is_anomaly"]
    ]

    assert len(anomaly_records) > 0

    assert any(
        record["column_value"] == 100.0
        for record in anomaly_records
    )


def test_univariate_record_reason_is_dynamic(
    simple_univariate_data: pd.DataFrame,
):
    detector = UnivariateDetector(
        simple_univariate_data
    )

    result = detector.detect_column(
        "amount"
    )

    anomaly_record = next(
        record
        for record in result["records"]
        if record["column_value"] == 100.0
    )

    assert anomaly_record["status"] == "Anomaly"

    assert "100" in anomaly_record["reason"]

    assert (
        str(result["upper_boundary"])
        in anomaly_record["reason"]
    )


def test_univariate_normal_record_has_dynamic_reason(
    simple_univariate_data: pd.DataFrame,
):
    detector = UnivariateDetector(
        simple_univariate_data
    )

    result = detector.detect_column(
        "amount"
    )

    normal_record = next(
        record
        for record in result["records"]
        if record["column_value"] == 10.0
        and not record["is_anomaly"]
    )

    assert normal_record["status"] == "Normal"

    assert "10" in normal_record["reason"]

    assert (
        str(result["lower_boundary"])
        in normal_record["reason"]
        or str(result["upper_boundary"])
        in normal_record["reason"]
    )


def test_univariate_summary_matches_column_results(
    simple_univariate_data: pd.DataFrame,
):
    detector = UnivariateDetector(
        simple_univariate_data
    )

    summary = detector.build_summary()
    results = detector.detect_all_columns()

    assert len(summary) == len(results)

    for summary_item, result in zip(
        summary,
        results,
    ):
        assert (
            summary_item["column_name"]
            == result["column_name"]
        )

        assert (
            summary_item["total_anomaly_records"]
            == result["anomaly_records"]
        )

        assert (
            summary_item["anomaly_percentage"]
            == result["anomaly_percentage"]
        )


# ======================================================================
# Multivariate tests
# ======================================================================


def test_multivariate_uses_all_usable_features(
    sample_preprocessed_data: pd.DataFrame,
):
    detector = MultivariateDetector(
        sample_preprocessed_data
    )

    result = detector.detect()

    assert result["method_used"] == (
        "Mahalanobis Distance"
    )

    assert "feature_a" in result[
        "columns_involved"
    ]

    assert "feature_b" in result[
        "columns_involved"
    ]

    assert "feature_c" in result[
        "columns_involved"
    ]


def test_multivariate_returns_one_score_per_record(
    sample_preprocessed_data: pd.DataFrame,
):
    detector = MultivariateDetector(
        sample_preprocessed_data
    )

    result = detector.detect()

    assert len(
        result["records"]
    ) == len(
        sample_preprocessed_data
    )

    for record in result["records"]:
        assert "mah_distance" in record
        assert "threshold" in record
        assert "status" in record


def test_multivariate_scores_are_non_negative(
    sample_preprocessed_data: pd.DataFrame,
):
    detector = MultivariateDetector(
        sample_preprocessed_data
    )

    result = detector.detect()

    for record in result["records"]:
        assert record["mah_distance"] >= 0


def test_multivariate_threshold_is_positive(
    sample_preprocessed_data: pd.DataFrame,
):
    detector = MultivariateDetector(
        sample_preprocessed_data
    )

    result = detector.detect()

    assert result["threshold"] > 0


def test_multivariate_status_matches_threshold(
    sample_preprocessed_data: pd.DataFrame,
):
    detector = MultivariateDetector(
        sample_preprocessed_data
    )

    result = detector.detect()

    threshold = result["threshold"]

    for record in result["records"]:
        expected_status = (
            "Anomaly"
            if record["mah_distance"] > threshold
            else "Normal"
        )

        assert (
            record["status"]
            == expected_status
        )

        assert (
            record["is_anomaly"]
            == (
                record["mah_distance"]
                > threshold
            )
        )


def test_multivariate_counts_match_records(
    sample_preprocessed_data: pd.DataFrame,
):
    detector = MultivariateDetector(
        sample_preprocessed_data
    )

    result = detector.detect()

    anomaly_count = sum(
        record["is_anomaly"]
        for record in result["records"]
    )

    normal_count = sum(
        not record["is_anomaly"]
        for record in result["records"]
    )

    assert (
        result["anomaly_records"]
        == anomaly_count
    )

    assert (
        result["normal_records"]
        == normal_count
    )


def test_multivariate_percentage_matches_count(
    sample_preprocessed_data: pd.DataFrame,
):
    detector = MultivariateDetector(
        sample_preprocessed_data
    )

    result = detector.detect()

    expected_percentage = (
        result["anomaly_records"]
        / result["total_records"]
    ) * 100

    assert result[
        "anomaly_percentage"
    ] == pytest.approx(
        round(
            expected_percentage,
            2,
        )
    )


def test_multivariate_interpretation_is_dynamic(
    sample_preprocessed_data: pd.DataFrame,
):
    detector = MultivariateDetector(
        sample_preprocessed_data
    )

    result = detector.detect()

    for record in result["records"]:
        assert str(
            record["mah_distance"]
        ) in record[
            "interpretation"
        ]

        assert str(
            record["threshold"]
        ) in record[
            "interpretation"
        ]


# ======================================================================
# Constant feature tests
# ======================================================================


def test_multivariate_excludes_constant_features():
    dataframe = pd.DataFrame(
        {
            "variable_feature": [
                10.0,
                11.0,
                12.0,
                13.0,
                14.0,
            ],
            "constant_feature": [
                5.0,
                5.0,
                5.0,
                5.0,
                5.0,
            ],
        }
    )

    detector = MultivariateDetector(
        dataframe
    )

    result = detector.detect()

    assert "variable_feature" in result[
        "columns_involved"
    ]

    assert "constant_feature" in result[
        "constant_columns_excluded"
    ]


# ======================================================================
# Multivariate explainability tests
# ======================================================================


def test_explainability_returns_top_three_features(
    sample_preprocessed_data: pd.DataFrame,
):
    used_columns = list(
        sample_preprocessed_data.columns
    )

    explainer = MahalanobisExplainability(
        dataframe=sample_preprocessed_data,
        used_columns=used_columns,
    )

    explanation = explainer.explain_record(
        record_number=1,
        top_n=3,
    )

    assert len(
        explanation["feature_contributions"]
    ) == 3


def test_explainability_feature_names_are_dynamic(
    sample_preprocessed_data: pd.DataFrame,
):
    used_columns = list(
        sample_preprocessed_data.columns
    )

    explainer = MahalanobisExplainability(
        dataframe=sample_preprocessed_data,
        used_columns=used_columns,
    )

    explanation = explainer.explain_record(
        record_number=1,
        top_n=3,
    )

    returned_names = {
        item["feature_name"]
        for item in explanation[
            "feature_contributions"
        ]
    }

    assert returned_names.issubset(
        set(used_columns)
    )


def test_explainability_ranks_contributions(
    sample_preprocessed_data: pd.DataFrame,
):
    used_columns = list(
        sample_preprocessed_data.columns
    )

    explainer = MahalanobisExplainability(
        dataframe=sample_preprocessed_data,
        used_columns=used_columns,
    )

    explanation = explainer.explain_record(
        record_number=1,
        top_n=3,
    )

    contributions = [
        item["absolute_contribution"]
        for item in explanation[
            "feature_contributions"
        ]
    ]

    assert contributions == sorted(
        contributions,
        reverse=True,
    )


def test_explainability_rank_values_are_sequential(
    sample_preprocessed_data: pd.DataFrame,
):
    used_columns = list(
        sample_preprocessed_data.columns
    )

    explainer = MahalanobisExplainability(
        dataframe=sample_preprocessed_data,
        used_columns=used_columns,
    )

    explanation = explainer.explain_record(
        record_number=1,
        top_n=3,
    )

    ranks = [
        item["rank"]
        for item in explanation[
            "feature_contributions"
        ]
    ]

    assert ranks == [1, 2, 3]


def test_explainability_percentage_is_valid(
    sample_preprocessed_data: pd.DataFrame,
):
    used_columns = list(
        sample_preprocessed_data.columns
    )

    explainer = MahalanobisExplainability(
        dataframe=sample_preprocessed_data,
        used_columns=used_columns,
    )

    explanation = explainer.explain_record(
        record_number=1,
        top_n=3,
    )

    for item in explanation[
        "feature_contributions"
    ]:
        assert (
            0 <= item[
                "contribution_percentage"
            ] <= 100
        )


def test_explainability_reason_contains_actual_feature_data(
    sample_preprocessed_data: pd.DataFrame,
):
    used_columns = list(
        sample_preprocessed_data.columns
    )

    explainer = MahalanobisExplainability(
        dataframe=sample_preprocessed_data,
        used_columns=used_columns,
    )

    explanation = explainer.explain_record(
        record_number=1,
        top_n=3,
    )

    for item in explanation[
        "feature_contributions"
    ]:
        assert item[
            "feature_name"
        ] in item["reason"]

        assert (
            str(
                item["actual_value"]
            )
            in item["reason"]
        )

        assert (
            str(
                item["feature_mean"]
            )
            in item["reason"]
        )


# ======================================================================
# Validation tests
# ======================================================================


def test_univariate_rejects_empty_dataframe():
    with pytest.raises(
        ValueError
    ):
        UnivariateDetector(
            pd.DataFrame()
        )


def test_multivariate_rejects_empty_dataframe():
    with pytest.raises(
        ValueError
    ):
        MultivariateDetector(
            pd.DataFrame()
        )


def test_explainability_rejects_missing_feature():
    dataframe = pd.DataFrame(
        {
            "feature_a": [
                1.0,
                2.0,
                3.0,
            ]
        }
    )

    with pytest.raises(
        ValueError
    ):
        MahalanobisExplainability(
            dataframe=dataframe,
            used_columns=[
                "feature_a",
                "missing_feature",
            ],
        )


def test_univariate_rejects_non_numeric_column():
    dataframe = pd.DataFrame(
        {
            "category": [
                "A",
                "B",
                "C",
            ]
        }
    )

    detector = UnivariateDetector(
        dataframe
    )

    assert (
        detector.get_eligible_columns()
        == []
    )


def test_multivariate_requires_multiple_records():
    dataframe = pd.DataFrame(
        {
            "feature_a": [
                10.0,
            ],
            "feature_b": [
                20.0,
            ],
        }
    )

    detector = MultivariateDetector(
        dataframe
    )

    with pytest.raises(
        ValueError
    ):
        detector.detect()