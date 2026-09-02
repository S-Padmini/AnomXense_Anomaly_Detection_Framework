from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib import error, request


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


def _normalise_text(value: str) -> str:
    value = str(value or "").strip().lower()
    value = re.sub(r"[_\-.]+", " ", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _column_profile_for_prompt(
    column_name: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """
    Reduce the Phase 1 profile to useful semantic evidence.

    We intentionally send actual dataset evidence to the LLM rather than
    maintaining dataset-specific mappings.
    """

    result = {
        "name": column_name,
        "type": profile.get("type")
        or profile.get("data_type")
        or profile.get("dtype"),
        "role": profile.get("role"),
        "description": profile.get("description"),
        "unique_count": profile.get("unique_count")
        or profile.get("n_unique"),
        "missing_count": profile.get("missing_count"),
        "sample_values": profile.get("sample_values")
        or profile.get("samples"),
    }

    return result


def _build_prompt(
    objective: str,
    selected_columns: list[str],
    column_profiles: dict[str, dict[str, Any]],
    phase3_statistics: dict[str, Any],
) -> str:

    columns = [
        _column_profile_for_prompt(
            column,
            column_profiles.get(column, {}),
        )
        for column in selected_columns
    ]

    payload = {
        "objective": objective,
        "selected_columns": columns,
        "phase3_statistics": phase3_statistics,
    }

    return f"""
You are the objective-understanding component of a dataset-independent
anomaly detection system.

Your job is to understand the user's natural-language anomaly detection
objective using semantic reasoning and the actual dataset evidence.

IMPORTANT:
- Never assume fixed column names.
- Never invent columns.
- Only use columns present in selected_columns.
- The same concept may be expressed using different words.
- Match concepts semantically, not only by exact string matching.
- Column names, descriptions, types, values and statistical evidence may
  all provide useful evidence.

PRIMARY ANOMALY TYPES:
1. point
   An individual observation/record is unusual.
2. contextual
   An observation is unusual because of its context, such as time,
   location, category, condition, or another contextual variable.
3. collective
   A group, sequence, pattern, or collection of observations is unusual
   even when individual observations may not be unusual independently.

IMPORTANT:
Local/global/temporal comparison is NOT itself the primary anomaly type.
It is a separate comparison_scope dimension.

COMPARISON SCOPE:
- global: compare observations against the overall population
- local: compare observations within groups defined by a reference/context
  column or subgroup
- temporal: behavior depends on ordering/time
- none: no explicit comparison requirement

DETECTION BEHAVIOR:
Describe what the user wants to detect, for example:
- unusually high/low values
- unusual records
- deviations from normal behavior
- unusual groups
- unusual sequences
- changes/trends
- deviations conditioned on context

TEMPORAL REQUIREMENT:
- required
- optional
- not_required
- unclear

COLUMN ROLES:
- target: variable/value whose unusual behavior is being detected
- reference: column used to define a comparison group
- context: variable providing conditions under which behavior is unusual

Return ONLY valid JSON matching this structure:

{{
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
  "temporal_requirement_reason": "...",
  "target_columns": [
    {{
      "column": "ACTUAL_COLUMN_NAME",
      "role": "target",
      "confidence": 0.0,
      "evidence": "..."
    }}
  ],
  "reference_columns": [
    {{
      "column": "ACTUAL_COLUMN_NAME",
      "role": "reference",
      "confidence": 0.0,
      "evidence": "..."
    }}
  ],
  "context_columns": [
    {{
      "column": "ACTUAL_COLUMN_NAME",
      "role": "context",
      "confidence": 0.0,
      "evidence": "..."
    }}
  ],
  "assumptions": [],
  "warnings": []
}}

Dataset evidence:

{json.dumps(payload, ensure_ascii=False, default=str, indent=2)}
""".strip()


def _extract_json(text: str) -> dict[str, Any]:
    """
    Extract JSON even if the model accidentally wraps it in markdown.
    """

    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])

    raise ValueError("LLM did not return valid JSON.")


def _clamp_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _validate_columns(
    items: Any,
    allowed_columns: set[str],
    expected_role: str,
) -> list[dict[str, Any]]:

    if not isinstance(items, list):
        return []

    result: list[dict[str, Any]] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        column = str(item.get("column", "")).strip()

        if column not in allowed_columns:
            continue

        result.append(
            {
                "column": column,
                "role": expected_role,
                "confidence": _clamp_confidence(
                    item.get("confidence", 0)
                ),
                "evidence": str(
                    item.get("evidence", "")
                ).strip(),
            }
        )

    return result


def _normalise_llm_result(
    raw: dict[str, Any],
    objective: str,
    selected_columns: list[str],
) -> dict[str, Any]:

    allowed = set(selected_columns)

    anomaly_type = str(
        raw.get("anomaly_type", "point")
    ).strip().lower()

    if anomaly_type not in PRIMARY_ANOMALY_TYPES:
        anomaly_type = "point"

    comparison_scope = str(
        raw.get("comparison_scope", "none")
    ).strip().lower()

    if comparison_scope not in COMPARISON_SCOPES:
        comparison_scope = "none"

    temporal_requirement = str(
        raw.get("temporal_requirement", "unclear")
    ).strip().lower()

    if temporal_requirement not in TEMPORAL_REQUIREMENTS:
        temporal_requirement = "unclear"

    return {
        "original_objective": objective,
        "interpreted_objective": str(
            raw.get("interpreted_objective")
            or objective
        ).strip(),

        "anomaly_type": anomaly_type,
        "anomaly_type_confidence": _clamp_confidence(
            raw.get("anomaly_type_confidence")
        ),
        "anomaly_type_reason": str(
            raw.get("anomaly_type_reason", "")
        ).strip(),

        "comparison_scope": comparison_scope,
        "comparison_scope_confidence": _clamp_confidence(
            raw.get("comparison_scope_confidence")
        ),
        "comparison_scope_reason": str(
            raw.get("comparison_scope_reason", "")
        ).strip(),

        "detection_behavior": str(
            raw.get("detection_behavior", "")
        ).strip(),

        "detection_behavior_reason": str(
            raw.get("detection_behavior_reason", "")
        ).strip(),

        "temporal_requirement": temporal_requirement,

        "temporal_requirement_reason": str(
            raw.get("temporal_requirement_reason", "")
        ).strip(),

        "target_columns": _validate_columns(
            raw.get("target_columns"),
            allowed,
            "target",
        ),

        "reference_columns": _validate_columns(
            raw.get("reference_columns"),
            allowed,
            "reference",
        ),

        "context_columns": _validate_columns(
            raw.get("context_columns"),
            allowed,
            "context",
        ),

        "assumptions": [
            str(x).strip()
            for x in raw.get("assumptions", [])
            if str(x).strip()
        ],

        "warnings": [
            str(x).strip()
            for x in raw.get("warnings", [])
            if str(x).strip()
        ],
    }


def _call_gemini(prompt: str) -> dict[str, Any]:
    """
    Optional Gemini integration.

    If GEMINI_API_KEY is absent, the caller will use the deterministic
    semantic fallback.
    """

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash",
    ).strip()

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
        f"?key={api_key}"
    )

    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    encoded = json.dumps(body).encode("utf-8")

    req = request.Request(
        url,
        data=encoded,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=45) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )
    except error.HTTPError as exc:
        message = exc.read().decode(
            "utf-8",
            errors="replace",
        )
        raise RuntimeError(
            f"Gemini request failed: {message}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(
            f"Gemini connection failed: {exc}"
        ) from exc

    candidates = payload.get("candidates", [])

    if not candidates:
        raise RuntimeError(
            "Gemini returned no candidates."
        )

    parts = (
        candidates[0]
        .get("content", {})
        .get("parts", [])
    )

    text_parts = [
        str(part.get("text", ""))
        for part in parts
        if part.get("text")
    ]

    if not text_parts:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return _extract_json("\n".join(text_parts))


def _fallback_parse(
    objective: str,
    selected_columns: list[str],
    column_profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Safe fallback when an LLM is unavailable.

    This is intentionally generic. It does not contain dataset-specific
    mappings such as customer_id -> reference or amount -> target.

    It uses semantic token overlap between the objective and actual
    column names/descriptions.
    """

    objective_norm = _normalise_text(objective)
    objective_tokens = set(objective_norm.split())

    scored_columns: list[tuple[float, str]] = []

    for column in selected_columns:
        profile = column_profiles.get(column, {})

        text_parts = [
            column,
            str(profile.get("description", "")),
            str(profile.get("role", "")),
            str(profile.get("type", "")),
        ]

        column_text = _normalise_text(
            " ".join(text_parts)
        )

        column_tokens = set(column_text.split())

        overlap = objective_tokens.intersection(
            column_tokens
        )

        score = len(overlap) / max(
            1,
            len(objective_tokens),
        )

        scored_columns.append(
            (score, column)
        )

    scored_columns.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    matched = [
        (score, column)
        for score, column in scored_columns
        if score > 0
    ]

    target_columns = []

    if matched:
        score, column = matched[0]

        target_columns.append(
            {
                "column": column,
                "role": "target",
                "confidence": min(
                    0.75,
                    max(0.35, score),
                ),
                "evidence": (
                    "The column has semantic overlap with "
                    "the detection objective."
                ),
            }
        )

    objective_lower = objective_norm

    local_terms = {
        "each",
        "within",
        "per",
        "individual",
        "group",
        "customer",
        "user",
        "device",
        "location",
        "account",
    }

    contextual_terms = {
        "context",
        "condition",
        "location",
        "time",
        "season",
        "weekday",
        "hour",
        "environment",
    }

    collective_terms = {
        "sequence",
        "pattern",
        "series",
        "group of",
        "collective",
        "trend",
        "behavior pattern",
    }

    local = any(
        term in objective_lower
        for term in local_terms
    )

    contextual = any(
        term in objective_lower
        for term in contextual_terms
    )

    collective = any(
        term in objective_lower
        for term in collective_terms
    )

    if collective:
        anomaly_type = "collective"
    elif contextual:
        anomaly_type = "contextual"
    else:
        anomaly_type = "point"

    reference_columns = []

    if local and len(matched) > 1:
        score, column = matched[1]

        reference_columns.append(
            {
                "column": column,
                "role": "reference",
                "confidence": min(
                    0.7,
                    max(0.35, score),
                ),
                "evidence": (
                    "The column appears semantically related "
                    "to the grouping/comparison requirement."
                ),
            }
        )

    temporal = any(
        term in objective_lower
        for term in {
            "over time",
            "time",
            "trend",
            "sequence",
            "hourly",
            "daily",
            "weekly",
            "monthly",
            "timestamp",
            "temporal",
        }
    )

    return {
        "original_objective": objective,
        "interpreted_objective": objective,
        "anomaly_type": anomaly_type,
        "anomaly_type_confidence": 0.45,
        "anomaly_type_reason": (
            "The objective was interpreted using a generic "
            "semantic fallback because the LLM was unavailable."
        ),
        "comparison_scope": (
            "local"
            if local
            else "temporal"
            if temporal
            else "none"
        ),
        "comparison_scope_confidence": 0.4,
        "comparison_scope_reason": (
            "The comparison requirement was inferred from "
            "the objective language."
        ),
        "detection_behavior": (
            "Identify observations that deviate from expected behavior."
        ),
        "detection_behavior_reason": (
            "The objective describes unusual or abnormal behavior."
        ),
        "temporal_requirement": (
            "required"
            if temporal
            else "not_required"
        ),
        "temporal_requirement_reason": (
            "Temporal language was detected in the objective."
            if temporal
            else "No explicit temporal requirement was detected."
        ),
        "target_columns": target_columns,
        "reference_columns": reference_columns,
        "context_columns": [],
        "assumptions": [],
        "warnings": [
            "LLM semantic interpretation was unavailable; "
            "fallback interpretation was used."
        ],
    }


def parse_objective(
    *,
    objective: str,
    selected_columns: list[str],
    column_profiles: dict[str, dict[str, Any]],
    phase3_statistics: dict[str, Any],
) -> dict[str, Any]:

    objective = objective.strip()

    if not objective:
        raise ValueError(
            "Detection objective cannot be empty."
        )

    if not selected_columns:
        raise ValueError(
            "At least one selected column is required."
        )

    prompt = _build_prompt(
        objective,
        selected_columns,
        column_profiles,
        phase3_statistics,
    )

    try:
        raw = _call_gemini(prompt)

        return _normalise_llm_result(
            raw,
            objective,
            selected_columns,
        )

    except Exception as exc:
        fallback = _fallback_parse(
            objective,
            selected_columns,
            column_profiles,
        )

        fallback["warnings"].append(
            f"Semantic LLM analysis unavailable: {str(exc)}"
        )

        return fallback