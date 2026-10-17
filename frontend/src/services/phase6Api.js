const API_BASE_URL = `${(import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "")}/api`;

async function handleResponse(response) {
  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    throw new Error(
      data?.detail ||
      data?.message ||
      data?.error ||
      `Request failed with status ${response.status}`
    );
  }

  return data;
}

async function apiRequest(endpoint, options = {}) {
  const response = await fetch(
    `${API_BASE_URL}${endpoint}`,
    {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    }
  );

  return handleResponse(response);
}


/* =========================================================
   PHASE 6 — DETECTION CONFIGURATION
   ========================================================= */

export async function getPhase6Config(datasetId) {
  if (!datasetId) {
    throw new Error("Dataset ID is missing.");
  }

  return apiRequest(
    `/phase6/${encodeURIComponent(datasetId)}/config`
  );
}


/* =========================================================
   PHASE 6 — RUN ANOMALY DETECTION
   ========================================================= */

export async function detectPhase6Anomalies(
  datasetId,
  payload = {}
) {
  if (!datasetId) {
    throw new Error("Dataset ID is missing.");
  }

  if (!payload?.target_columns?.length) {
    throw new Error(
      "Please select at least one Target / Detection Column."
    );
  }

  const contaminationMode =
    payload?.contamination_mode === "custom"
      ? "custom"
      : payload?.contamination_mode === "default"
      ? "default"
      : "";

  if (!contaminationMode) {
    throw new Error(
      "Please select a contamination method to continue."
    );
  }

  const contamination = Number(
    payload?.contamination
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

  const effectiveContamination =
    contaminationMode === "default"
      ? 0.10
      : contamination;

  return apiRequest(
    `/phase6/${encodeURIComponent(datasetId)}/detect`,
    {
      method: "POST",
      body: JSON.stringify({
        approach:
          payload?.approach === "combined_score"
            ? "combined_score"
            : "best_score",

        contamination_mode: contaminationMode,

        contamination: effectiveContamination,

        target_columns: Array.isArray(
          payload?.target_columns
        )
          ? payload.target_columns
          : [],

        explain_by_columns: Array.isArray(
          payload?.explain_by_columns
        )
          ? payload.explain_by_columns
          : [],
      }),
    }
  );
}


/* =========================================================
   PHASE 6 — GET DETECTION RESULTS
   ========================================================= */

export async function getPhase6Result(datasetId) {
  if (!datasetId) {
    throw new Error("Dataset ID is missing.");
  }

  return apiRequest(
    `/phase6/${encodeURIComponent(datasetId)}/result`
  );
}


/* =========================================================
   PHASE 6 — GET ANOMALY DETAILS
   ========================================================= */

export async function getPhase6AnomalyDetail(
  datasetId,
  recordIndex
) {
  if (!datasetId) {
    throw new Error("Dataset ID is missing.");
  }

  if (
    recordIndex === undefined ||
    recordIndex === null ||
    recordIndex === ""
  ) {
    throw new Error("Record index is missing.");
  }

  return apiRequest(
    `/phase6/${encodeURIComponent(
      datasetId
    )}/anomaly/${encodeURIComponent(recordIndex)}`
  );
}


/* =========================================================
   PHASE 6 — GET VISUALIZATION
   ========================================================= */

export async function getPhase6Visualization(
  datasetId,
  filters = {}
) {
  if (!datasetId) {
    throw new Error("Dataset ID is missing.");
  }

  return apiRequest(
    `/phase6/${encodeURIComponent(
      datasetId
    )}/visualization`,
    {
      method: "POST",
      body: JSON.stringify({ filters }),
    }
  );
}


/* =========================================================
   PHASE 6 — DOWNLOAD HELPERS
   ========================================================= */

async function downloadBlob(
  endpoint,
  filename,
  fallbackMessage
) {
  const response = await fetch(
    `${API_BASE_URL}${endpoint}`
  );

  if (!response.ok) {
    let message = fallbackMessage;

    try {
      const data = await response.json();

      message =
        data?.detail ||
        data?.message ||
        message;
    } catch {
      // Response was not JSON.
    }

    throw new Error(message);
  }

  const blob = await response.blob();

  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");

  anchor.href = url;
  anchor.download = filename;

  document.body.appendChild(anchor);

  anchor.click();
  anchor.remove();

  window.setTimeout(
    () => URL.revokeObjectURL(url),
    1000
  );
}


export async function downloadPhase6CSV(datasetId) {
  if (!datasetId) {
    throw new Error("Dataset ID is missing.");
  }

  return downloadBlob(
    `/phase6/${encodeURIComponent(datasetId)}/csv`,
    "anomaly_records.csv",
    "Unable to download anomaly CSV."
  );
}


export async function downloadPhase6Report(datasetId) {
  if (!datasetId) {
    throw new Error("Dataset ID is missing.");
  }

  return downloadBlob(
    `/phase6/${encodeURIComponent(datasetId)}/report`,
    "ANOMALY_Phase6_Report.pdf",
    "Unable to download the Phase 6 report."
  );
}


/* =========================================================
   PHASE 6 — API BASE URL
   ========================================================= */

export function getPhase6ApiBaseUrl() {
  return API_BASE_URL;
}


/* =========================================================
   AUTOMATIC ANOMALY DISCOVERY — RE-EXPORTS
   ========================================================= */

export {
  benchmarkAutomaticDiscovery,
  getAutomaticDiscoveryRecommendations,
  runAutomaticDiscovery,
  getAutomaticDiscoveryResult,
  getAutomaticDiscoveryColumnResult,
  getAutomaticDiscoveryAnomalyDetail,
  getAutomaticDiscoveryVisualization,
} from "./api";
