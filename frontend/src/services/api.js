const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");


/* =========================================================
   GENERIC API REQUEST
   ========================================================= */

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);

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

    throw new Error(
      typeof detail === "string"
        ? detail
        : JSON.stringify(detail)
    );
  }

  return body;
}


/* =========================================================
   PHASE 1 — DATASET ANALYSIS
   ========================================================= */

export async function uploadDataset(file) {
  const form = new FormData();

  form.append("file", file);

  return request("/api/phase1/analyze", {
    method: "POST",
    body: form,
  });
}


/* =========================================================
   PHASE 2 — COLUMN DETAILS
   ========================================================= */

export async function getColumnDetails(
  datasetId,
  columnName
) {
  return request(
    `/api/phase2/${encodeURIComponent(
      datasetId
    )}/column/${encodeURIComponent(columnName)}`
  );
}


/* =========================================================
   PHASE 2 — COLUMN SELECTION
   ========================================================= */

export async function saveSelection(
  datasetId,
  selectedColumns
) {
  return request(
    `/api/phase2/${encodeURIComponent(datasetId)}/selection`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        selected_columns: selectedColumns,
      }),
    }
  );
}


export async function confirmSelection(
  datasetId
) {
  return request(
    `/api/phase2/${encodeURIComponent(datasetId)}/confirm`,
    {
      method: "POST",
    }
  );
}


/* =========================================================
   PHASE 3 — PREPROCESSING INSPECTION
   ========================================================= */

/*
 * Get the complete preprocessing inspection.
 *
 * Used when Phase 3 is opened.
 */
export async function getPreprocessingInspection(
  datasetId
) {
  return request(
    `/api/phase3/${encodeURIComponent(
      datasetId
    )}/preprocessing/inspection`
  );
}


/*
 * Get records containing missing values
 * for one specific column.
 *
 * Used by App.jsx:
 * payload.kind === "missing-column"
 */
export async function getMissingColumnInspection(
  datasetId,
  columnName
) {
  return request(
    `/api/phase3/${encodeURIComponent(
      datasetId
    )}/preprocessing/inspection/missing/${encodeURIComponent(
      columnName
    )}`
  );
}

export async function getDuplicateColumnInspection(
  datasetId,
  columnName
) {
  return request(
    `/api/phase3/${encodeURIComponent(
      datasetId
    )}/preprocessing/inspection/duplicates/${encodeURIComponent(
      columnName
    )}`
  );
}
/* =========================================================
   PHASE 3 — PREPROCESS DATASET
   ========================================================= */

export async function preprocessDataset(
  datasetId,
  selectedColumns
) {
  return request(
    `/api/phase3/${encodeURIComponent(
      datasetId
    )}/preprocess`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        selected_columns: selectedColumns,
      }),
    }
  );
}


/* =========================================================
   PHASE 3 — DATASET PREVIEW
   ========================================================= */

export async function getPreview(
  datasetId,
  page = 1,
  pageSize = 10
) {
  return request(
    `/api/phase3/${encodeURIComponent(
      datasetId
    )}/preview?page=${page}&page_size=${pageSize}`
  );
}


/* =========================================================
   PHASE 3 — STATISTICAL ANALYSIS
   ========================================================= */

export async function runStatisticalAnalysis(
  datasetId,
  selectedColumns
) {
  return request(
    `/api/phase3/${encodeURIComponent(
      datasetId
    )}/statistical-analysis`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        selected_columns: selectedColumns,
      }),
    }
  );
}


/* =========================================================
   HEALTH CHECK
   ========================================================= */

export async function healthCheck() {
  return request("/health");
}


/* =========================================================
   EXPORT BASE URL
   ========================================================= */

export { API_BASE_URL };

