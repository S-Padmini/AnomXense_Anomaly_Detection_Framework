from __future__ import annotations

import io

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.phases.phase1.column_classifier import classify_column
from app.phases.phase3.preprocessing import build_preprocessing_inspection, preprocess_dataset

client = TestClient(app)


def make_dataset() -> pd.DataFrame:
    n = 753
    df = pd.DataFrame({
        "customer_id": [f"C{i:04d}" for i in range(n)],
        "transaction_id": [f"T{i:04d}" for i in range(n)],
        "age": [18 + (i % 52) for i in range(n)],
        "annual_income": [25000 + (i * 211) % 155000 for i in range(n)],
        "transaction_amount": [100 + (i * 37.1) % 50000 for i in range(n)],
        "transaction_count": [(i % 20) + 1 for i in range(n)],
        "customer_name": [f"Customer {i}" for i in range(n)],
        "city": ["Pune", "Mumbai", "Delhi"][0:] if False else ["Pune", "Mumbai", "Delhi"] * 251,
        "customer_segment": ["Retail", "SMB", "Enterprise"] * 251,
        "device_type": ["Mobile" if i % 2 == 0 else "Web" for i in range(n)],
        "payment_method": ["Card", "UPI", "Cash"] * 251,
        "transaction_status": ["Success", "Pending", "Failed"] * 251,
        "transaction_date": pd.date_range("2025-01-01", periods=n, freq="h"),
        "is_fraud_flag": [False] * n,
        "is_active": [True] * n,
    })
    # Exactly 6 missing values in the four columns used by Phase 3.
    df.loc[[10, 20], "age"] = None
    df.loc[[30, 40], "annual_income"] = None
    df.loc[[50, 60], "transaction_amount"] = None

    # Exactly three later records duplicate earlier records across the selected
    # Phase-3 columns, while keeping identifiers different.
    selected = ["age", "annual_income", "transaction_amount", "is_fraud_flag"]
    for source, target in [(0, 750), (1, 751), (2, 752)]:
        df.loc[target, selected] = df.loc[source, selected].values
    return df


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def test_customer_name_is_not_misclassified_as_identifier():
    s = pd.Series([f"Customer {i}" for i in range(100)])
    assert classify_column(s, "customer_name")["kind"] == "categorical"


def test_phase1_reports_nine_metrics_and_column_groups():
    response = client.post(
        "/api/phase1/analyze",
        files={"file": ("test.csv", csv_bytes(make_dataset()), "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["rows"] == 753
    assert body["columns"] == 15
    assert body["numeric"] == 4
    assert body["categorical"] == 6
    assert body["datetime"] == 1
    assert body["identifiers"] == 2
    assert body["boolean"] == 2
    assert body["null_empty"] == 0
    assert body["total_missing_values"] == 6
    assert len(body["all_column_names"]) == 15


def test_phase2_selection_and_confirmation():
    upload = client.post(
        "/api/phase1/analyze",
        files={"file": ("test.csv", csv_bytes(make_dataset()), "text/csv")},
    ).json()
    dataset_id = upload["dataset_id"]
    selected = ["age", "annual_income", "transaction_amount", "is_fraud_flag"]

    response = client.post(
        f"/api/phase2/{dataset_id}/selection",
        json={"selected_columns": selected},
    )
    assert response.status_code == 200
    assert response.json()["selected_count"] == 4

    response = client.post(f"/api/phase2/{dataset_id}/confirm")
    assert response.status_code == 200
    assert response.json()["confirmed"] is True


def test_phase3_inspection_preprocess_preview_and_statistics():
    upload = client.post(
        "/api/phase1/analyze",
        files={"file": ("test.csv", csv_bytes(make_dataset()), "text/csv")},
    ).json()
    dataset_id = upload["dataset_id"]
    selected = ["age", "annual_income", "transaction_amount", "is_fraud_flag"]

    client.post(f"/api/phase2/{dataset_id}/selection", json={"selected_columns": selected})
    client.post(f"/api/phase2/{dataset_id}/confirm")

    inspection = client.get(
        f"/api/phase3/{dataset_id}/preprocessing/inspection"
    ).json()
    assert inspection["row_count"] == 753
    assert inspection["missingTotal"] == 6
    assert inspection["exactDuplicateRows"] == 3

    result = client.post(
        f"/api/phase3/{dataset_id}/preprocess",
        json={"selected_columns": selected},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["missing_values_handled"] == 6
    assert body["duplicate_records_removed"] == 3
    assert body["before"]["rows"] == 753
    assert body["after"]["rows"] == 750
    assert body["after"]["missing_values"] == 0
    assert body["after"]["columns"] == 4
    assert body["extreme_values_retained"] is True

    preview = client.get(f"/api/phase3/{dataset_id}/preview?page=1&page_size=10")
    assert preview.status_code == 200
    preview_body = preview.json()
    assert preview_body["total_rows"] == 750
    assert preview_body["columns"] == selected
    assert len(preview_body["rows"]) == 10

    stats = client.post(
        f"/api/phase3/{dataset_id}/statistical-analysis",
        json={"selected_columns": selected},
    )
    assert stats.status_code == 200
    stats_body = stats.json()
    assert stats_body["analysis_completed"] is True
    assert stats_body["records"] == 750
    assert stats_body["features"] == 4
    assert set(stats_body["sections"]) == {
        "overview", "types", "distribution", "extreme", "scale",
        "correlation", "cluster", "density", "temporal", "timeseries",
    }


def test_preprocess_duplicate_detection_happens_before_imputation():
    df = pd.DataFrame({
        "a": [1.0, None, 1.0],
        "b": [2, 3, 2],
    })
    summary = {
        "numeric_column_names": ["a", "b"],
        "categorical_column_names": [],
        "datetime_column_names": [],
        "identifier_column_names": [],
        "boolean_column_names": [],
    }
    processed, result = preprocess_dataset(df, ["a", "b"], summary)
    assert result["duplicate_records_removed"] == 1
    assert len(processed) == 2
    assert result["missing_values_handled"] == 1
