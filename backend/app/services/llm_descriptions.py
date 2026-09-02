from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

from dotenv import load_dotenv

try:
    from groq import Groq
except ImportError:
    Groq = None


# =========================================================
# ENVIRONMENT
# =========================================================

# Load backend/.env reliably when this module is imported.


_ENV_FILE = (
    Path(__file__).resolve().parents[2] / ".env"
)

load_dotenv(
    dotenv_path=_ENV_FILE,
    override=False,
)


# =========================================================
# LLM CONFIGURATION
# =========================================================

# The model is read from the environment at runtime.
# This avoids using an outdated model value if .env changes.
DEFAULT_LLM_MODEL = "openai/gpt-oss-120b"

GROQ_API_KEY_ENV = "GROQ_API_KEY"

# Maximum representative values sent for one column.
MAX_SAMPLE_VALUES = 12

# Maximum strongest numeric relationships.
MAX_NUMERIC_RELATIONSHIPS = 30

# Maximum common categorical values.
MAX_COMMON_VALUES = 10

# Maximum columns included in semantic context.
MAX_COLUMNS_IN_CONTEXT = 150


def _get_llm_model() -> str:
    """
    Get the currently configured Groq model.

    The value is read at runtime so changes in .env
    are respected without modifying this file.
    """
    return (
        os.getenv(
            "LLM_DESCRIPTION_MODEL",
            DEFAULT_LLM_MODEL,
        )
        or DEFAULT_LLM_MODEL
    ).strip()


# =========================================================
# SAFE VALUE HELPERS
# =========================================================

def _safe_value(value: Any) -> Any:
    """
    Convert pandas / numpy / datetime values into
    JSON-safe primitive values.
    """
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    return str(value)


def _round_number(
    value: Any,
    digits: int = 4,
) -> Any:
    """
    Safely round numeric values.
    """
    try:
        if pd.isna(value):
            return None

        return round(
            float(value),
            digits,
        )
    except Exception:
        return _safe_value(value)


# =========================================================
# REPRESENTATIVE VALUES
# =========================================================

def _sample_values(
    series: pd.Series,
    limit: int = MAX_SAMPLE_VALUES,
) -> list[Any]:
    """
    Return representative non-null values.

    The complete raw column is intentionally NOT sent
    to the LLM. A compact representative sample is used
    for semantic reasoning while keeping the prompt small.
    """
    try:
        non_null = series.dropna()

        if non_null.empty:
            return []

        if len(non_null) <= limit:
            selected = non_null
        else:
            head_count = min(
                5,
                limit // 2,
            )

            tail_count = min(
                limit - head_count,
                len(non_null) - head_count,
            )

            selected = pd.concat(
                [
                    non_null.head(head_count),
                    non_null.tail(tail_count),
                ]
            )

            selected = selected.drop_duplicates()

        return [
            _safe_value(value)
            for value in selected.tolist()[:limit]
        ]

    except Exception:
        return []


# =========================================================
# VALUE / SEMANTIC PATTERN
# =========================================================

def _value_pattern(
    series: pd.Series,
) -> dict[str, Any]:
    """
    Build semantic evidence for one column.

    This function provides evidence to the LLM.
    It does NOT assign business meaning.
    """
    result: dict[str, Any] = {}

    try:
        non_null = series.dropna()

        if non_null.empty:
            return {
                "observed_values": 0,
                "unique_values": 0,
            }

        result["observed_values"] = int(
            len(non_null)
        )

        result["unique_values"] = int(
            non_null.nunique()
        )

        result["unique_ratio"] = _round_number(
            non_null.nunique() / len(non_null),
            4,
        )

        # -------------------------------------------------
        # Numeric evidence
        # -------------------------------------------------

        numeric = pd.to_numeric(
            non_null,
            errors="coerce",
        )

        if numeric.notna().all():
            result["numeric"] = True

            result["minimum"] = _round_number(
                numeric.min()
            )

            result["maximum"] = _round_number(
                numeric.max()
            )

            result["mean"] = _round_number(
                numeric.mean()
            )

            result["median"] = _round_number(
                numeric.median()
            )

            result["std"] = _round_number(
                numeric.std()
            )

            result["range"] = _round_number(
                numeric.max() - numeric.min()
            )

            try:
                integer_like = (
                    (numeric.dropna() % 1) == 0
                ).mean()

                result["integer_like_ratio"] = _round_number(
                    integer_like,
                    4,
                )

            except Exception:
                pass

            return result

        # -------------------------------------------------
        # Datetime evidence
        # -------------------------------------------------

        datetime_values = pd.to_datetime(
            non_null,
            errors="coerce",
            format="mixed",
        )

        valid_datetime_ratio = (
            datetime_values.notna().mean()
        )

        if valid_datetime_ratio >= 0.8:
            result["datetime_like"] = True

            result["datetime_valid_ratio"] = _round_number(
                valid_datetime_ratio,
                4,
            )

            result["earliest"] = _safe_value(
                datetime_values.min()
            )

            result["latest"] = _safe_value(
                datetime_values.max()
            )

            return result

        # -------------------------------------------------
        # Categorical / text evidence
        # -------------------------------------------------

        values_as_text = non_null.astype(str)

        value_counts = (
            values_as_text
            .value_counts()
            .head(MAX_COMMON_VALUES)
        )

        result["categorical_or_text"] = True

        result["common_values"] = [
            {
                "value": str(value),
                "count": int(count),
                "percentage": _round_number(
                    count / len(non_null) * 100,
                    2,
                ),
            }
            for value, count in value_counts.items()
        ]

        try:
            average_length = (
                values_as_text
                .str.len()
                .mean()
            )

            result["average_text_length"] = _round_number(
                average_length,
                2,
            )

        except Exception:
            pass

    except Exception:
        return result

    return result


# =========================================================
# COLUMN NAME TOKENS
# =========================================================

def _name_tokens(
    name: str,
) -> list[str]:
    """
    Break a column name into semantic tokens.

    This does NOT assign meaning.

    Examples:
        employee_name -> employee, name
        joiningYear   -> joining, year
        monthly-salary -> monthly, salary
    """
    text = str(name)

    text = re.sub(
        r"([a-z])([A-Z])",
        r"\1 \2",
        text,
    )

    text = re.sub(
        r"[_\-.]+",
        " ",
        text,
    )

    text = re.sub(
        r"[^A-Za-z0-9 ]+",
        " ",
        text,
    )

    tokens = [
        token.lower()
        for token in text.split()
        if token.strip()
    ]

    return tokens


# =========================================================
# DATASET SEMANTIC PROFILE
# =========================================================

def build_dataset_semantic_context(
    df: pd.DataFrame,
    target_column: str,
    dataset_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a compact semantic representation of the dataset.

    The raw dataset itself is NOT sent to Groq.

    The LLM receives evidence about:

        - every column
        - column names
        - semantic name tokens
        - data types
        - roles
        - missingness
        - representative values
        - numeric ranges
        - categorical values
        - temporal information
        - cross-column numeric relationships
        - dataset dimensions
    """

    summary_details = (
        dataset_summary.get(
            "column_details",
            {},
        )
        if isinstance(
            dataset_summary,
            dict,
        )
        else {}
    )

    all_columns = [
        str(column)
        for column in df.columns
    ]

    columns_context: list[dict[str, Any]] = []

    # -----------------------------------------------------
    # ALL COLUMN PROFILES
    # -----------------------------------------------------

    for index, column in enumerate(df.columns):

        if index >= MAX_COLUMNS_IN_CONTEXT:
            break

        column_name = str(column)

        series = df[column]

        detail = summary_details.get(
            column_name,
            {},
        )

        column_context = {
            "name": column_name,

            "name_tokens": _name_tokens(
                column_name
            ),

            "dtype": str(
                detail.get(
                    "dtype",
                    series.dtype,
                )
            ),

            "role": detail.get(
                "role",
                "Feature",
            ),

            "row_count": int(
                len(series)
            ),

            "missing_values": int(
                series.isna().sum()
            ),

            "missing_percentage": _round_number(
                series.isna().mean() * 100,
                2,
            ),

            "sample_values": _sample_values(
                series
            ),

            "value_pattern": _value_pattern(
                series
            ),
        }

        columns_context.append(
            column_context
        )

    # -----------------------------------------------------
    # NUMERIC RELATIONSHIPS
    # -----------------------------------------------------

    correlations: list[dict[str, Any]] = []

    numeric_df = df.select_dtypes(
        include="number"
    )

    if numeric_df.shape[1] >= 2:

        try:
            corr = numeric_df.corr(
                numeric_only=True
            )

            for i, first in enumerate(
                corr.columns
            ):

                for second in corr.columns[
                    i + 1:
                ]:

                    value = corr.loc[
                        first,
                        second,
                    ]

                    if pd.notna(value):

                        correlations.append(
                            {
                                "column_1": str(
                                    first
                                ),

                                "column_2": str(
                                    second
                                ),

                                "correlation": _round_number(
                                    value,
                                    4,
                                ),
                            }
                        )

            correlations = sorted(
                correlations,
                key=lambda item: abs(
                    item["correlation"]
                ),
                reverse=True,
            )[
                :MAX_NUMERIC_RELATIONSHIPS
            ]

        except Exception:
            correlations = []

    # -----------------------------------------------------
    # BASIC DATASET CONTEXT
    # -----------------------------------------------------

    dataset_context = {
        "target_column": str(
            target_column
        ),

        "row_count": int(
            len(df)
        ),

        "column_count": int(
            len(df.columns)
        ),

        "all_columns": all_columns,

        "columns": columns_context,

        "numeric_relationships": correlations,
    }

    return dataset_context


# =========================================================
# GROQ CLIENT
# =========================================================

def _get_groq_client() -> Any:
    """
    Create the Groq client from backend/.env.
    """

    if Groq is None:
        print(
            "GROQ CLIENT ERROR: groq package is not available "
            "in the running Python environment."
        )
        return None

    api_key = os.getenv(
        GROQ_API_KEY_ENV
    )

    if not api_key:
        print(
            "GROQ CLIENT ERROR: GROQ_API_KEY was not loaded."
        )
        return None

    try:
        client = Groq(
            api_key=api_key
        )

        print(
            "GROQ CLIENT: initialized successfully"
        )

        return client

    except Exception as exc:
        print(
            "GROQ CLIENT ERROR:",
            repr(exc),
        )
        return None


# =========================================================
# LLM SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are a senior data analyst and dataset semantic interpretation system.

Your job is to determine the real-world meaning of ONE target column by
reasoning over the COMPLETE DATASET CONTEXT supplied by the application.

The dataset context is evidence. You must use relationships between columns
when they help establish the meaning of the target column.

IMPORTANT RULES:

1. Do NOT merely repeat datatype, row count, missing values, unique count,
   mean, median, minimum, maximum or other statistics.

2. The final answer must primarily explain WHAT THE COLUMN REPRESENTS in the
   real world.

3. If the column name clearly communicates its meaning, explain that meaning
   naturally and specifically.

4. If the column name is ambiguous, inspect the other columns, representative
   values, value ranges, categorical context, temporal context and numerical
   relationships before forming an interpretation.

5. A cryptic name such as "X", "A", "V1" or "col_7" must NOT automatically
   receive a generic description. Try to infer its meaning from the dataset
   context.

6. Never infer meaning merely because a value is numeric.

7. Do not invent units, currency, business definitions or relationships that
   are unsupported by the evidence.

8. When evidence supports a likely interpretation but does not prove it,
   clearly use language such as "appears to represent", "likely represents",
   or "is consistent with".

9. If the exact meaning cannot reasonably be established, say that explicitly
   instead of hallucinating a business meaning.

10. The description should be useful for understanding the column's role in
    anomaly detection, but anomaly-detection relevance is secondary to the
    real-world meaning.

11. Write 2 to 4 clear sentences.

12. Do not mention that you are an AI.

13. Do not mention this prompt.

14. Do not output bullet points, JSON, headings, confidence scores or labels.

15. Return only the final human-readable description.
""".strip()


# =========================================================
# GENERATE WITH GROQ
# =========================================================

def _generate_with_llm(
    profile: dict[str, Any],
    dataset_context: dict[str, Any],
) -> dict[str, Any]:

    client = _get_groq_client()

    if client is None:
        return {
            "description": None,
            "source": "llm_unavailable",
            "model": None,
        }

    target_column = str(
        profile.get(
            "name",
            dataset_context.get(
                "target_column",
                "Unknown",
            ),
        )
    )

    model = _get_llm_model()

    user_prompt = f"""
Determine the real-world semantic meaning of this target column.

TARGET COLUMN:
{target_column}

TARGET COLUMN PROFILE:
{json.dumps(
    profile,
    indent=2,
    ensure_ascii=False,
    default=str,
)}

COMPLETE DATASET CONTEXT:
{json.dumps(
    dataset_context,
    indent=2,
    ensure_ascii=False,
    default=str,
)}

Reason over the complete dataset before writing the final description.

In particular:

- Compare the target column name with the names of other columns.
- Inspect representative values.
- Consider whether its value pattern is compatible with a known business
  concept.
- Use relationships with other numerical columns when meaningful.
- Use employee, entity, category and date relationships when present.
- Do not force an interpretation if evidence is insufficient.
- Clearly distinguish evidence-supported interpretation from uncertainty.
- Return only the final 2-to-4 sentence description.
""".strip()

    try:

        response = client.chat.completions.create(
            model=model,
            temperature=0.1,
            max_tokens=300,
            timeout=90.0,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

        choice = response.choices[0]

        message = choice.message

        description = message.content

        # Some Groq reasoning models may return reasoning separately
        # before producing the final answer. Use the final content only.
        if description is None:
            description = ""

        description = description.strip()

        if not description:
            raise ValueError(
                "LLM returned an empty description."
            )

        if description is None:
            raise ValueError(
                "LLM returned no content."
            )

        description = description.strip()

        if not description:
            raise ValueError(
                "LLM returned an empty description."
            )

        return {
            "description": description,
            "source": "llm",
            "model": model,
        }

    except Exception as exc:

        # Keep API details server-side.
        print(
            "LLM column-description error:",
            repr(exc),
        )

        return {
            "description": None,
            "source": "llm_error",
            "model": model,
            "error": repr(exc),
        }


# =========================================================
# FALLBACK DESCRIPTION
# =========================================================

def _fallback_description(
    profile: dict[str, Any],
) -> str:

    name = profile.get(
        "name",
        "This column",
    )

    role = profile.get(
        "role",
        "Feature",
    )

    kind = profile.get(
        "kind",
        "unknown",
    )

    if role == "Identifier":

        return (
            f"{name} appears to identify or distinguish "
            "records or entities in the dataset. Its exact "
            "business meaning cannot be determined from the "
            "available semantic evidence."
        )

    if kind == "datetime":

        return (
            f"{name} represents a date or time-related value "
            "in the dataset. Its specific business meaning "
            "cannot be determined from the available context."
        )

    if kind == "boolean":

        return (
            f"{name} represents a two-state condition in the "
            "dataset. The available context is insufficient "
            "to determine the exact meaning of those states."
        )

    return (
        f"{name} contains {kind} values, but the available "
        "dataset evidence is insufficient to determine its "
        "specific real-world meaning reliably."
    )


# =========================================================
# PUBLIC FUNCTION
# =========================================================

def generate_column_description(
    profile: dict[str, Any],
    dataset_summary: dict[str, Any],
    *,
    df: pd.DataFrame | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Generate a semantic description for one column.

    Preferred flow:

        complete dataframe
                ↓
        dataset semantic profile
                ↓
        target column + complete context
                ↓
        Groq LLM
                ↓
        semantic description

    If the LLM cannot be reached, a transparent fallback
    is returned.
    """

    if not use_llm:
        return {
            "description": _fallback_description(profile),
            "source": "fallback",
            "model": None,
        }

    if df is None:
        return {
            "description": _fallback_description(profile),
            "source": "fallback_no_dataframe",
            "model": None,
        }

    try:
        dataset_context = build_dataset_semantic_context(
            df=df,
            target_column=str(
                profile.get(
                    "name",
                    "",
                )
            ),
            dataset_summary=dataset_summary,
        )

        result = _generate_with_llm(
            profile=profile,
            dataset_context=dataset_context,
        )

        # IMPORTANT:
        # Preserve the actual LLM error instead of silently
        # converting it to "fallback".
        if result.get("description"):
            return result

        return {
            "description": _fallback_description(profile),
            "source": result.get(
                "source",
                "llm_error",
            ),
            "model": result.get(
                "model"
            ),
            "error": result.get(
                "error"
            ),
        }

    except Exception as exc:
        print(
            "COLUMN DESCRIPTION PIPELINE ERROR:",
            repr(exc),
        )

        return {
            "description": _fallback_description(profile),
            "source": "llm_pipeline_error",
            "model": _get_llm_model(),
            "error": repr(exc),
        }

