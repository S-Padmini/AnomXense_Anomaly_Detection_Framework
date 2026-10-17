from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv

try:
    from groq import Groq
except ImportError:
    Groq = None


# ============================================================
# ENVIRONMENT
# ============================================================

CURRENT_FILE = os.path.abspath(__file__)

BACKEND_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(CURRENT_FILE),
        "..",
        "..",
        "..",
    )
)

ENV_PATH = os.path.join(
    BACKEND_DIR,
    ".env",
)

load_dotenv(
    ENV_PATH,
    override=False,
)


DEFAULT_LLM_MODEL = "openai/gpt-oss-120b"


PRIMARY_ANOMALY_TYPES = {
    "point",
    "contextual",
    "collective",
}


COMPARISON_SCOPES = {
    "global",
    "local",
    "temporal",
    "none",
}


TEMPORAL_REQUIREMENTS = {
    "required",
    "optional",
    "not_required",
    "unclear",
}


ATTRIBUTE_ROLES = {
    "detection_feature",
    "entity_identifier",
    "context_feature",
    "reference_feature",
    "temporal_feature",
    "supporting_feature",
}


# ============================================================
# BASIC HELPERS
# ============================================================

def _text(value: Any) -> str:

    return str(
        value or ""
    ).strip()


def _clamp_confidence(
    value: Any,
) -> float:

    try:

        number = float(value)

    except (
        TypeError,
        ValueError,
    ):

        return 0.0

    return max(
        0.0,
        min(
            1.0,
            number,
        ),
    )


# ============================================================
# COLUMN PROFILE
# ============================================================

def _column_profile_for_prompt(
    column_name: str,
    profile: dict[str, Any],
) -> dict[str, Any]:

    return {
        "name": column_name,

        "type":
            profile.get("type")
            or profile.get("data_type")
            or profile.get("dtype")
            or "",

        "role":
            profile.get("role")
            or "",

        "description":
            profile.get("description")
            or profile.get("llm_description")
            or "",

        "unique_count":
            profile.get("unique_count")
            or profile.get("n_unique")
            or profile.get("unique_values"),

        "missing_count":
            (
                profile.get("missing_count")
                if profile.get("missing_count") is not None
                else profile.get("missing_values")
            ),

        "missing_percentage":
            profile.get(
                "missing_percentage"
            ),

        "sample_values":
            profile.get("sample_values")
            or profile.get("samples")
            or [],
    }


# ============================================================
# PRIMARY SEMANTIC PROMPT
# ============================================================

def _build_prompt(
    objective: str,
    selected_columns: list[str],
    available_columns: list[str],
    column_profiles: dict[str, dict[str, Any]],
    phase3_statistics: dict[str, Any],
) -> str:

    all_columns = [
        _column_profile_for_prompt(
            column,
            column_profiles.get(
                column,
                {},
            ),
        )
        for column in available_columns
    ]

    selected_profiles = [
        _column_profile_for_prompt(
            column,
            column_profiles.get(
                column,
                {},
            ),
        )
        for column in selected_columns
    ]

    dataset_context = {
        "objective": objective,

        "all_dataset_columns": all_columns,

        "confirmed_phase2_selected_columns":
            selected_profiles,

        "phase3_statistics":
            phase3_statistics,
    }

    dataset_json = json.dumps(
        dataset_context,
        ensure_ascii=False,
        default=str,
        indent=2,
    )

    prompt = """
You are the semantic objective-understanding engine of an
intelligent, domain-independent anomaly detection platform.

Your responsibility is to understand what the investigator
wants to detect from natural language.

The investigator does NOT need to know anomaly-detection
terminology.

============================================================
IMPORTANT DATASET DISTINCTION
============================================================

The supplied dataset context contains TWO column groups:

1. all_dataset_columns

These are every actual column available in the uploaded
dataset.

2. confirmed_phase2_selected_columns

These are the columns currently approved by the investigator
during Phase 2.

These two groups are intentionally different.

Your job is to determine which actual dataset attributes are
materially required by the investigation objective.

An attribute may therefore be:

- already selected in Phase 2
- available in the dataset but NOT selected in Phase 2

If an objective requires an attribute that exists in
all_dataset_columns but is absent from
confirmed_phase2_selected_columns, identify it in
attributes_involved.

DO NOT silently add it to the Phase 2 selection.

The Python validation layer will compare the objective
requirements with the confirmed Phase 2 selection.

============================================================
CORE SEMANTIC REQUIREMENT
============================================================

Use semantic reasoning based on:

1. User objective
2. Actual dataset columns
3. Phase 1 column descriptions
4. Datatypes
5. Representative values
6. Dataset context
7. Phase 3 statistical evidence

Do NOT use hardcoded keyword-to-column rules.

Do NOT use predefined domain-specific column names.

Do NOT assume a particular column name always represents
a particular concept.

Do NOT select a column merely because its name resembles
a word in the objective.

============================================================
IDENTIFY ALL ATTRIBUTES INVOLVED
============================================================

The objective may require more than the variable whose value
is ultimately judged anomalous.

For example, an objective may require comparison:

- globally
- against an entity
- against a group
- against a location
- against a machine
- against a patient
- against an account
- against a time period
- under a particular operating condition

When such context is materially required, the actual dataset
attribute defining that context MUST be included in
attributes_involved.

This applies even if that attribute was not selected in
Phase 2.

============================================================
CRITICAL DISTINCTION
============================================================

attributes_involved is the COMPLETE semantic set of actual
dataset columns materially needed to satisfy the objective.

target_columns contains ONLY primary anomaly variables.

reference_columns contain attributes defining the reference
population or comparison entity/group.

context_columns contain attributes defining the context in
which abnormality is evaluated.

An entity identifier or temporal attribute can therefore be
present in attributes_involved without being present in
target_columns.

============================================================
SEMANTIC COLUMN AUDIT
============================================================

Inspect EVERY column in all_dataset_columns.

For each column ask:

1. Does it represent the behavior being investigated?

2. Does it identify the entity, subject, group, account,
   customer, machine, patient, device, etc. against which
   behavior is compared?

3. Does it establish temporal context?

4. Does it define a condition required by the objective?

5. Does it define the reference population?

6. Does it provide another materially necessary supporting
   attribute?

7. Or is it unrelated?

Only materially relevant columns belong in
attributes_involved.

============================================================
NO FABRICATION
============================================================

Every returned column must exactly match one of the supplied
all_dataset_columns.

Never invent a column.

============================================================
PHASE 2 SELECTION RULE
============================================================

attributes_involved may contain an attribute that is available
in the dataset but absent from Phase 2 selection.

This is intentional.

However:

target_columns,
reference_columns,
and
context_columns

must contain only attributes that are currently present in the
confirmed Phase 2 selection.

============================================================
ANOMALY TYPE
============================================================

Choose exactly one:

point
contextual
collective

point:
An individual observation is unusual compared with the
general population.

contextual:
An observation is unusual because its meaning depends on
another entity, group, condition, environment, or context.

collective:
A group, sequence, or combination of observations is unusual
even if individual observations may not be unusual alone.

============================================================
COMPARISON SCOPE
============================================================

Choose exactly one:

global
local
temporal
none

global:
Comparison against the overall dataset.

local:
Comparison within meaningful entities, groups, or
subpopulations.

temporal:
Comparison according to time/order.

none:
No explicit comparison context is required.

============================================================
TEMPORAL REQUIREMENT
============================================================

Choose exactly one:

required
optional
not_required
unclear

Use required only when temporal information is materially
part of the investigator's objective.

============================================================
OBJECTIVE UNDERSTANDING
============================================================

interpreted_objective must be ONE clear detailed paragraph.

It must explain:

- what is being detected
- what makes it unusual
- what it is compared against
- what context matters
- what the investigator is trying to identify

============================================================
WHY THIS FITS
============================================================

anomaly_type_reason must clearly explain why the inferred
anomaly type matches the objective.

============================================================
ATTRIBUTES INVOLVED
============================================================

For every materially relevant actual dataset column return:

column:
The exact dataset column name.

role:
One of:

detection_feature
entity_identifier
context_feature
reference_feature
temporal_feature
supporting_feature

confidence:
A value from 0.0 to 1.0.

reason:
A specific explanation of why this actual column materially
participates in the investigator's objective.

IMPORTANT:

If the objective depends on an entity/customer/account/device/
machine/person/group comparison, include the actual dataset
column defining that comparison.

If the objective depends on time/order, include the actual
dataset temporal column.

Do not include unrelated columns.

============================================================
TARGET COLUMNS
============================================================

target_columns must contain ONLY primary anomaly variables.

Do not put entity identifiers into target_columns merely
because they are involved in the objective.

Do not put temporal attributes into target_columns merely
because they are involved in the objective.

Only include target columns that are currently selected
during Phase 2.

============================================================
REFERENCE COLUMNS
============================================================

reference_columns should contain selected columns that define
the reference population or comparison entity/group when
appropriate.

============================================================
CONTEXT COLUMNS
============================================================

context_columns should contain selected columns that define
the context in which abnormality is evaluated.

Temporal attributes may be included here when appropriate.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

The JSON structure must be:

{
  "interpreted_objective": "...",
  "anomaly_type": "point|contextual|collective",
  "anomaly_type_confidence": 0.0,
  "anomaly_type_reason": "...",
  "comparison_scope": "global|local|temporal|none",
  "comparison_scope_confidence": 0.0,
  "comparison_scope_reason": "...",
  "detection_behavior": "...",
  "detection_behavior_reason": "...",
  "temporal_requirement": "required|optional|not_required|unclear",

  "attributes_involved": [
    {
      "column": "EXACT_DATASET_COLUMN",
      "role": "detection_feature",
      "confidence": 0.0,
      "reason": "..."
    }
  ],

  "target_columns": [
    {
      "column": "EXACT_SELECTED_COLUMN",
      "role": "target",
      "confidence": 0.0,
      "evidence": "..."
    }
  ],

  "reference_columns": [
    {
      "column": "EXACT_SELECTED_COLUMN",
      "role": "reference",
      "confidence": 0.0,
      "evidence": "..."
    }
  ],

  "context_columns": [
    {
      "column": "EXACT_SELECTED_COLUMN",
      "role": "context",
      "confidence": 0.0,
      "evidence": "..."
    }
  ],

  "assumptions": [],
  "warnings": []
}

============================================================
ACTUAL DATASET CONTEXT
============================================================

""" + dataset_json

    return prompt.strip()


# ============================================================
# SECOND ATTRIBUTE AUDIT PROMPT
# ============================================================

def _build_attribute_audit_prompt(
    objective: str,
    selected_columns: list[str],
    available_columns: list[str],
    column_profiles: dict[str, dict[str, Any]],
    initial_result: dict[str, Any],
) -> str:

    columns = [
        _column_profile_for_prompt(
            column,
            column_profiles.get(
                column,
                {},
            ),
        )
        for column in available_columns
    ]

    selected_profiles = [
        _column_profile_for_prompt(
            column,
            column_profiles.get(
                column,
                {},
            ),
        )
        for column in selected_columns
    ]

    columns_json = json.dumps(
        columns,
        ensure_ascii=False,
        default=str,
        indent=2,
    )

    selected_json = json.dumps(
        selected_profiles,
        ensure_ascii=False,
        default=str,
        indent=2,
    )

    initial_json = json.dumps(
        initial_result,
        ensure_ascii=False,
        default=str,
        indent=2,
    )

    prompt = """
You are performing a SECOND independent semantic audit for
an anomaly-detection investigation.

Your ONLY purpose is to identify ALL actual dataset attributes
that materially participate in the investigator's objective.

Do not blindly trust the first semantic interpretation.

============================================================
INVESTIGATOR OBJECTIVE
============================================================

""" + objective + """

============================================================
ALL DATASET COLUMNS
============================================================

""" + columns_json + """

============================================================
CURRENT PHASE 2 SELECTION
============================================================

""" + selected_json + """

============================================================
INITIAL INTERPRETATION
============================================================

""" + initial_json + """

============================================================
AUDIT TASK
============================================================

Inspect EVERY column in ALL DATASET COLUMNS.

Determine whether each column is materially required to answer
the investigator's objective.

A column is materially involved when it is needed to:

- measure the behavior being investigated
- identify the entity/group against which behavior is compared
- define temporal context
- define another condition under which behavior becomes unusual
- define the reference population
- provide another explicitly necessary supporting attribute

A column is NOT materially involved merely because:

- it exists
- it is numeric
- it has variance
- it is statistically interesting
- its name resembles a word in the objective
- a machine-learning algorithm could potentially use it

============================================================
IMPORTANT
============================================================

If the objective requires an attribute that is present in the
dataset but was not selected during Phase 2, RETURN THAT
ATTRIBUTE.

Do not silently remove it because it is not in Phase 2.

The deterministic Python validation layer will identify it as
missing from the confirmed Phase 2 selection.

============================================================
NO FABRICATION
============================================================

Every returned column must exactly match a supplied
ALL DATASET COLUMN.

Never invent columns.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON:

{
  "attributes_involved": [
    {
      "column": "EXACT_DATASET_COLUMN",
      "role": "detection_feature|entity_identifier|context_feature|reference_feature|temporal_feature|supporting_feature",
      "confidence": 0.0,
      "reason": "Specific semantic explanation."
    }
  ]
}
"""

    return prompt.strip()


# ============================================================
# JSON EXTRACTION
# ============================================================

def _extract_json(
    text: str,
) -> dict[str, Any]:

    text = str(
        text or ""
    ).strip()

    if not text:

        raise ValueError(
            "LLM returned an empty response."
        )

    if text.startswith("```"):

        text = re.sub(
            r"^```(?:json)?",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"```$",
            "",
            text,
        ).strip()

    try:

        result = json.loads(
            text
        )

        if isinstance(
            result,
            dict,
        ):

            return result

    except json.JSONDecodeError:
        pass

    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
    )

    if (
        start >= 0
        and end > start
    ):

        try:

            result = json.loads(
                text[
                    start:end + 1
                ]
            )

            if isinstance(
                result,
                dict,
            ):

                return result

        except json.JSONDecodeError:
            pass

    raise ValueError(
        "LLM did not return valid JSON."
    )


# ============================================================
# GROQ CLIENT
# ============================================================

def _get_groq_client():

    if Groq is None:

        raise RuntimeError(
            "Groq package is not available in the "
            "running Python environment."
        )

    api_key = os.getenv(
        "GROQ_API_KEY",
        "",
    ).strip()

    if not api_key:

        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    return Groq(
        api_key=api_key
    )


# ============================================================
# GROQ CALL
# ============================================================

def _call_groq(
    prompt: str,
    max_tokens: int = 2800,
) -> dict[str, Any]:

    client = _get_groq_client()

    model = os.getenv(
        "LLM_DESCRIPTION_MODEL",
        DEFAULT_LLM_MODEL,
    ).strip()

    response = client.chat.completions.create(
        model=model,

        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior data scientist "
                    "specialized in semantic objective "
                    "understanding for anomaly detection. "
                    "Return ONLY valid JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],

        temperature=0.1,

        max_tokens=max_tokens,
    )

    if not response.choices:

        raise RuntimeError(
            "Groq returned no choices."
        )

    content = getattr(
        response.choices[0].message,
        "content",
        None,
    )

    if not content:

        raise RuntimeError(
            "Groq returned an empty response."
        )

    return _extract_json(
        content
    )


# ============================================================
# ATTRIBUTE VALIDATION
# ============================================================

def _validate_attributes(
    items: Any,
    allowed_columns: set[str],
) -> list[dict[str, Any]]:

    if not isinstance(
        items,
        list,
    ):

        return []

    role_aliases = {

        "target":
            "detection_feature",

        "detection":
            "detection_feature",

        "detection_feature":
            "detection_feature",

        "entity":
            "entity_identifier",

        "entity_identifier":
            "entity_identifier",

        "reference":
            "reference_feature",

        "reference_feature":
            "reference_feature",

        "context":
            "context_feature",

        "context_feature":
            "context_feature",

        "temporal":
            "temporal_feature",

        "temporal_feature":
            "temporal_feature",

        "supporting":
            "supporting_feature",

        "supporting_feature":
            "supporting_feature",
    }

    unique = {}

    for item in items:

        if isinstance(
            item,
            str,
        ):

            column = item.strip()

            role = (
                "supporting_feature"
            )

            confidence = 0.0

            reason = ""

        elif isinstance(
            item,
            dict,
        ):

            column = str(
                item.get("column")
                or item.get("name")
                or item.get("column_name")
                or ""
            ).strip()

            raw_role = str(
                item.get("role")
                or "supporting_feature"
            ).strip().lower()

            role = role_aliases.get(
                raw_role,
                "supporting_feature",
            )

            confidence = _clamp_confidence(
                item.get(
                    "confidence",
                    0,
                )
            )

            reason = str(
                item.get("reason")
                or item.get("evidence")
                or item.get("explanation")
                or item.get("why_relevant")
                or ""
            ).strip()

        else:

            continue

        if column not in allowed_columns:
            continue

        if role not in ATTRIBUTE_ROLES:

            role = (
                "supporting_feature"
            )

        candidate = {
            "column": column,
            "role": role,
            "confidence": confidence,
            "reason": reason,
        }

        existing = unique.get(
            column
        )

        if (
            existing is None
            or confidence
            > existing["confidence"]
        ):

            unique[
                column
            ] = candidate

    return list(
        unique.values()
    )


# ============================================================
# STANDARD COLUMN VALIDATION
# ============================================================

def _validate_columns(
    items: Any,
    allowed_columns: set[str],
    expected_role: str,
) -> list[dict[str, Any]]:

    if not isinstance(
        items,
        list,
    ):

        return []

    unique = {}

    for item in items:

        if isinstance(
            item,
            str,
        ):

            column = item.strip()

            confidence = 0.0

            evidence = ""

        elif isinstance(
            item,
            dict,
        ):

            column = str(
                item.get("column")
                or item.get("name")
                or item.get("column_name")
                or ""
            ).strip()

            confidence = _clamp_confidence(
                item.get(
                    "confidence",
                    0,
                )
            )

            evidence = str(
                item.get("evidence")
                or item.get("reason")
                or item.get("explanation")
                or item.get("why_relevant")
                or ""
            ).strip()

        else:

            continue

        if column not in allowed_columns:
            continue

        candidate = {
            "column": column,
            "role": expected_role,
            "confidence": confidence,
            "evidence": evidence,
        }

        existing = unique.get(
            column
        )

        if (
            existing is None
            or confidence
            > existing["confidence"]
        ):

            unique[
                column
            ] = candidate

    return list(
        unique.values()
    )


# ============================================================
# NORMALIZE RESULT
# ============================================================

def _normalise_llm_result(
    raw: dict[str, Any],
    objective: str,
    selected_columns: list[str],
    available_columns: list[str],
) -> dict[str, Any]:

    selected_allowed = set(
        selected_columns
    )

    available_allowed = set(
        available_columns
    )

    anomaly_type = str(
        raw.get(
            "anomaly_type",
            "",
        )
    ).strip().lower()

    if anomaly_type not in PRIMARY_ANOMALY_TYPES:

        raise ValueError(
            "LLM returned an invalid anomaly type."
        )

    comparison_scope = str(
        raw.get(
            "comparison_scope",
            "none",
        )
    ).strip().lower()

    if comparison_scope not in COMPARISON_SCOPES:

        comparison_scope = "none"

    temporal_requirement = str(
        raw.get(
            "temporal_requirement",
            "unclear",
        )
    ).strip().lower()

    if temporal_requirement not in TEMPORAL_REQUIREMENTS:

        temporal_requirement = "unclear"

    interpreted_objective = str(
        raw.get(
            "interpreted_objective",
            "",
        )
    ).strip()

    if not interpreted_objective:

        raise ValueError(
            "LLM did not provide an objective interpretation."
        )

    anomaly_type_reason = str(
        raw.get(
            "anomaly_type_reason",
            "",
        )
    ).strip()

    if not anomaly_type_reason:

        anomaly_type_reason = (
            "The anomaly type was inferred from "
            "the semantic meaning of the objective "
            "and the available dataset context."
        )

    # --------------------------------------------------------
    # ALL OBJECTIVE ATTRIBUTES
    #
    # Validate against ALL actual dataset columns, not only
    # Phase 2 selection.
    # --------------------------------------------------------

    attributes_involved = (
        _validate_attributes(
            raw.get(
                "attributes_involved"
            ),
            available_allowed,
        )
    )

    # --------------------------------------------------------
    # TARGET / REFERENCE / CONTEXT
    #
    # These remain restricted to Phase 2 selected columns.
    # --------------------------------------------------------

    target_columns = (
        _validate_columns(
            raw.get(
                "target_columns"
            ),
            selected_allowed,
            "target",
        )
    )

    reference_columns = (
        _validate_columns(
            raw.get(
                "reference_columns"
            ),
            selected_allowed,
            "reference",
        )
    )

    context_columns = (
        _validate_columns(
            raw.get(
                "context_columns"
            ),
            selected_allowed,
            "context",
        )
    )

    # --------------------------------------------------------
    # FALLBACK FROM CLASSIFIED COLUMNS
    # --------------------------------------------------------

    if not attributes_involved:

        fallback = []

        for item in target_columns:

            fallback.append({
                "column":
                    item["column"],

                "role":
                    "detection_feature",

                "confidence":
                    item["confidence"],

                "reason":
                    item["evidence"],
            })

        for item in reference_columns:

            fallback.append({
                "column":
                    item["column"],

                "role":
                    "reference_feature",

                "confidence":
                    item["confidence"],

                "reason":
                    item["evidence"],
            })

        for item in context_columns:

            fallback.append({
                "column":
                    item["column"],

                "role":
                    "context_feature",

                "confidence":
                    item["confidence"],

                "reason":
                    item["evidence"],
            })

        attributes_involved = fallback

    return {

        "original_objective":
            objective,

        "interpreted_objective":
            interpreted_objective,

        "anomaly_type":
            anomaly_type,

        "anomaly_type_confidence":
            _clamp_confidence(
                raw.get(
                    "anomaly_type_confidence"
                )
            ),

        "anomaly_type_reason":
            anomaly_type_reason,

        "comparison_scope":
            comparison_scope,

        "comparison_scope_confidence":
            _clamp_confidence(
                raw.get(
                    "comparison_scope_confidence"
                )
            ),

        "comparison_scope_reason":
            str(
                raw.get(
                    "comparison_scope_reason",
                    "",
                )
            ).strip(),

        "detection_behavior":
            str(
                raw.get(
                    "detection_behavior",
                    "",
                )
            ).strip(),

        "detection_behavior_reason":
            str(
                raw.get(
                    "detection_behavior_reason",
                    "",
                )
            ).strip(),

        "temporal_requirement":
            temporal_requirement,

        "temporal_requirement_reason":
            str(
                raw.get(
                    "temporal_requirement_reason",
                    "",
                )
            ).strip(),

        "attributes_involved":
            attributes_involved,

        "target_columns":
            target_columns,

        "reference_columns":
            reference_columns,

        "context_columns":
            context_columns,

        "assumptions": [
            str(item).strip()
            for item in raw.get(
                "assumptions",
                [],
            )
            if str(item).strip()
        ],

        "warnings": [
            str(item).strip()
            for item in raw.get(
                "warnings",
                [],
            )
            if str(item).strip()
        ],
    }


# ============================================================
# MERGE ATTRIBUTE AUDIT
# ============================================================

def _merge_attribute_audit(
    primary: dict[str, Any],
    audit: dict[str, Any],
    selected_columns: list[str],
    available_columns: list[str],
) -> list[dict[str, Any]]:

    allowed = set(
        available_columns
    )

    primary_items = (
        _validate_attributes(
            primary.get(
                "attributes_involved"
            ),
            allowed,
        )
    )

    audit_items = (
        _validate_attributes(
            audit.get(
                "attributes_involved"
            ),
            allowed,
        )
    )

    merged = {}

    for item in primary_items:

        merged[
            item["column"]
        ] = item

    for item in audit_items:

        column = item[
            "column"
        ]

        existing = merged.get(
            column
        )

        if existing is None:

            merged[
                column
            ] = item

        else:

            if (
                item.get(
                    "reason"
                )
                and
                (
                    not existing.get(
                        "reason"
                    )
                    or
                    item["confidence"]
                    >=
                    existing["confidence"]
                )
            ):

                existing[
                    "reason"
                ] = item[
                    "reason"
                ]

            if (
                item["confidence"]
                >
                existing["confidence"]
            ):

                existing[
                    "confidence"
                ] = item[
                    "confidence"
                ]

            if (
                existing["role"]
                == "supporting_feature"
                and
                item["role"]
                != "supporting_feature"
            ):

                existing[
                    "role"
                ] = item[
                    "role"
                ]

    # Preserve the actual dataset column order.
    ordered = []

    for column in available_columns:

        if column in merged:

            ordered.append(
                merged[
                    column
                ]
            )

    return ordered


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def parse_objective(
    *,
    objective: str,
    selected_columns: list[str],
    available_columns: list[str] | None = None,
    column_profiles: dict[str, dict[str, Any]],
    phase3_statistics: dict[str, Any],
) -> dict[str, Any]:

    objective = str(
        objective or ""
    ).strip()

    if not objective:

        raise ValueError(
            "Detection objective cannot be empty."
        )

    if not selected_columns:

        raise ValueError(
            "At least one selected column is required."
        )

    if available_columns is None:

        available_columns = list(
            selected_columns
        )

    available_columns = [
        str(column)
        for column in available_columns
        if str(column).strip()
    ]

    # ========================================================
    # FIRST LLM PASS
    # ========================================================

    primary_prompt = _build_prompt(
        objective,
        selected_columns,
        available_columns,
        column_profiles,
        phase3_statistics,
    )

    primary_raw = _call_groq(
        primary_prompt,
        max_tokens=2800,
    )

    result = _normalise_llm_result(
        primary_raw,
        objective,
        selected_columns,
        available_columns,
    )

    # ========================================================
    # SECOND LLM ATTRIBUTE AUDIT
    # ========================================================

    audit_prompt = _build_attribute_audit_prompt(
        objective,
        selected_columns,
        available_columns,
        column_profiles,
        result,
    )

    audit_raw = _call_groq(
        audit_prompt,
        max_tokens=1800,
    )

    # ========================================================
    # MERGE
    # ========================================================

    result[
        "attributes_involved"
    ] = _merge_attribute_audit(
        result,
        audit_raw,
        selected_columns,
        available_columns,
    )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    allowed = set(
        available_columns
    )

    result[
        "attributes_involved"
    ] = [
        item
        for item in result[
            "attributes_involved"
        ]
        if item.get(
            "column"
        ) in allowed
    ]

    return result