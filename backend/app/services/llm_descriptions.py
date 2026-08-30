from __future__ import annotations

from typing import Any


def generate_column_description(
    profile: dict[str, Any],
    dataset_summary: dict[str, Any],
    *,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Return a deterministic, evidence-based description.

    Descriptions are intentionally local and deterministic so the application
    works without an external API key and produces reproducible results.
    """
    name = profile.get("name", "This column")
    role = profile.get("role", "Feature")
    kind = profile.get("kind", "categorical")
    unique = profile.get("unique_values", 0)
    non_null = profile.get("non_null_values", 0)

    if role == "Identifier":
        if "customer" in name.lower():
            text = f"{name} is an identifier used to distinguish customer records."
        elif "transaction" in name.lower():
            text = f"{name} is an identifier used to distinguish transaction records."
        else:
            text = f"{name} is an identifier used to distinguish records or entities."
    elif kind == "numeric":
        text = (
            f"{name} is a numerical feature with {unique} distinct observed values "
            f"across {non_null} non-missing records; it is suitable for quantitative "
            "statistical and anomaly analysis."
        )
    elif kind == "boolean":
        text = f"{name} is a boolean feature representing a two-state condition."
    elif kind == "datetime":
        text = (
            f"{name} is a date/time feature representing temporal observations that "
            "can support ordering and time-based analysis."
        )
    elif kind == "null_empty":
        text = f"{name} is empty across the dataset and contains no observed values."
    else:
        text = (
            f"{name} is a categorical feature with {unique} distinct observed values "
            f"across {non_null} non-missing records; its values represent discrete "
            "categories or labels."
        )

    return {"description": text, "source": "deterministic", "model": None}
