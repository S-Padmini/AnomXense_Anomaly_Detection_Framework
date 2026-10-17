const API_BASE_URL = `${(import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "")}/api`;

/* =========================================================
   COMMON RESPONSE HANDLER
   ========================================================= */

async function handleResponse(response) {
  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const message =
      data?.detail ||
      data?.message ||
      data?.error ||
      `Request failed with status ${response.status}`;

    throw new Error(message);
  }

  return data;
}


/* =========================================================
   COMMON API REQUEST
   ========================================================= */

async function apiRequest(endpoint, options = {}) {
  const isFormData =
    options?.body instanceof FormData;

  const response = await fetch(
    `${API_BASE_URL}${endpoint}`,
    {
      ...options,

      headers: {
        ...(isFormData
          ? {}
          : {
              "Content-Type":
                "application/json",
            }),

        ...(options.headers || {}),
      },
    }
  );

  return handleResponse(response);
}


/* =========================================================
   PHASE 1 — DATASET UPLOAD
   ========================================================= */

/*
 * Backend:
 * POST /api/phase1/upload
 */

export async function uploadDataset(file) {
  if (!file) {
    throw new Error(
      "Please select a dataset file."
    );
  }

  const formData = new FormData();

  formData.append(
    "file",
    file
  );

  return apiRequest(
    "/phase1/upload",
    {
      method: "POST",
      body: formData,
    }
  );
}


/* =========================================================
   PHASE 1 — DATASET ANALYSIS
   ========================================================= */

/*
 * Backend:
 * POST /api/phase1/{dataset_id}/analyze
 */

export async function analyzeDataset(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase1/${encodeURIComponent(
      datasetId
    )}/analyze`,
    {
      method: "POST",
    }
  );
}


/*
 * Backend:
 * GET /api/phase1/{dataset_id}
 */

export async function getDatasetAnalysis(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase1/${encodeURIComponent(
      datasetId
    )}`
  );
}


/* =========================================================
   PHASE 1 — DATASET SUMMARY
   ========================================================= */

/*
 * Compatibility helper.
 */

export async function getDatasetSummary(
  datasetId
) {
  return getDatasetAnalysis(
    datasetId
  );
}


/* =========================================================
   PHASE 1 — COLUMN DETAILS
   ========================================================= */

/*
 * Backend:
 * GET /api/phase1/{dataset_id}/column/{column_name}
 *
 * The popup intentionally receives only:
 *
 * - column_name
 * - role
 * - data_type
 * - missing_percentage
 * - llm_description
 */

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

  return apiRequest(
    `/phase1/${encodeURIComponent(
      datasetId
    )}/column/${encodeURIComponent(
      columnName
    )}`
  );
}


/* =========================================================
   PHASE 1 — COLUMN DESCRIPTION
   ========================================================= */

export async function getColumnDescription(
  datasetId,
  columnName
) {
  return getColumnDetails(
    datasetId,
    columnName
  );
}


/* =========================================================
   PHASE 1 — MISSING VALUES
   ========================================================= */

export async function getMissingValues(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase1/${encodeURIComponent(
      datasetId
    )}/missing-values`
  );
}


/* =========================================================
   PHASE 2 — SAVE COLUMN SELECTION
   ========================================================= */

/*
 * Backend:
 * POST /api/phase2/{dataset_id}/confirm
 *
 * Body:
 * {
 *   selected_columns: [...]
 * }
 */

export async function saveSelection(
  datasetId,
  selectedColumns
) {
  return confirmSelection(
    datasetId,
    selectedColumns
  );
}


/* =========================================================
   PHASE 2 — SELECT COLUMNS
   ========================================================= */

export async function selectColumns(
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

  return apiRequest(
    `/phase2/${encodeURIComponent(
      datasetId
    )}/select`,
    {
      method: "POST",

      body: JSON.stringify({
        selected_columns:
          selectedColumns,
      }),
    }
  );
}


/* =========================================================
   PHASE 2 — CONFIRM SELECTION
   ========================================================= */

export async function confirmSelection(
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

  return apiRequest(
    `/phase2/${encodeURIComponent(
      datasetId
    )}/confirm`,
    {
      method: "POST",

      body: JSON.stringify({
        selected_columns:
          selectedColumns,
      }),
    }
  );
}


/* =========================================================
   PHASE 2 — CONFIRM COLUMN SELECTION
   ========================================================= */

/*
 * Compatibility alias.
 */

export async function confirmColumnSelection(
  datasetId,
  selectedColumns
) {
  return confirmSelection(
    datasetId,
    selectedColumns
  );
}


/* =========================================================
   PHASE 2 — GET SELECTED COLUMNS
   ========================================================= */

export async function getSelectedColumns(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase2/${encodeURIComponent(
      datasetId
    )}/selected`
  );
}


/* =========================================================
   PHASE 2 — GET COLUMN SELECTION
   ========================================================= */

/*
 * Compatibility helper for older
 * Phase 2 implementations.
 */

export async function getColumnSelection(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase2/${encodeURIComponent(
      datasetId
    )}`
  );
}


/* =========================================================
   PHASE 3 — DOWNLOAD PROCESSED DATASET
   ========================================================= */

/*
 * Backend:
 * GET /api/phase3/{dataset_id}/download
 *
 * Downloads the exact dataset produced by Phase 3
 * preprocessing as a CSV file.
 *
 * The backend performs:
 * - Missing-value handling
 * - Exact duplicate handling
 *
 * It does NOT remove anomaly/outlier values.
 */

export async function downloadProcessedDataset(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  const response = await fetch(
    `${API_BASE_URL}/phase3/${encodeURIComponent(
      datasetId
    )}/download`
  );

  if (!response.ok) {
    let message =
      `Request failed with status ${response.status}`;

    try {
      const data = await response.json();

      message =
        data?.detail ||
        data?.message ||
        data?.error ||
        message;
    } catch {
      // Response was not JSON.
    }

    throw new Error(message);
  }

  const blob =
    await response.blob();

  const disposition =
    response.headers.get(
      "Content-Disposition"
    );

  let filename =
    `processed_dataset_${datasetId}.csv`;

  const match =
    disposition?.match(
      /filename="?([^"]+)"?/i
    );

  if (match?.[1]) {
    filename = match[1];
  }

  const url =
    window.URL.createObjectURL(
      blob
    );

  const link =
    document.createElement("a");

  link.href = url;
  link.download = filename;

  document.body.appendChild(
    link
  );

  link.click();

  link.remove();

  window.URL.revokeObjectURL(url);

  return true;
}


/* =========================================================
   PHASE 3 — PREPROCESS DATASET
   ========================================================= */

/*
 * Backend:
 * POST /api/phase3/{dataset_id}/preprocess
 *
 * Body:
 * {
 *   selected_columns: [...]
 * }
 */

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

  return apiRequest(
    `/phase3/${encodeURIComponent(
      datasetId
    )}/preprocess`,
    {
      method: "POST",

      body: JSON.stringify({
        selected_columns:
          selectedColumns,
      }),
    }
  );
}


/* =========================================================
   PHASE 3 — RUN PREPROCESSING
   ========================================================= */

/*
 * Compatibility function.
 *
 * If older code calls runPreprocessing(),
 * it sends the preprocessing request.
 */

export async function runPreprocessing(
  datasetId,
  selectedColumns
) {
  if (
    Array.isArray(selectedColumns) &&
    selectedColumns.length > 0
  ) {
    return preprocessDataset(
      datasetId,
      selectedColumns
    );
  }

  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase3/${encodeURIComponent(
      datasetId
    )}/preprocess`,
    {
      method: "POST",
    }
  );
}


/* =========================================================
   PHASE 3 — PREPROCESSING RESULTS
   ========================================================= */

export async function getPreprocessingResults(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase3/${encodeURIComponent(
      datasetId
    )}/preprocessing`
  );
}


/* =========================================================
   PHASE 3 — PREPROCESSING INSPECTION
   ========================================================= */

/*
 * Backend:
 * GET /api/phase3/{dataset_id}/preprocessing/inspection
 */

export async function getPreprocessingInspection(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase3/${encodeURIComponent(
      datasetId
    )}/preprocessing/inspection`
  );
}


/* =========================================================
   PHASE 3 — DATASET PREVIEW
   ========================================================= */

/*
 * Backend:
 * GET /api/phase3/{dataset_id}/preview
 *
 * Query:
 * ?page=1&page_size=10
 */

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

  return apiRequest(
    `/phase3/${encodeURIComponent(
      datasetId
    )}/preview?page=${safePage}&page_size=${safePageSize}`
  );
}


/* =========================================================
   PHASE 3 — MISSING COLUMN INSPECTION
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

  return apiRequest(
    `/phase3/${encodeURIComponent(
      datasetId
    )}/preprocessing/inspection/missing/${encodeURIComponent(
      columnName
    )}`
  );
}


/* =========================================================
   PHASE 3 — DUPLICATE COLUMN INSPECTION
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

  return apiRequest(
    `/phase3/${encodeURIComponent(
      datasetId
    )}/preprocessing/inspection/duplicates/${encodeURIComponent(
      columnName
    )}`
  );
}


/* =========================================================
   PHASE 3 — STATISTICAL ANALYSIS
   ========================================================= */

/*
 * MAIN CURRENT ENDPOINT:
 *
 * POST
 * /api/phase3/{dataset_id}/statistical-analysis
 */

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

  return apiRequest(
    `/phase3/${encodeURIComponent(
      datasetId
    )}/statistical-analysis`,
    {
      method: "POST",

      body: JSON.stringify({
        selected_columns:
          selectedColumns,
      }),
    }
  );
}


/* =========================================================
   PHASE 3 — STATISTICS ALIAS
   ========================================================= */

export async function analyzeStatistics(
  datasetId,
  selectedColumns
) {
  return runStatisticalAnalysis(
    datasetId,
    selectedColumns
  );
}


/* =========================================================
   PHASE 3 — GET STATISTICAL ANALYSIS
   ========================================================= */

export async function getStatisticalAnalysis(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase3/${encodeURIComponent(
      datasetId
    )}/statistics`
  );
}


/* =========================================================
   PHASE 3 — STATISTICAL CHARACTERISTICS
   ========================================================= */

export async function getStatisticalCharacteristics(
  datasetId
) {
  return getStatisticalAnalysis(
    datasetId
  );
}


/* =========================================================
   PHASE 3 — STATISTICAL RESULTS
   ========================================================= */

export async function getStatisticalResults(
  datasetId
) {
  return getStatisticalAnalysis(
    datasetId
  );
}


/* =========================================================
   STATISTICAL APPROACH — DETECTION
   ========================================================= */

/*
 * These endpoints are separate from the existing
 * Phase 3 statistical-analysis endpoint.
 *
 * Existing Phase 3 statistical analysis:
 * POST /api/phase3/{dataset_id}/statistical-analysis
 *
 * Statistical detection:
 * GET /api/statistical/{dataset_id}/univariate
 * GET /api/statistical/{dataset_id}/multivariate
 *
 * Both detection endpoints operate on the Phase 3
 * preprocessed dataset stored in the backend session.
 */


/*
 * GET
 * /api/statistical/{dataset_id}/univariate
 *
 * Univariate statistical detection using IQR.
 */

export async function getUnivariateStatisticalDetection(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/statistical/${encodeURIComponent(
      datasetId
    )}/univariate`
  );
}


/*
 * GET
 * /api/statistical/{dataset_id}/multivariate
 *
 * Multivariate statistical detection using
 * Mahalanobis Distance.
 */

export async function getMultivariateStatisticalDetection(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/statistical/${encodeURIComponent(
      datasetId
    )}/multivariate`
  );
}


/*
 * Generic statistical detection helper.
 *
 * method:
 * - "univariate" → IQR
 * - "multivariate" → Mahalanobis Distance
 */

export async function runStatisticalDetection(
  datasetId,
  method
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  if (
    method !== "univariate" &&
    method !== "multivariate"
  ) {
    throw new Error(
      "Statistical detection method must be univariate or multivariate."
    );
  }

  if (method === "univariate") {
    return getUnivariateStatisticalDetection(
      datasetId
    );
  }

  return getMultivariateStatisticalDetection(
    datasetId
  );
}


/*
 * Compatibility/helper function.
 *
 * Runs the univariate IQR branch.
 */

export async function runUnivariateDetection(
  datasetId
) {
  return getUnivariateStatisticalDetection(
    datasetId
  );
}


/*
 * Compatibility/helper function.
 *
 * Runs the multivariate Mahalanobis branch.
 */

export async function runMultivariateDetection(
  datasetId
) {
  return getMultivariateStatisticalDetection(
    datasetId
  );
}


/*
 * POST
 * /api/statistical/approach
 *
 * Saves/records the statistical approach selected
 * by the frontend.
 *
 * Body:
 * {
 *   dataset_id: "...",
 *   approach: "univariate" | "multivariate"
 * }
 */

export async function selectStatisticalApproach(
  datasetId,
  approach
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  if (
    approach !== "univariate" &&
    approach !== "multivariate"
  ) {
    throw new Error(
      "Statistical approach must be univariate or multivariate."
    );
  }

  return apiRequest(
    "/statistical/approach",
    {
      method: "POST",

      body: JSON.stringify({
        dataset_id:
          datasetId,

        approach,
      }),
    }
  );
}


/*
 * POST
 * /api/statistical/{dataset_id}/multivariate/explain
 *
 * Requests dynamic explanation for one
 * Mahalanobis-detected record.
 *
 * Body:
 * {
 *   record_index: number,
 *   top_n: number
 * }
 */

export async function explainMultivariateRecord(
  datasetId,
  recordIndex,
  topN = 3
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  const numericRecordIndex =
    Number(recordIndex);

  if (
    !Number.isInteger(
      numericRecordIndex
    ) ||
    numericRecordIndex < 0
  ) {
    throw new Error(
      "A valid record index is required."
    );
  }

  let safeTopN =
    Number(topN);

  if (
    !Number.isInteger(
      safeTopN
    ) ||
    safeTopN <= 0
  ) {
    safeTopN = 3;
  }

  return apiRequest(
    `/statistical/${encodeURIComponent(
      datasetId
    )}/multivariate/explain`,
    {
      method: "POST",

      body: JSON.stringify({
        record_index:
          numericRecordIndex,

        top_n:
          safeTopN,
      }),
    }
  );
}


/* =========================================================
   PHASE 4 — OBJECTIVE UNDERSTANDING
   ========================================================= */

/*
 * IMPORTANT:
 *
 * React sends ONLY the natural-language objective.
 *
 * The backend + LLM determines:
 *
 * - objective interpretation
 * - anomaly type
 * - comparison scope
 * - temporal requirement
 * - relevant attributes
 * - target/detection features
 *
 * No frontend keyword logic is used.
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

  return apiRequest(
    `/phase4/${encodeURIComponent(
      datasetId
    )}/analyze`,
    {
      method: "POST",

      body: JSON.stringify({
        objective:
          objective.trim(),
      }),
    }
  );
}


/* =========================================================
   PHASE 4 — COMPATIBILITY ALIAS
   ========================================================= */

export async function analyzeObjective(
  datasetId,
  objective
) {
  return analyzePhase4Objective(
    datasetId,
    objective
  );
}


/* =========================================================
   PHASE 4 — COMPATIBILITY ALIAS
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
   PHASE 4 — VALIDATE OBJECTIVE
   ========================================================= */

/*
 * Older Phase 4 code may call this.
 *
 * It still delegates semantic understanding
 * to the backend.
 */

export async function validateDetectionObjective(
  datasetId,
  payload = {}
) {
  let objective = "";

  if (
    typeof payload === "string"
  ) {
    objective = payload;
  } else if (
    payload &&
    typeof payload.objective === "string"
  ) {
    objective =
      payload.objective;
  }

  return analyzePhase4Objective(
    datasetId,
    objective
  );
}


/* =========================================================
   PHASE 4 — VALIDATE OBJECTIVE ALIAS
   ========================================================= */

export async function validateObjective(
  datasetId,
  objective
) {
  return analyzePhase4Objective(
    datasetId,
    objective
  );
}


/* =========================================================
   PHASE 4 — GET OBJECTIVE ANALYSIS
   ========================================================= */

export async function getObjectiveAnalysis(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase4/${encodeURIComponent(
      datasetId
    )}/analysis`
  );
}


/* =========================================================
   PHASE 4 — GET STORED OBJECTIVE
   ========================================================= */

export async function getPhase4Objective(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase4/${encodeURIComponent(
      datasetId
    )}`
  );
}


/* =========================================================
   PHASE 4 — CONFIRM OBJECTIVE
   ========================================================= */

/*
 * Backend:
 * POST /api/phase4/{dataset_id}/confirm
 */

export async function confirmPhase4Objective(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase4/${encodeURIComponent(
      datasetId
    )}/confirm`,
    {
      method: "POST",
    }
  );
}


/* =========================================================
   PHASE 4 — CONFIRM INTENT
   ========================================================= */

export async function confirmPhase4Intent(
  payload = {}
) {
  const datasetId =
    payload?.datasetId ||
    payload?.dataset_id;

  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return confirmPhase4Objective(
    datasetId
  );
}


/* =========================================================
   PHASE 5 — MODEL RECOMMENDATION
   ========================================================= */

/*
 * Backend:
 * POST /api/phase5/{dataset_id}/recommend
 *
 * Payload may contain:
 *
 * - statistical_profile
 * - interpretation
 * - column_profiles
 * - top_n
 */

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
    Number(
      payload?.top_n
    );

  if (
    !Number.isFinite(topN) ||
    topN <= 0
  ) {
    topN = 3;
  }

  return apiRequest(
    `/phase5/${encodeURIComponent(
      datasetId
    )}/recommend`,
    {
      method: "POST",

      body: JSON.stringify({
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
   PHASE 5 — GET MODEL RECOMMENDATIONS
   ========================================================= */

export async function getModelRecommendations(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase5/${encodeURIComponent(
      datasetId
    )}`
  );
}


/* =========================================================
   PHASE 5 — GET RECOMMENDATIONS ALIAS
   ========================================================= */

export async function getPhase5Recommendations(
  datasetId
) {
  return getModelRecommendations(
    datasetId
  );
}


/* =========================================================
   PHASE 5 — GENERATE RECOMMENDATION
   ========================================================= */

export async function generatePhase5Recommendation(
  datasetId,
  payload = {}
) {
  return recommendModels(
    datasetId,
    payload
  );
}


/* =========================================================
   PHASE 5 — GET RECOMMENDATION
   ========================================================= */

export async function getPhase5Recommendation(
  datasetId
) {
  return getModelRecommendations(
    datasetId
  );
}


/* =========================================================
   PHASE 5 — CONFIRM MODEL SELECTION
   ========================================================= */

export async function confirmModelSelection(
  datasetId,
  model
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  if (!model) {
    throw new Error(
      "Please select a model."
    );
  }

  return apiRequest(
    `/phase5/${encodeURIComponent(
      datasetId
    )}/confirm`,
    {
      method: "POST",

      body: JSON.stringify({
        model,
      }),
    }
  );
}


/* =========================================================
   PHASE 5 — CONFIRM RECOMMENDATION
   ========================================================= */

export async function confirmPhase5Recommendation(
  datasetId,
  payload = {}
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase5/${encodeURIComponent(
      datasetId
    )}/confirm`,
    {
      method: "POST",

      body: JSON.stringify(
        payload
      ),
    }
  );
}


/* =========================================================
   PHASE 6 — ANOMALY DETECTION
   ========================================================= */

/*
 * GET
 * /api/phase6/{dataset_id}/config
 */

export async function getPhase6Config(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase6/${encodeURIComponent(
      datasetId
    )}/config`
  );
}


/*
 * POST
 * /api/phase6/{dataset_id}/detect
 */

export async function detectPhase6Anomalies(
  datasetId,
  payload = {}
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  const approach =
    payload?.approach ===
    "combined_score"
      ? "combined_score"
      : "best_score";

  const contamination =
    Number(
      payload?.contamination ??
      0.05
    );

  if (
    !Number.isFinite(
      contamination
    ) ||
    contamination <= 0 ||
    contamination > 0.50
  ) {
    throw new Error(
      "Expected anomaly percentage must be between 1% and 50%."
    );
  }

  const targetColumns =
    Array.isArray(
      payload?.target_columns
    )
      ? payload.target_columns
      : [];

  const explainByColumns =
    Array.isArray(
      payload?.explain_by_columns
    )
      ? payload.explain_by_columns
      : [];

  if (
    targetColumns.length ===
    0
  ) {
    throw new Error(
      "Please select at least one Target / Detection Column."
    );
  }

  return apiRequest(
    `/phase6/${encodeURIComponent(
      datasetId
    )}/detect`,
    {
      method: "POST",

      body: JSON.stringify({
        approach,

        contamination,

        target_columns:
          targetColumns,

        explain_by_columns:
          explainByColumns,
      }),
    }
  );
}


/*
 * GET
 * /api/phase6/{dataset_id}/result
 */

export async function getPhase6Result(
  datasetId
) {
  if (!datasetId) {
    throw new Error(
      "Dataset ID is missing."
    );
  }

  return apiRequest(
    `/phase6/${encodeURIComponent(
      datasetId
    )}/result`
  );
}
/* =========================================================
   AUTOMATIC ANOMALY DISCOVERY API
   ========================================================= */

/*
 * These functions are separate from the existing
 * objective-based Phase 6 detection workflow.
 *
 * Backend prefix:
 * /api/automatic-discovery
 */


/* =========================================================
   AUTOMATIC ANOMALY DISCOVERY — separate API branch
   ========================================================= */

function requireDatasetId(datasetId) {
  if (!datasetId) {
    throw new Error("Dataset ID is missing.");
  }
}


/* =========================================================
   AUTOMATIC DISCOVERY — BENCHMARK
   ========================================================= */

export async function benchmarkAutomaticDiscovery(
  datasetId,
  approach
) {
  requireDatasetId(datasetId);

  if (
    approach !== "univariate" &&
    approach !== "multivariate"
  ) {
    throw new Error(
      "Approach must be univariate or multivariate."
    );
  }

  return apiRequest(
    `/automatic-discovery/${encodeURIComponent(
      datasetId
    )}/benchmark`,
    {
      method: "POST",

      body: JSON.stringify({
        approach,
      }),
    }
  );
}


/* =========================================================
   AUTOMATIC DISCOVERY — RECOMMENDATIONS
   ========================================================= */

export async function getAutomaticDiscoveryRecommendations(
  datasetId,
  scoreMethod = "combined_score"
) {
  requireDatasetId(datasetId);

  const safeMethod =
    scoreMethod === "best_score"
      ? "best_score"
      : "combined_score";

  return apiRequest(
    `/automatic-discovery/${encodeURIComponent(
      datasetId
    )}/recommendations?score_method=${safeMethod}`
  );
}


/* =========================================================
   AUTOMATIC DISCOVERY — FINAL DETECTION
   ========================================================= */

export async function runAutomaticDiscovery(
  datasetId,
  payload = {}
) {
  requireDatasetId(datasetId);

  const scoreMethod =
    payload.score_method === "best_score"
      ? "best_score"
      : "combined_score";

  const contaminationMode =
    payload.contamination_mode === "custom"
      ? "custom"
      : "default";

  const contamination = Number(
    contaminationMode === "default"
      ? 0.10
      : payload.contamination
  );

  if (
    !Number.isFinite(contamination) ||
    contamination < 0.01 ||
    contamination > 0.50
  ) {
    throw new Error(
      "Contamination must be between 0.01 (1%) and 0.50 (50%)."
    );
  }

  const body = {
    score_method: scoreMethod,

    contamination_mode:
      contaminationMode,

    contamination:
      contaminationMode === "default"
        ? 0.10
        : contamination,
  };

  /*
   * Best Score:
   * send the user-selected model.
   *
   * Combined Score:
   * no model is required because backend
   * trains all three fixed Top-3 models.
   */

  if (
    scoreMethod === "best_score" &&
    payload.selected_model
  ) {
    body.selected_model =
      payload.selected_model;
  }

  return apiRequest(
    `/automatic-discovery/${encodeURIComponent(
      datasetId
    )}/detect`,
    {
      method: "POST",

      body: JSON.stringify(body),
    }
  );
}


/* =========================================================
   AUTOMATIC DISCOVERY — QUERY BUILDER
   ========================================================= */

function buildDiscoveryQuery(
  options = {}
) {
  const params =
    new URLSearchParams();

  if (
    options.page != null
  ) {
    params.set(
      "page",
      String(
        Math.max(
          1,
          Number(
            options.page
          ) || 1
        )
      )
    );
  }

  if (
    options.page_size != null
  ) {
    params.set(
      "page_size",
      String(
        Math.min(
          500,
          Math.max(
            1,
            Number(
              options.page_size
            ) || 50
          )
        )
      )
    );
  }

  if (
    options.anomalies_only
  ) {
    params.set(
      "anomalies_only",
      "true"
    );
  }

  /*
   * Backend search:
   * - record number
   * - feature/column values
   * - anomaly score
   */

  if (
    options.search
  ) {
    params.set(
      "search",
      String(
        options.search
      )
    );
  }

  const query =
    params.toString();

  return query
    ? `?${query}`
    : "";
}


/* =========================================================
   AUTOMATIC DISCOVERY — ALL RECORDS
   ========================================================= */

export async function getAutomaticDiscoveryResult(
  datasetId,
  options = {}
) {
  requireDatasetId(datasetId);

  return apiRequest(
    `/automatic-discovery/${encodeURIComponent(
      datasetId
    )}/result${buildDiscoveryQuery(
      options
    )}`
  );
}


/* =========================================================
   AUTOMATIC DISCOVERY — COLUMN RECORDS
   ========================================================= */

export async function getAutomaticDiscoveryColumnResult(
  datasetId,
  columnName,
  options = {}
) {
  requireDatasetId(datasetId);

  if (!columnName) {
    throw new Error(
      "Column name is missing."
    );
  }

  return apiRequest(
    `/automatic-discovery/${encodeURIComponent(
      datasetId
    )}/result/columns/${encodeURIComponent(
      columnName
    )}${buildDiscoveryQuery(
      options
    )}`
  );
}


/* =========================================================
   AUTOMATIC DISCOVERY — RECORD DETAIL
   ========================================================= */

export async function getAutomaticDiscoveryAnomalyDetail(
  datasetId,
  recordNumber,
  columnName = null
) {
  requireDatasetId(datasetId);

  const number =
    Number(recordNumber);

  if (
    !Number.isInteger(number) ||
    number < 1
  ) {
    throw new Error(
      "A valid record number is required."
    );
  }

  const params =
    new URLSearchParams();

  if (columnName) {
    params.set(
      "column_name",
      columnName
    );
  }

  const query =
    params.toString();

  return apiRequest(
    `/automatic-discovery/${encodeURIComponent(
      datasetId
    )}/anomaly/${number}${
      query
        ? `?${query}`
        : ""
    }`
  );
}


/* =========================================================
   AUTOMATIC DISCOVERY — VISUALIZATION
   ========================================================= */

export async function getAutomaticDiscoveryVisualization(
  datasetId,
  columnName = null,
  limit = 1000,
  plotType = "score_distribution"
) {
  requireDatasetId(datasetId);

  const allowedPlots = [
    "score_distribution",
    "feature_vs_score",
    "parallel_coordinates",
  ];

  const safePlot =
    allowedPlots.includes(
      plotType
    )
      ? plotType
      : "score_distribution";

  const params =
    new URLSearchParams({
      limit: String(
        Math.min(
          5000,
          Math.max(
            50,
            Number(limit) || 1000
          )
        )
      ),

      plot_type:
        safePlot,
    });

  if (columnName) {
    params.set(
      "column_name",
      columnName
    );
  }

  return apiRequest(
    `/automatic-discovery/${encodeURIComponent(
      datasetId
    )}/visualization?${params.toString()}`
  );
}


/* =========================================================
   AUTOMATIC DISCOVERY — FEATURE CONTRIBUTION
   ========================================================= */

export async function getAutomaticDiscoveryFeatureContribution(
  datasetId,
  recordNumber,
  topN = 3
) {
  requireDatasetId(datasetId);

  const number =
    Number(recordNumber);

  if (
    !Number.isInteger(number) ||
    number < 1
  ) {
    throw new Error(
      "A valid record number is required."
    );
  }

  const safeTopN =
    Math.min(
      20,
      Math.max(
        1,
        Number(topN) || 3
      )
    );

  return apiRequest(
    `/automatic-discovery/${encodeURIComponent(
      datasetId
    )}/feature-contribution/${number}?top_n=${safeTopN}`
  );
}


/* =========================================================
   PHASE 1 — POSTGRESQL SOURCE
   ========================================================= */

/*
 * Backend: GET /api/phase1/postgres/tables
 * Returns the configured schema and its accessible tables.
 */
export async function getPostgresTables() {
  return apiRequest("/phase1/postgres/tables");
}

/*
 * Backend: POST /api/phase1/postgres/load
 * Body: { table_name: string }
 * Returns the same Phase 1 dataset summary contract as file upload.
 */
export async function loadPostgresTable(tableName) {
  if (typeof tableName !== "string" || !tableName.trim()) {
    throw new Error("Please select a PostgreSQL table.");
  }

  return apiRequest("/phase1/postgres/load", {
    method: "POST",
    body: JSON.stringify({ table_name: tableName.trim() }),
  });
}

