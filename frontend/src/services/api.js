const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000"
).replace(/\/+$/, "");


/* =========================================================
   GENERIC API REQUEST
========================================================= */

async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}${path}`,
      options
    );
  } catch (error) {
    throw new Error(
      `Unable to connect to backend at ${API_BASE_URL}. ` +
      `Please make sure the FastAPI backend is running.`
    );
  }

  let body = null;

  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const detail =
      body?.detail ||
      body?.message ||
      `Request failed with status ${response.status}`;

    if (Array.isArray(detail)) {
      throw new Error(
        detail
          .map(
            (item) =>
              item?.msg ||
              JSON.stringify(item)
          )
          .join(", ")
      );
    }

    throw new Error(
      typeof detail === "string"
        ? detail
        : JSON.stringify(detail)
    );
  }

  return body;
}


/* =========================================================
   PHASE 1
   DATASET ANALYSIS
========================================================= */

export async function uploadDataset(file) {
  if (!file) {
    throw new Error(
      "Please select a dataset file."
    );
  }

  const form = new FormData();

  form.append("file", file);

  return request(
    "/api/phase1/analyze",
    {
      method: "POST",
      body: form,
    }
  );
}


/* =========================================================
   PHASE 2
   COLUMN DETAILS
========================================================= */

export async function getColumnDetails(
  datasetId,
  columnName
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  if (!columnName) {
    throw new Error(
      "Column name is missing."
    );
  }

  return request(
    `/api/phase2/${encodeURIComponent(
      datasetId
    )}/column/${encodeURIComponent(
      columnName
    )}`
  );
}


/* =========================================================
   PHASE 2
   SAVE COLUMN SELECTION
========================================================= */

export async function saveSelection(
  datasetId,
  selectedColumns
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return request(
    `/api/phase2/${encodeURIComponent(
      datasetId
    )}/selection`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        selected_columns:
          Array.isArray(selectedColumns)
            ? selectedColumns
            : [],
      }),
    }
  );
}


/* =========================================================
   PHASE 2
   CONFIRM SELECTION
========================================================= */

export async function confirmSelection(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return request(
    `/api/phase2/${encodeURIComponent(
      datasetId
    )}/confirm`,
    {
      method: "POST",
    }
  );
}


/* =========================================================
   PHASE 3
   PREPROCESSING INSPECTION
========================================================= */

export async function getPreprocessingInspection(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return request(
    `/api/phase3/${encodeURIComponent(
      datasetId
    )}/preprocessing/inspection`
  );
}


/* =========================================================
   PHASE 3
   MISSING COLUMN INSPECTION
========================================================= */

export async function getMissingColumnInspection(
  datasetId,
  columnName
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  if (!columnName) {
    throw new Error(
      "Column name is missing."
    );
  }

  return request(
    `/api/phase3/${encodeURIComponent(
      datasetId
    )}/preprocessing/inspection/missing/${encodeURIComponent(
      columnName
    )}`
  );
}


/* =========================================================
   PHASE 3
   DUPLICATE COLUMN INSPECTION
========================================================= */

export async function getDuplicateColumnInspection(
  datasetId,
  columnName
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  if (!columnName) {
    throw new Error(
      "Column name is missing."
    );
  }

  return request(
    `/api/phase3/${encodeURIComponent(
      datasetId
    )}/preprocessing/inspection/duplicates/${encodeURIComponent(
      columnName
    )}`
  );
}


/* =========================================================
   PHASE 3
   PREPROCESS DATASET
========================================================= */

export async function preprocessDataset(
  datasetId,
  selectedColumns
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  if (
    !Array.isArray(selectedColumns) ||
    selectedColumns.length === 0
  ) {
    throw new Error(
      "Please select at least one column."
    );
  }

  return request(
    `/api/phase3/${encodeURIComponent(
      datasetId
    )}/preprocess`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        selected_columns:
          selectedColumns,
      }),
    }
  );
}


/* =========================================================
   PHASE 3
   DATASET PREVIEW
========================================================= */

export async function getPreview(
  datasetId,
  page = 1,
  pageSize = 10
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  const safePage = Math.max(
    1,
    Number(page) || 1
  );

  const safePageSize = Math.max(
    1,
    Number(pageSize) || 10
  );

  return request(
    `/api/phase3/${encodeURIComponent(
      datasetId
    )}/preview?page=${safePage}&page_size=${safePageSize}`
  );
}


/* =========================================================
   PHASE 3
   STATISTICAL ANALYSIS
========================================================= */

export async function runStatisticalAnalysis(
  datasetId,
  selectedColumns
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  if (
    !Array.isArray(selectedColumns) ||
    selectedColumns.length === 0
  ) {
    throw new Error(
      "Please select at least one column."
    );
  }

  return request(
    `/api/phase3/${encodeURIComponent(
      datasetId
    )}/statistical-analysis`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        selected_columns:
          selectedColumns,
      }),
    }
  );
}


/* =========================================================
   PHASE 4
   OBJECTIVE UNDERSTANDING
========================================================= */

/*
   IMPORTANT:

   Your current backend exposes:

   POST
   /api/phase4/{dataset_id}/analyze

   The backend receives the natural-language objective
   and performs the actual semantic understanding.

   We intentionally keep the backend as the source
   of truth instead of calculating anomaly meaning
   inside React.
*/

export async function analyzePhase4Objective(
  datasetId,
  objective
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  if (
    typeof objective !== "string" ||
    !objective.trim()
  ) {
    throw new Error(
      "Please enter your detection objective."
    );
  }

  return request(
    `/api/phase4/${encodeURIComponent(
      datasetId
    )}/analyze`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        objective:
          objective.trim(),
      }),
    }
  );
}


/* =========================================================
   PHASE 4
   VALIDATION COMPATIBILITY FUNCTION
========================================================= */

/*
   App.jsx imports validateDetectionObjective.

   Your backend currently does not expose a separate
   /validate endpoint.

   Therefore this function correctly uses the existing
   Phase 4 objective-analysis endpoint.

   The returned backend interpretation is then checked
   by App.jsx against the user's selected configuration.
*/

export async function validateDetectionObjective(
  datasetId,
  payload = {}
) {
  const objective =
    payload?.objective || "";

  return analyzePhase4Objective(
    datasetId,
    objective
  );
}


/* =========================================================
   PHASE 4
   CONFIRM OBJECTIVE
========================================================= */

export async function confirmPhase4Objective(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return request(
    `/api/phase4/${encodeURIComponent(
      datasetId
    )}/confirm`,
    {
      method: "POST",
    }
  );
}


/* =========================================================
   PHASE 4
   COMPATIBILITY ALIAS
========================================================= */

export async function analyzePhase4(
  datasetId,
  objective
) {
  return analyzePhase4Objective(
    datasetId,
    objective
  );
}


/* =========================================================
   PHASE 4
   COLUMN VALIDATION
========================================================= */

export async function validatePhase4Column(
  datasetId,
  objective,
  column,
  role
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return request(
    "/api/phase4/validate-column",
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        dataset_id:
          datasetId,

        objective:
          objective,

        column:
          column,

        role:
          role,
      }),
    }
  );
}


/* =========================================================
   PHASE 4
   CONFIRM INTENT
========================================================= */

export async function confirmPhase4Intent({
  datasetId,
  objective,
  anomalyType,
  anomalyConfidence,
  targetColumns,
  explainByColumns,
}) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return request(
    "/api/phase4/confirm",
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        dataset_id:
          datasetId,

        objective:
          objective,

        anomaly_type:
          anomalyType,

        anomaly_confidence:
          anomalyConfidence,

        target_columns:
          targetColumns || [],

        explain_by_columns:
          explainByColumns || [],
      }),
    }
  );
}

/* =========================================================
   PHASE 5
   MODEL RECOMMENDATION
========================================================= */

export async function recommendModels(
  datasetId,
  payload = {}
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  const statisticalProfile =
    payload?.statistical_profile ||
    payload?.statisticalProfile ||
    payload?.analysis ||
    {};

  const interpretation =
    payload?.interpretation ||
    payload?.intent ||
    payload?.objective_interpretation ||
    {};

  const columnProfiles =
    payload?.column_profiles ||
    payload?.columnProfiles ||
    {};

  let topN =
    Number(payload?.top_n);

  if (
    !Number.isFinite(topN) ||
    topN <= 0
  ) {
    topN = 3;
  }

  return request(
    "/api/phase5/recommend",
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        dataset_id:
          datasetId,

        statistical_profile:
          statisticalProfile,

        interpretation:
          interpretation,

        column_profiles:
          columnProfiles,

        top_n:
          topN,
      }),
    }
  );
}

/* =========================================================
   PHASE 5
   COMPATIBILITY ALIAS
========================================================= */

export async function getModelRecommendations(
  datasetId,
  payload = {}
) {
  return recommendModels(
    datasetId,
    payload
  );
}


/* =========================================================
   HEALTH CHECK
========================================================= */

export async function healthCheck() {
  return request(
    "/health"
  );
}

/* =========================================================
   EXPORT BASE URL
========================================================= 
*/
export {
  API_BASE_URL,
};


