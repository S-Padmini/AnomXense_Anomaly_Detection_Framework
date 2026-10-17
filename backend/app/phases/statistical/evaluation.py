from __future__ import annotations

from typing import Any


def calculate_accuracy(
    actual_labels: list[int],
    predicted_labels: list[int],
) -> float:
    """
    Calculate classification accuracy from actual and predicted labels.

    Label convention:
        0 = Normal
        1 = Anomaly

    Returns:
        Accuracy as a percentage from 0.0 to 100.0.
    """

    if len(actual_labels) != len(predicted_labels):
        raise ValueError(
            "Actual and predicted labels must contain the same number of records."
        )

    if not actual_labels:
        raise ValueError("At least one record is required to calculate accuracy.")

    correct_predictions = sum(
        1
        for actual, predicted in zip(actual_labels, predicted_labels)
        if int(actual) == int(predicted)
    )

    accuracy = (correct_predictions / len(actual_labels)) * 100.0

    return round(accuracy, 2)


def calculate_confusion_matrix(
    actual_labels: list[int],
    predicted_labels: list[int],
) -> dict[str, int]:
    """
    Calculate TP, TN, FP and FN from actual and predicted labels.

    Label convention:
        0 = Normal
        1 = Anomaly
    """

    if len(actual_labels) != len(predicted_labels):
        raise ValueError(
            "Actual and predicted labels must contain the same number of records."
        )

    if not actual_labels:
        raise ValueError(
            "At least one record is required to calculate the confusion matrix."
        )

    true_positive = 0
    true_negative = 0
    false_positive = 0
    false_negative = 0

    for actual, predicted in zip(actual_labels, predicted_labels):
        actual = int(actual)
        predicted = int(predicted)

        if actual == 1 and predicted == 1:
            true_positive += 1

        elif actual == 0 and predicted == 0:
            true_negative += 1

        elif actual == 0 and predicted == 1:
            false_positive += 1

        elif actual == 1 and predicted == 0:
            false_negative += 1

    return {
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
    }


def evaluate_detection(
    actual_labels: list[int],
    predicted_labels: list[int],
) -> dict[str, Any]:
    """
    Evaluate anomaly detection results using ground-truth labels.

    Returns accuracy and the confusion-matrix values used to calculate it.
    """

    accuracy = calculate_accuracy(
        actual_labels=actual_labels,
        predicted_labels=predicted_labels,
    )

    confusion_matrix = calculate_confusion_matrix(
        actual_labels=actual_labels,
        predicted_labels=predicted_labels,
    )

    total_records = len(actual_labels)

    return {
        "accuracy": accuracy,
        "total_records": total_records,
        **confusion_matrix,
    }