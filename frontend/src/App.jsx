import { useEffect, useState } from "react";
import Phase6 from "./pages/Phase6";
import StatisticalApproach from "./components/StatisticalApproach";
import { automaticDiscoveryApi } from "./services/automaticDiscoveryApi";
import UnivariateAnalysis from "./components/UnivariateAnalysis";
import MultivariateAnalysis from "./components/MultivariateAnalysis";
import {
  confirmSelection,
  getColumnDetails,
  getPreview,
  downloadProcessedDataset,
  getPreprocessingInspection,
  saveSelection,
  preprocessDataset,
  runStatisticalAnalysis,
  uploadDataset,
  getPostgresTables,
  loadPostgresTable,
  analyzePhase4Objective,
  confirmPhase4Objective,
  recommendModels,
  getUnivariateStatisticalDetection,
  getMultivariateStatisticalDetection,
  benchmarkAutomaticDiscovery,
  getAutomaticDiscoveryRecommendations,
  runAutomaticDiscovery,
  getAutomaticDiscoveryResult,
  getAutomaticDiscoveryColumnResult,
  getAutomaticDiscoveryAnomalyDetail,
  getAutomaticDiscoveryVisualization,
  getAutomaticDiscoveryFeatureContribution,
} from "./services/api";
import "./App.css";

/* =========================================================
   CONSTANTS
========================================================= */

const PHASES = [
  ["01", "Dataset Analysis"],
  ["02", "Column Selection"],
  ["03", "Preprocessing & Analysis"],
  ["04", "Objective Understanding"],
  ["05", "Model Recommendation"],
  ["06", "Anomaly Detection & Visualization"],
  
];

const ANOMALY_TYPES = [
  "Point",
  "Contextual",
  "Collective",
];

const DETECTION_SCOPES = [
  "Global",
  "Local",
];

const TEMPORAL_BEHAVIORS = [
  "Non-Temporal",
  "Temporal",
];

const ANALYSES = [
  ["overview", "1. Dataset Size & Dimensionality"],
  ["types", "2. Data Type & Feature Composition"],
  ["distribution", "3. Distribution Analysis"],
  ["extreme", "4. Extreme Value Analysis"],
  ["scale", "5. Feature Scale Analysis"],
  ["correlation", "6. Correlation Analysis"],
  ["cluster", "7. Cluster Structure Analysis"],
  ["density", "8. Local Density & Neighborhood Analysis"],
  ["temporal", "9. Temporal Structure Analysis"],
  ["timeseries", "10. Time-Series Pattern Analysis"],
];
/* =========================================================
   PHASE 4 OBJECTIVE ATTRIBUTE HELPERS
========================================================= */

function normalizeObjectiveColumns(value) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (typeof item === "string") {
        return item.trim();
      }

      if (item && typeof item === "object") {
        return String(
          item.column ||
          item.name ||
          item.column_name ||
          item.field ||
          ""
        ).trim();
      }

      return "";
    })
    .filter(Boolean);
}


function getObjectiveRequiredColumns(objectiveValidation) {
  const understanding =
    objectiveValidation?.objective_understanding ||
    objectiveValidation?.objective ||
    objectiveValidation ||
    {};

  const primary =
    normalizeObjectiveColumns(
      understanding?.attributes_involved ||
      objectiveValidation?.attributes_involved ||
      []
    );

  if (primary.length > 0) {
    return [...new Set(primary)];
  }

  /*
   * Compatibility fallback for older Phase 4 responses.
   * These are still backend-returned semantic attributes; no
   * column names are invented in the frontend.
   */
  const fallback = [
    ...normalizeObjectiveColumns(
      understanding?.target_columns ||
      objectiveValidation?.target_columns ||
      []
    ),
    ...normalizeObjectiveColumns(
      understanding?.reference_columns ||
      objectiveValidation?.reference_columns ||
      []
    ),
    ...normalizeObjectiveColumns(
      understanding?.context_columns ||
      objectiveValidation?.context_columns ||
      []
    ),
  ];

  return [...new Set(fallback)];
}


function getMissingObjectiveColumns(
  objectiveValidation,
  selectedColumns
) {
  const required =
    getObjectiveRequiredColumns(
      objectiveValidation
    );

  const selected =
    new Set(
      normalizeObjectiveColumns(
        selectedColumns
      )
    );

  return required.filter(
    (column) => !selected.has(column)
  );
}


/* =========================================================
   MAIN APP
========================================================= */

function App() {
  const [summary, setSummary] = useState(null);
  const [file, setFile] = useState(null);

  const [activePhase, setActivePhase] =
    useState(1);

  /* =======================================================
     STATISTICAL APPROACH
  ======================================================= */

  const [statisticalApproach, setStatisticalApproach] =
    useState("");

  const [statisticalResult, setStatisticalResult] =
    useState(null);

  const [statisticalLoading, setStatisticalLoading] =
    useState(false);

  const [statisticalView, setStatisticalView] =
    useState("");


  /* =======================================================
     AUTOMATIC ANOMALY DISCOVERY — isolated state
     ======================================================= */
  const [autoDiscoveryView, setAutoDiscoveryView] = useState("");
  const [autoDiscoveryApproach, setAutoDiscoveryApproach] = useState("");
  const [autoDiscoveryBenchmark, setAutoDiscoveryBenchmark] = useState(null);
  const [autoDiscoveryRecommendations, setAutoDiscoveryRecommendations] = useState(null);
  const [autoDiscoveryScoreMethod, setAutoDiscoveryScoreMethod] = useState("combined_score");
  const [autoDiscoverySelectedModel, setAutoDiscoverySelectedModel] = useState("");
  const [autoDiscoveryContaminationMode, setAutoDiscoveryContaminationMode] = useState("default");
  const [autoDiscoveryContamination, setAutoDiscoveryContamination] = useState(0.10);
  const [autoDiscoveryDetection, setAutoDiscoveryDetection] = useState(null);
  const [autoDiscoveryRecords, setAutoDiscoveryRecords] = useState(null);
  const [autoDiscoveryColumn, setAutoDiscoveryColumn] = useState("");
  const [autoDiscoveryDetail, setAutoDiscoveryDetail] = useState(null);
  const [autoDiscoveryVisualization, setAutoDiscoveryVisualization] = useState(null);
  const [autoDiscoveryLoading, setAutoDiscoveryLoading] = useState(false);
  const [autoDiscoveryPage, setAutoDiscoveryPage] = useState(1);
  const [autoDiscoveryAnomaliesOnly, setAutoDiscoveryAnomaliesOnly] = useState(false);
  const [autoDiscoverySearch, setAutoDiscoverySearch] = useState("");
  const [autoDiscoveryPlotType, setAutoDiscoveryPlotType] = useState("score_distribution");
  const [autoDiscoverySelectedPoint, setAutoDiscoverySelectedPoint] = useState(null);
  const [autoDiscoveryContribution, setAutoDiscoveryContribution] = useState(null);

  /* =======================================================
     PHASE 2
  ======================================================= */

  const [selectedColumns, setSelectedColumns] =
    useState([]);

  const [confirmed, setConfirmed] =
    useState(false);

  const [confirmationOpen, setConfirmationOpen] =
    useState(false);

  const [infoColumn, setInfoColumn] =
    useState(null);

  const [selectedDetail, setSelectedDetail] =
    useState(null);


  /* =======================================================
     PHASE 3
  ======================================================= */

  const [inspectionData, setInspectionData] =
    useState(null);

  const [preprocessResult, setPreprocessResult] =
    useState(null);

  const [preview, setPreview] =
    useState(null);

  const [previewPage, setPreviewPage] =
    useState(1);

  const [analysis, setAnalysis] =
    useState(null);

  const [openSections, setOpenSections] =
    useState({});


  /* =======================================================
     LOADING
  ======================================================= */

  const [loading, setLoading] =
    useState(false);

  const [phase3Loading, setPhase3Loading] =
    useState(false);

  const [analysisLoading, setAnalysisLoading] =
    useState(false);

  const [inspectionLoading, setInspectionLoading] =
    useState(false);

  const [objectiveLoading, setObjectiveLoading] =
    useState(false);

  const [recommendationLoading, setRecommendationLoading] =
    useState(false);


  /* =======================================================
     PHASE 4
  ======================================================= */

  const [anomalyType, setAnomalyType] =
    useState("");

  const [detectionScope, setDetectionScope] =
    useState("");

  const [temporalBehavior, setTemporalBehavior] =
    useState("");

  const [detectionObjective, setDetectionObjective] =
    useState("");

  const [objectiveValidation, setObjectiveValidation] =
    useState(null);

  const [phase4Complete, setPhase4Complete] =
    useState(false);


  /* =======================================================
     PHASE 5
  ======================================================= */

  const [recommendations, setRecommendations] =
    useState(null);


  /* =======================================================
     ERROR
  ======================================================= */

  const [error, setError] =
    useState("");


  const datasetId =
    summary?.dataset_id;

/* =========================================================
   RESET PHASE 4 / 5
========================================================= */

  function resetPhase4And5(clearObjective = true) {
    setAnomalyType("");
    setDetectionScope("");
    setTemporalBehavior("");

    if (clearObjective) {
      setDetectionObjective("");
    }

    setObjectiveValidation(null);
    setPhase4Complete(false);

    setRecommendations(null);
  }


/* =========================================================
   RESET FOR NEW FILE
========================================================= */

  function resetForNewFile() {
    setSummary(null);
    setFile(null);

    setActivePhase(1);

    setSelectedColumns([]);
    setConfirmed(false);
    setConfirmationOpen(false);

    setInfoColumn(null);
    setSelectedDetail(null);

    setInspectionData(null);
    setPreprocessResult(null);
    setPreview(null);
    setPreviewPage(1);

    setAnalysis(null);
    setOpenSections({
      overview: true,
    });

    setStatisticalApproach("");
    setStatisticalResult(null);
    setStatisticalLoading(false);
    setStatisticalView("");
    resetAutomaticDiscovery();

    resetPhase4And5();

    setError("");
  }


/* =========================================================
   FILE UPLOAD
========================================================= */

  async function handleFileSelected(nextFile) {
    if (!nextFile) {
      return;
    }

    resetForNewFile();

    setFile(nextFile);
    setLoading(true);
    setError("");

    try {
      const result =
        await uploadDataset(nextFile);

      setSummary(result);

      /*
       * Start with every uploaded column selected.
       * User can then remove columns in Phase 2.
       */
      const columns =
        Array.isArray(
          result?.all_column_names
        )
          ? result.all_column_names
          : [];

      setSelectedColumns(columns);

      setActivePhase(1);
    } catch (err) {
      setError(
        err?.message ||
          "Unable to analyze dataset."
      );
    } finally {
      setLoading(false);
    }
  }


  /* =========================================================
     POSTGRESQL TABLE LOAD
     Uses the same Phase 1 summary/session contract as CSV.
     ========================================================= */
  async function handlePostgresTableSelected(tableName) {
    if (!tableName) {
      setError("Please select a PostgreSQL table.");
      return;
    }

    resetForNewFile();
    setFile({ name: `${tableName}.csv` });
    setLoading(true);
    setError("");

    try {
      const result = await loadPostgresTable(tableName);

      setSummary(result);

      const columns = Array.isArray(result?.all_column_names)
        ? result.all_column_names
        : [];

      if (columns.length === 0) {
        throw new Error(
          "The selected PostgreSQL table was loaded, but no columns were returned."
        );
      }

      setSelectedColumns(columns);
      setActivePhase(1);
    } catch (err) {
      setSummary(null);
      setFile(null);
      setSelectedColumns([]);
      setError(
        err?.message ||
          "Unable to load the selected PostgreSQL table."
      );
    } finally {
      setLoading(false);
    }
  }




  
/* =========================================================
   COLUMN INFORMATION
========================================================= */

async function chooseColumn(column) {
  if (!column) {
    return;
  }

  /* -------------------------------------------------------
     Clicking the same information button closes it.
  ------------------------------------------------------- */

  if (infoColumn === column) {
    setInfoColumn(null);
    setSelectedDetail(null);
    return;
  }

  setInfoColumn(column);

  /* -------------------------------------------------------
     Get cached Phase 1 profile.
     We NEVER store the complete profile in selectedDetail.
  ------------------------------------------------------- */

  const cached =
    summary?.column_details?.[column] || {};

  const cachedMissingPercentage =
    cached?.missing_percentage ??
    (
      Number(summary?.rows) > 0
        ? (
            Number(
              cached?.missing_values || 0
            ) /
            Number(summary.rows)
          ) *
          100
        : 0
    );

  /*
   * STRICT FIVE-FIELD OBJECT.
   *
   * Nothing else is allowed into selectedDetail.
   */
  const cleanCachedDetail = {
    column_name:
      column,
    role:
      cached?.role ||
      "—",
    data_type:
      cached?.dtype ||
      cached?.data_type ||
      "—",
    missing_percentage:
      cachedMissingPercentage,
    llm_description:
      "Generating description...",
  };

  setSelectedDetail(
    cleanCachedDetail
  );

  /* -------------------------------------------------------
     Ask backend for the latest LLM description.
  ------------------------------------------------------- */

  if (!datasetId) {
    return;
  }

  try {
    const result =
      await getColumnDetails(
        datasetId,
        column
      );

    console.log("COLUMN DETAILS API RESULT:", result);
    console.log(
      "BACKEND DETAILS JSON:",
      JSON.stringify(result?.details, null, 2)
    );

    const backendDetails =
      result?.details || {};

    /*
     * IMPORTANT:
     *
     * DO NOT DO THIS:
     *
     * {
     *   ...current,
     *   ...backendDetails
     * }
     *
     * because that brings all backend fields
     * into the popup.
     */

    const backendMissingPercentage =
      backendDetails?.missing_percentage ??
      cleanCachedDetail.missing_percentage ??
      0;

    const cleanBackendDetail = {
      column_name:
        backendDetails?.column_name ||
        backendDetails?.name ||
        backendDetails?.column ||
        column,

      role:
        backendDetails?.role ||
        cleanCachedDetail.role ||
        "—",

      data_type:
        backendDetails?.data_type ||
        backendDetails?.dtype ||
        cleanCachedDetail.data_type ||
        "—",

      missing_percentage:
        backendMissingPercentage,

      llm_description:
        backendDetails?.llm_description ||
        backendDetails?.description ||
        "No description available.",
    };

    /*
     * Replace selectedDetail with ONLY the five
     * permitted fields.
     */
    setSelectedDetail(
      cleanBackendDetail
    );

  } catch (err) {

    /*
     * The cached five-field information remains
     * visible if the backend detail request fails.
     */
    setError(
      err?.message ||
        "Unable to load column information."
    );
  }
}



  function closeColumnInfo() {
    setInfoColumn(null);
    setSelectedDetail(null);
  }


/* =========================================================
   COLUMN SELECTION
========================================================= */

  function toggleColumn(column) {
    setSelectedColumns(
      (current) => {
        if (current.includes(column)) {
          return current.filter(
            (item) => item !== column
          );
        }

        return [
          ...current,
          column,
        ];
      }
    );

    /*
     * Changing Phase 2 invalidates all downstream
     * processing and detection configuration.
     */
    setConfirmed(false);
    setConfirmationOpen(false);

    setInspectionData(null);
    setPreprocessResult(null);
    setPreview(null);
    setPreviewPage(1);
    setAnalysis(null);

    setStatisticalApproach("");
    setStatisticalResult(null);
    setStatisticalLoading(false);
    setStatisticalView("");

    /*
     * Keep the user's Phase 4 objective while invalidating its
     * previous interpretation. It will be revalidated after
     * Phase 3 is completed again.
     */
    resetPhase4And5(false);
  }


/* =========================================================
   CONFIRM SELECTION
========================================================= */

  async function handleConfirmSelection() {
    if (
      !datasetId ||
      selectedColumns.length === 0
    ) {
      setError(
        "Please select at least one column."
      );

      return;
    }

    setPhase3Loading(true);
    setError("");

    try {
      /*
       * One canonical Phase 2 confirmation request.
       * The selected columns are sent with the request.
       */
      const result =
        await confirmSelection(
          datasetId,
          selectedColumns
        );

      console.log(
        "PHASE 2 CONFIRMATION RESULT:",
        result
      );

      setConfirmed(true);
      setConfirmationOpen(true);
    } catch (err) {
      setError(
        err?.message ||
          "Unable to confirm column selection."
      );
    } finally {
      setPhase3Loading(false);
    }
  }


/* =========================================================
   PROCEED TO PHASE 3
========================================================= */

  function proceedToPreprocessing() {
    setConfirmationOpen(false);

    setActivePhase(3);

    /*
     * Load inspection separately.
     */
    loadPhase3Inspection();
  }


/* =========================================================
   EDIT SELECTION
========================================================= */

  function editSelection() {
    setConfirmationOpen(false);

    setActivePhase(2);
  }


/* =========================================================
   LOAD PHASE 3 INSPECTION
========================================================= */

  async function loadPhase3Inspection() {
    if (!datasetId) {
      return;
    }

    setPhase3Loading(true);
    setError("");

    try {
      const result =
        await getPreprocessingInspection(
          datasetId
        );

      setInspectionData(result);
    } catch (err) {
      setError(
        err?.message ||
          "Unable to load preprocessing inspection."
      );
    } finally {
      setPhase3Loading(false);
    }
  }


/* =========================================================
   OPEN PHASE 3
========================================================= */

  async function openPhase3() {
    if (
      !datasetId ||
      !confirmed
    ) {
      return;
    }

    setActivePhase(3);

    await loadPhase3Inspection();

    /*
     * If preprocessing already happened,
     * load preview separately.
     */
    if (preprocessResult) {
      await loadPreview(
        previewPage
      );
    }
  }


/* =========================================================
   PREPROCESS DATASET
========================================================= */

  async function handlePreprocess() {
    if (
      !datasetId ||
      selectedColumns.length === 0 ||
      !confirmed
    ) {
      return false;
    }

    setPhase3Loading(true);
    setError("");

    /*
     * Clear only old preview/analysis.
     * Do NOT clear the entire Phase 3 screen.
     */
    setPreview(null);
    setAnalysis(null);

    try {
      /*
       * MAIN BACKEND PREPROCESSING CALL
       */
      const result =
        await preprocessDataset(
          datasetId,
          selectedColumns
        );

      /*
       * IMPORTANT:
       * Set this immediately.
       *
       * This prevents a preview/inspection problem
       * from making the entire page appear blank.
       */
      setPreprocessResult(result);
      setPreviewPage(1);

      /*
       * Inspection and preview are intentionally
       * loaded independently.
       */
      try {
        const inspectionResult =
          await getPreprocessingInspection(
            datasetId
          );

        setInspectionData(
          inspectionResult
        );
      } catch (inspectionError) {
        setError(
          inspectionError?.message ||
            "Preprocessing completed, but inspection could not be refreshed."
        );
      }

      try {
        const previewResult =
          await getPreview(
            datasetId,
            1,
            10
          );

        setPreview(
          previewResult
        );
      } catch (previewError) {
        /*
         * Preview failure must NOT remove
         * the preprocessing result.
         */
        setError(
          previewError?.message ||
            "Preprocessing completed, but preview could not be loaded."
        );
      }

      /*
       * Phase 2/3 changes invalidate the old Phase 4 result,
       * but the user's objective itself is retained so it can
       * be automatically revalidated after returning to Phase 4.
       */
      resetPhase4And5(false);

      setOpenSections({
        overview: true,
      });

      setActivePhase(3);
      return true;
    } catch (err) {
      /*
       * Actual preprocessing backend failure.
       */
      setError(
        err?.message ||
          "Unable to preprocess dataset."
      );
      return false;
    } finally {
      setPhase3Loading(false);
    }
  }


/* =========================================================
   LOAD PREVIEW
========================================================= */

  async function loadPreview(page = 1) {
    if (
      !datasetId ||
      !preprocessResult
    ) {
      return;
    }

    setPhase3Loading(true);
    setError("");

    try {
      const result =
        await getPreview(
          datasetId,
          page,
          10
        );

      setPreview(result);

      setPreviewPage(
        Number(result?.page) ||
          page
      );
    } catch (err) {
      setError(
        err?.message ||
          "Unable to load dataset preview."
      );
    } finally {
      setPhase3Loading(false);
    }
  }


  /* =========================================================
     DOWNLOAD PROCESSED DATASET
  ========================================================= */

  async function handleDownloadProcessedDataset() {
    if (!datasetId || !preprocessResult) {
      setError(
        "Run Phase 3 preprocessing before downloading the processed dataset."
      );
      return false;
    }

    setPhase3Loading(true);
    setError("");

    try {
      await downloadProcessedDataset(datasetId);
      return true;
    } catch (err) {
      setError(
        err?.message ||
          "Unable to download the processed dataset."
      );
      return false;
    } finally {
      setPhase3Loading(false);
    }
  }


/* =========================================================
   PAGE CHANGE
========================================================= */

  async function changePreviewPage(page) {
    await loadPreview(page);
  }


/* =========================================================
   STATISTICAL ANALYSIS
========================================================= */

  async function handleRunAnalysis() {
    if (
      !datasetId ||
      !preprocessResult ||
      selectedColumns.length === 0
    ) {
      setError(
        "Preprocess the selected dataset before running statistical analysis."
      );

      return false;
    }

    setAnalysisLoading(true);
    setError("");

    try {
      const result =
        await runStatisticalAnalysis(
          datasetId,
          selectedColumns
        );

      setAnalysis(result);

      setOpenSections({
        overview: true,
      });
      return true;
    } catch (err) {
      setError(
        err?.message ||
          "Unable to calculate statistical analysis."
      );
      return false;
    } finally {
      setAnalysisLoading(false);
    }
  }


/* =========================================================
   RECORD INSPECTION
========================================================= */

  function inspect(payload) {
    if (!payload) {
      return;
    }

    setInspectionLoading(true);
    setError("");

    try {
      let focusedRecords = [];

      if (
        payload.kind ===
        "missing-column"
      ) {
        const columnStats =
          inspectionData?.columns?.find(
            (item) =>
              item.column ===
              payload.column
          );

        focusedRecords =
          columnStats?.missing_records ||
          [];
      }

      else if (
        payload.kind ===
        "duplicate-column"
      ) {
        const columnStats =
          inspectionData?.columns?.find(
            (item) =>
              item.column ===
              payload.column
          );

        focusedRecords =
          columnStats?.duplicate_records ||
          [];
      }

      else if (
        payload.kind ===
        "missing-total"
      ) {
        const allMissing =
          inspectionData?.allMissingRecords ||
          [];

        focusedRecords =
          allMissing.flatMap(
            (item) =>
              (item.records || []).map(
                (record) => ({
                  ...record,
                  column:
                    item.column,
                })
              )
          );
      }

      else if (
        payload.kind ===
        "duplicate-total"
      ) {
        focusedRecords =
          inspectionData?.allDuplicateRecords ||
          [];
      }

      setInspectionData(
        (current) => ({
          ...(current || {}),
          focused:
            focusedRecords,
        })
      );

      setInspection(
        payload
      );
    } catch (err) {
      setError(
        err?.message ||
          "Unable to inspect records."
      );
    } finally {
      setInspectionLoading(false);
    }
  }

  const [inspection, setInspection] =
    useState(null);


/* =========================================================
   PHASE 4
   OBJECTIVE VALIDATION
========================================================= */

  async function handleValidateObjective() {
    if (
      !datasetId ||
      !analysis ||
      !detectionObjective.trim()
    ) {
      setError(
        "Please complete Phase 3 statistical analysis and enter your detection objective."
      );

      return;
    }

    setObjectiveLoading(true);
    setObjectiveValidation(null);
    setPhase4Complete(false);
    setRecommendations(null);
    setError("");

    try {
      /*
       * Phase 4 semantic interpretation.
       *
       * The backend determines which dataset attributes are
       * involved in the objective. The frontend does NOT infer
       * domain-specific columns.
       */
      const result =
        await analyzePhase4Objective(
          datasetId,
          detectionObjective.trim()
        );

      console.log(
        "PHASE 4 API RESULT:",
        result
      );

      console.log(
        "PHASE 4 BACKEND JSON:",
        JSON.stringify(result, null, 2)
      );

      const understanding =
        result?.objective_understanding ||
        result?.objective ||
        result ||
        {};

      /*
       * Deterministic Phase 2 validation:
       *
       * required = attributes identified by the backend
       * selected = latest React Phase 2 selection
       *
       * No LLM is used for this comparison.
       */
      const requiredColumns =
        getObjectiveRequiredColumns(
          result
        );

      const missingColumns =
        getMissingObjectiveColumns(
          result,
          selectedColumns
        );

      const attributeSelectionValid =
        missingColumns.length === 0;

      /*
       * Keep the complete backend response, while adding only
       * frontend validation metadata. Existing Phase 4 fields
       * remain unchanged.
       */
      const validationResult = {
        ...result,
        frontend_attribute_selection_validation: {
          valid: attributeSelectionValid,
          required_columns: requiredColumns,
          selected_columns:
            normalizeObjectiveColumns(
              selectedColumns
            ),
          missing_columns: missingColumns,
          status: attributeSelectionValid
            ? "Validation Passed — All required attributes selected"
            : "Validation Failed — Required attribute missing",
        },
      };

      setObjectiveValidation(
        validationResult
      );

      /*
       * These values still come only from the backend.
       */
      const interpretedObjective =
        understanding?.interpreted_objective ||
        understanding?.objective_understanding ||
        understanding?.explanation ||
        result?.interpreted_objective ||
        "";

      const inferredAnomalyType =
        understanding?.anomaly_type ||
        result?.anomaly_type ||
        "";

      const inferredScope =
        understanding?.comparison_scope ||
        result?.comparison_scope ||
        "";

      const inferredTemporal =
        understanding?.temporal_requirement ||
        result?.temporal_requirement ||
        "";

      setAnomalyType(
        inferredAnomalyType
      );

      setDetectionScope(
        inferredScope
      );

      setTemporalBehavior(
        inferredTemporal
      );

      /*
       * Phase 4 is considered complete only when:
       * 1. the objective was understood,
       * 2. an anomaly type was returned, and
       * 3. every required objective attribute is present
       *    in the confirmed/latest Phase 2 selection.
       *
       * This is what blocks Phase 5 when an attribute is missing.
       */
      setPhase4Complete(
        Boolean(
          String(
            interpretedObjective
          ).trim()
        ) &&
        Boolean(
          String(
            inferredAnomalyType
          ).trim()
        ) &&
        attributeSelectionValid
      );

    } catch (err) {
      setObjectiveValidation(null);
      setPhase4Complete(false);

      setError(
        err?.message ||
          "Unable to understand the detection objective."
      );
    } finally {
      setObjectiveLoading(false);
    }
  }


  /*
   * Enter Phase 4 without triggering a new objective analysis.
   *
   * Phase 4 analysis is an explicit user action. When the user
   * returns to Phase 4 from another phase, the existing objective
   * interpretation stored in this component remains visible.
   * Groq is called again only when the user clicks
   * "Understand Objective".
   */
  function enterPhase4() {
    setStatisticalView("");
    setStatisticalApproach("ml");
    setStatisticalResult(null);
    setActivePhase(4);
  }


  function resetAutomaticDiscovery() {
    setAutoDiscoveryView("");
    setAutoDiscoveryApproach("");
    setAutoDiscoveryBenchmark(null);
    setAutoDiscoveryRecommendations(null);
    setAutoDiscoveryScoreMethod("combined_score");
    setAutoDiscoverySelectedModel("");
    setAutoDiscoveryContaminationMode("default");
    setAutoDiscoveryContamination(0.10);
    setAutoDiscoveryDetection(null);
    setAutoDiscoveryRecords(null);
    setAutoDiscoveryColumn("");
    setAutoDiscoveryDetail(null);
    setAutoDiscoveryVisualization(null);
    setAutoDiscoveryLoading(false);
    setAutoDiscoveryPage(1);
    setAutoDiscoveryAnomaliesOnly(false);
    setAutoDiscoverySearch("");
    setAutoDiscoveryPlotType("score_distribution");
    setAutoDiscoverySelectedPoint(null);
    setAutoDiscoveryContribution(null);
  }

  function openAutomaticDiscovery() {
    if (!datasetId || !preprocessResult) {
      setError("Complete Phase 3 preprocessing before using Automatic Anomaly Discovery.");
      return;
    }
    resetAutomaticDiscovery();
    setAutoDiscoveryView("setup");
    setActivePhase(4);
    setError("");
  }

  function handleChooseAutomaticDiscoveryApproach(approach) {
    if (approach !== "univariate" && approach !== "multivariate") return;
    setAutoDiscoveryApproach(approach);
    setError("");
  }

  async function handleAutomaticDiscoveryBenchmark(approach = autoDiscoveryApproach) {
    if (!datasetId || !preprocessResult) {
      setError("Complete Phase 3 preprocessing before benchmarking models.");
      return;
    }
    if (!approach) {
      setError("Choose Univariate or Multivariate before continuing.");
      return;
    }
    setAutoDiscoveryLoading(true);
    setError("");
    try {
      const benchmark = await benchmarkAutomaticDiscovery(datasetId, approach);
      const recommendations = await getAutomaticDiscoveryRecommendations(datasetId, autoDiscoveryScoreMethod);
      setAutoDiscoveryApproach(approach);
      setAutoDiscoveryBenchmark(benchmark);
      setAutoDiscoveryRecommendations(recommendations);
      const topThree = Array.isArray(recommendations?.recommendations)
        ? recommendations.recommendations.slice(0, 3)
        : [];
      setAutoDiscoverySelectedModel(
        autoDiscoveryScoreMethod === "combined_score"
          ? topThree.map((item) => item.model).join(",")
          : topThree[0]?.model || ""
      );
      setAutoDiscoveryView("recommendations");
    } catch (err) {
      setError(err?.message || "Unable to benchmark models for Automatic Anomaly Discovery.");
    } finally {
      setAutoDiscoveryLoading(false);
    }
  }

  async function handleAutomaticDiscoveryScoreMethod(method) {
    const safeMethod = method === "best_score" ? "best_score" : "combined_score";
    setAutoDiscoveryScoreMethod(safeMethod);
    if (!datasetId || !autoDiscoveryBenchmark) return;
    setAutoDiscoveryLoading(true);
    setError("");
    try {
      const recommendations = await getAutomaticDiscoveryRecommendations(datasetId, safeMethod);
      setAutoDiscoveryRecommendations(recommendations);
      const topThree = Array.isArray(recommendations?.recommendations)
        ? recommendations.recommendations.slice(0, 3)
        : [];

      if (safeMethod === "combined_score") {
        setAutoDiscoverySelectedModel(topThree.map((item) => item.model).join(","));
      } else {
        const currentModels = String(autoDiscoverySelectedModel || "")
          .split(",")
          .map((model) => model.trim())
          .filter(Boolean);
        const selected = currentModels.find((model) =>
          topThree.some((item) => item.model === model)
        );
        setAutoDiscoverySelectedModel(selected || topThree[0]?.model || "");
      }
    } catch (err) {
      setError(err?.message || "Unable to update model recommendations.");
    } finally {
      setAutoDiscoveryLoading(false);
    }
  }

  async function handleRunAutomaticDiscovery() {
    if (!datasetId || !autoDiscoveryApproach) {
      setError("Benchmark the dataset and complete the detection settings first.");
      return;
    }
    if (autoDiscoveryScoreMethod === "best_score" && !autoDiscoverySelectedModel) {
      setError("Select one of the three recommended models for Best Score detection.");
      return;
    }
    if (autoDiscoveryScoreMethod === "combined_score") {
      const topThreeModels = (autoDiscoveryRecommendations?.recommendations || [])
        .slice(0, 3)
        .map((item) => item.model)
        .filter(Boolean);
      const selectedModels = String(autoDiscoverySelectedModel || "")
        .split(",")
        .map((model) => model.trim())
        .filter(Boolean);
      if (topThreeModels.length !== 3 || selectedModels.length !== 3 || topThreeModels.some((model) => !selectedModels.includes(model))) {
        setError("Combined Score requires all three Top 3 models.");
        return;
      }
    }
    setAutoDiscoveryLoading(true);
    setError("");
    try {
      const detection = await runAutomaticDiscovery(datasetId, {
        score_method: autoDiscoveryScoreMethod,
        contamination_mode: autoDiscoveryContaminationMode,
        contamination: autoDiscoveryContamination,
        selected_model: autoDiscoveryScoreMethod === "best_score" ? autoDiscoverySelectedModel : null,
      });
      const records = await getAutomaticDiscoveryResult(datasetId, { page: 1, page_size: 50 });
      const defaultPlot = autoDiscoveryApproach === "univariate" ? "feature_vs_score" : "parallel_coordinates";
      const visualization = await getAutomaticDiscoveryVisualization(datasetId, autoDiscoveryApproach === "univariate" ? null : null, 1000, defaultPlot);
      setAutoDiscoveryDetection(detection);
      setAutoDiscoveryRecords(records);
      setAutoDiscoveryVisualization(visualization);
      setAutoDiscoveryColumn("");
      setAutoDiscoveryDetail(null);
      setAutoDiscoveryPage(1);
      setAutoDiscoveryAnomaliesOnly(false);
      setAutoDiscoverySearch("");
      setAutoDiscoveryPlotType(defaultPlot);
      setAutoDiscoverySelectedPoint(null);
      setAutoDiscoveryContribution(null);
      setAutoDiscoveryView("results");
      setTimeout(() => document.getElementById("automatic-results")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
    } catch (err) {
      setError(err?.message || "Automatic anomaly detection failed.");
    } finally {
      setAutoDiscoveryLoading(false);
    }
  }

  async function handleAutomaticDiscoveryColumn(columnName, page = 1, anomaliesOnly = false, search = autoDiscoverySearch) {
    if (!datasetId) return;
    setAutoDiscoveryLoading(true);
    setError("");
    try {
      const records = columnName
        ? await getAutomaticDiscoveryColumnResult(datasetId, columnName, { page, page_size: 50, anomalies_only: anomaliesOnly, search })
        : await getAutomaticDiscoveryResult(datasetId, { page, page_size: 50, anomalies_only: anomaliesOnly, search });
      const visualization = await getAutomaticDiscoveryVisualization(datasetId, columnName || null, 1000, autoDiscoveryPlotType);
      setAutoDiscoveryColumn(columnName || "");
      setAutoDiscoveryRecords(records);
      setAutoDiscoveryVisualization(visualization);
      setAutoDiscoveryDetail(null);
      setAutoDiscoveryPage(page);
      setAutoDiscoveryAnomaliesOnly(anomaliesOnly);
      setAutoDiscoverySelectedPoint(null);
      setAutoDiscoveryContribution(null);
      if (columnName) {
        setTimeout(() => document.getElementById("automatic-records")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
      }
    } catch (err) {
      setError(err?.message || "Unable to load column-specific results.");
    } finally {
      setAutoDiscoveryLoading(false);
    }
  }

  async function handleAutomaticDiscoverySearch(search) {
    setAutoDiscoverySearch(search);
    if (!datasetId) return;
    const page = 1;
    setAutoDiscoveryLoading(true);
    setError("");
    try {
      const records = autoDiscoveryApproach === "univariate" && autoDiscoveryColumn
        ? await getAutomaticDiscoveryColumnResult(datasetId, autoDiscoveryColumn, { page, page_size: 50, anomalies_only: autoDiscoveryAnomaliesOnly, search })
        : await getAutomaticDiscoveryResult(datasetId, { page, page_size: 50, anomalies_only: autoDiscoveryAnomaliesOnly, search });
      setAutoDiscoveryRecords(records);
      setAutoDiscoveryPage(1);
      setAutoDiscoveryDetail(null);
    } catch (err) {
      setError(err?.message || "Unable to search detection records.");
    } finally {
      setAutoDiscoveryLoading(false);
    }
  }

  async function handleAutomaticDiscoveryPage(page, anomaliesOnly = autoDiscoveryAnomaliesOnly) {
    if (!datasetId) return;
    setAutoDiscoveryLoading(true);
    setError("");
    try {
      const records = autoDiscoveryApproach === "univariate" && autoDiscoveryColumn
        ? await getAutomaticDiscoveryColumnResult(datasetId, autoDiscoveryColumn, { page, page_size: 50, anomalies_only: anomaliesOnly, search: autoDiscoverySearch })
        : await getAutomaticDiscoveryResult(datasetId, { page, page_size: 50, anomalies_only: anomaliesOnly, search: autoDiscoverySearch });
      setAutoDiscoveryRecords(records);
      setAutoDiscoveryPage(page);
      setAutoDiscoveryAnomaliesOnly(anomaliesOnly);
    } catch (err) {
      setError(err?.message || "Unable to load the requested records page.");
    } finally {
      setAutoDiscoveryLoading(false);
    }
  }

  async function handleAutomaticDiscoveryRecord(recordNumber, scroll = true) {
    if (!datasetId) return;
    setAutoDiscoveryLoading(true);
    setError("");
    try {
      const detail = await getAutomaticDiscoveryAnomalyDetail(datasetId, recordNumber, autoDiscoveryApproach === "univariate" ? autoDiscoveryColumn : null);
      setAutoDiscoveryDetail(detail);
      setAutoDiscoverySelectedPoint(Number(recordNumber));
      if (scroll) {
        setTimeout(() => document.getElementById(autoDiscoveryApproach === "univariate" && autoDiscoveryColumn ? "automatic-visualization" : "automatic-detail")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
      }
    } catch (err) {
      setError(err?.message || "Unable to load record details.");
    } finally {
      setAutoDiscoveryLoading(false);
    }
  }

  async function handleAutomaticDiscoveryVisualization(plotType, point = null) {
    if (!datasetId) return;
    setAutoDiscoveryPlotType(plotType);
    try {
      const visualization = await getAutomaticDiscoveryVisualization(
        datasetId,
        autoDiscoveryApproach === "univariate" ? (autoDiscoveryColumn || null) : null,
        1000,
        plotType
      );
      setAutoDiscoveryVisualization(visualization);
      if (point != null) {
        setAutoDiscoverySelectedPoint(Number(point));
        await handleAutomaticDiscoveryRecord(Number(point), false);
      }
    } catch (err) {
      setError(err?.message || "Unable to load visualization.");
    }
  }

  async function handleAutomaticDiscoveryContribution() {
    if (!datasetId || !autoDiscoverySelectedPoint) {
      setError("Select an anomaly record before opening Feature Contribution.");
      return;
    }
    setAutoDiscoveryLoading(true);
    setError("");
    try {
      const result = await getAutomaticDiscoveryFeatureContribution(datasetId, autoDiscoverySelectedPoint, 3);
      setAutoDiscoveryContribution(result);
      setTimeout(() => document.getElementById("automatic-contribution")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
    } catch (err) {
      setError(err?.message || "Unable to calculate feature contributions.");
    } finally {
      setAutoDiscoveryLoading(false);
    }
  }
  async function handleAutomaticDiscoveryReport() {
  if (!datasetId) {
    setError("No dataset is selected.");
    return;
  }

  setAutoDiscoveryLoading(true);
  setError("");

  try {
    await automaticDiscoveryApi.downloadReport(datasetId);
  } catch (err) {
    setError(
      err?.message ||
        "Unable to download the Machine Learning Benchmarking report."
    );
  } finally {
    setAutoDiscoveryLoading(false);
  }
}
  /* =========================================================
     STATISTICAL APPROACH
  ========================================================= */

  function openStatisticalApproach() {
    if (!datasetId || !preprocessResult || !analysis) {
      setError(
        "Complete Phase 3 preprocessing and statistical analysis before selecting a detection approach."
      );
      return;
    }

    setStatisticalApproach("statistical");
    setStatisticalResult(null);
    setStatisticalView("approach");
    // Move to the Statistical Phase 4 screen immediately.
    // The main content must stay synchronized with the sidebar.
    setActivePhase(4);
  }


  async function handleRunStatisticalBranch(method) {
    if (!datasetId || !preprocessResult) {
      setError(
        "Complete Phase 3 preprocessing before running statistical detection."
      );
      return;
    }

    if (
      method !== "univariate" &&
      method !== "multivariate"
    ) {
      setError("Invalid statistical detection method.");
      return;
    }

    setStatisticalLoading(true);
    setError("");

    try {
      const result =
        method === "univariate"
          ? await getUnivariateStatisticalDetection(
              datasetId
            )
          : await getMultivariateStatisticalDetection(
              datasetId
            );

      setStatisticalApproach(method);
      setStatisticalResult(result);
      setStatisticalView(method);
      // Move directly to the Statistical result screen after Continue.
      // Statistical results use the existing internal Phase 5 screen,
      // while the sidebar displays it as Phase 06.
      setActivePhase(5);
    } catch (err) {
      setError(
        err?.message ||
          `Unable to run ${method} statistical detection.`
      );
    } finally {
      setStatisticalLoading(false);
    }
  }

  /*
   * Phase 4 validation failure sends the user back to Phase 2.
   * The objective is intentionally preserved.
   */
  function returnToPhase2FromPhase4() {
    setActivePhase(2);

    setObjectiveValidation(null);
    setPhase4Complete(false);
    setRecommendations(null);
    setError("");
  }

/* =========================================================
   PHASE 5
   RECOMMEND MODELS
========================================================= */

  async function handleRecommendModels() {
    if (
      !datasetId ||
      !analysis ||
      !phase4Complete ||
      !objectiveValidation ||
      getMissingObjectiveColumns(
        objectiveValidation,
        selectedColumns
      ).length > 0
    ) {
      return;
    }

    setRecommendationLoading(true);
    setError("");

    try {
      /*
       * Confirm the semantic Phase 4 interpretation first.
       * The backend stores the interpreted objective for Phase 5.
       */
      await confirmPhase4Objective(
        datasetId
      );

      /*
       * Phase 5 receives the statistical evidence and the
       * semantic objective understanding returned by Phase 4.
       */
      const result =
        await recommendModels(
          datasetId,
          {
            statistical_profile:
              analysis,

            interpretation:
              objectiveValidation,

            column_profiles:
              summary?.column_details ||
              {},

            top_n: 3,
          }
        );

      setRecommendations(result);
      setActivePhase(5);

    } catch (err) {
      setError(
        err?.message ||
          "Unable to generate model recommendations."
      );
    } finally {
      setRecommendationLoading(false);
    }
  }

/* =========================================================
   NAVIGATION
========================================================= */

  function navigate(phase) {
    if (!summary) {
      return;
    }

    if (autoDiscoveryView) {
      if (phase === 1) { setActivePhase(1); resetAutomaticDiscovery(); return; }
      if (phase === 2) { setActivePhase(2); resetAutomaticDiscovery(); return; }
      if (phase === 3) { setActivePhase(3); resetAutomaticDiscovery(); return; }
      if (phase === 4) { setActivePhase(4); return; }
      return;
    }

    if (phase === 1) {
      setActivePhase(1);
      return;
    }

    if (phase === 2) {
      setActivePhase(2);
      return;
    }

    if (
      phase === 3 &&
      confirmed
    ) {
      setStatisticalView("");
      setStatisticalApproach("");
      setStatisticalResult(null);
      openPhase3();
      return;
    }

    /* =======================================================
       STATISTICAL BRANCH NAVIGATION
    ======================================================= */

    const statisticalBranch =
      statisticalApproach === "statistical" ||
      statisticalApproach === "univariate" ||
      statisticalApproach === "multivariate";

    if (
      statisticalBranch &&
      phase === 4 &&
      analysis
    ) {
      setStatisticalApproach("statistical");
      setStatisticalResult(null);
      setStatisticalView("approach");
      setActivePhase(4);
      return;
    }

    if (
      statisticalBranch &&
      phase === 5 &&
      (statisticalView === "univariate" ||
        statisticalView === "multivariate")
    ) {
      // Keep the existing statistical result screen exactly as it is.
      // The sidebar item is labelled 06, but internally this screen
      // continues to use activePhase 5.
      setActivePhase(5);
      return;
    }

    /* =======================================================
       EXISTING ML BRANCH NAVIGATION
    ======================================================= */

    if (
      statisticalApproach !== "statistical" &&
      statisticalApproach !== "univariate" &&
      statisticalApproach !== "multivariate" &&
      phase === 4 &&
      analysis
    ) {
      enterPhase4();
      return;
    }

    if (
      phase === 5 &&
      phase4Complete &&
      recommendations
    ) {
      setActivePhase(5);
      return;
    }

    if (
      phase === 6 &&
      recommendations
    ) {
      setActivePhase(6);
    }
  }


/* =========================================================
   RENDER
========================================================= */

  return (
    <div className="app-shell">

      <Sidebar
        activePhase={activePhase}
        summary={summary}
        confirmed={confirmed}
        analysis={analysis}
        phase4Complete={
          phase4Complete
        }
        recommendations={
          recommendations
        }
        statisticalApproach={
          statisticalApproach
        }
        statisticalView={
          statisticalView
        }
        statisticalResult={
          statisticalResult
        }
        autoDiscoveryView={autoDiscoveryView}
        onNavigate={navigate}
      />


      <div className="app-content">

        <header className="top-header">

          <div>
            <p className="eyebrow">
              INTELLIGENT ANOMALY INSIGHTS
            </p>

            <h1>
              Smart Anomaly Detection Framework
            </h1>

            <p className="subtitle">
              Analyze, preprocess and configure
              anomaly detection before model
              recommendation.
            </p>
          </div>

          {file && (
            <div className="header-file">
              <span>Dataset</span>
              <strong>
                {file.name}
              </strong>
            </div>
          )}

        </header>


        <main className="main-content">

          {/* ==================================================
              UPLOAD
          ================================================== */}

          <UploadPanel
            onFileSelected={
              handleFileSelected
            }
            onPostgresTableSelected={
              handlePostgresTableSelected
            }
            disabled={loading}
            currentFile={file}
          />


          {/* ==================================================
              LOADING
          ================================================== */}

          {loading && (
            <StatusCard
              text="Processing dataset"
              detail="The backend is profiling the uploaded dataset. Please wait..."
            />
          )}


          {/* ==================================================
              ERROR
          ================================================== */}

          {error && (
            <div className="error-card">

              <div>
                <strong>
                  Unable to complete the request
                </strong>

                <p>
                  {error}
                </p>
              </div>

              <button
                type="button"
                className="text-button"
                onClick={() =>
                  setError("")
                }
              >
                Dismiss
              </button>

            </div>
          )}


          {/* ==================================================
              PHASE 1
          ================================================== */}

          {summary &&
            !loading &&
            activePhase === 1 && (
              <Phase1
                summary={summary}
                onNext={() =>
                  setActivePhase(2)
                }
              />
            )}


          {/* ==================================================
              PHASE 2
          ================================================== */}

          {summary &&
            activePhase === 2 && (
              <Phase2
                summary={summary}
                selectedColumns={
                  selectedColumns
                }
                selectedDetail={
                  selectedDetail
                }
                infoColumn={
                  infoColumn
                }
                onToggle={
                  toggleColumn
                }
                onInfo={
                  chooseColumn
                }
                onCloseInfo={
                  closeColumnInfo
                }
                onConfirm={
                  handleConfirmSelection
                }
                confirming={
                  phase3Loading
                }
              />
            )}


          {/* ==================================================
              PHASE 3
          ================================================== */}

          {summary &&
            activePhase === 3 &&
            !statisticalView && (
              <Phase3
                summary={summary}
                selectedColumns={
                  selectedColumns
                }
                inspectionData={
                  inspectionData
                }
                preprocessResult={
                  preprocessResult
                }
                preview={preview}
                previewPage={
                  previewPage
                }
                phase3Loading={
                  phase3Loading
                }
                analysis={
                  analysis
                }
                analysisLoading={
                  analysisLoading
                }
                openSections={
                  openSections
                }
                onInspect={
                  inspect
                }
                onPreprocess={
                  handlePreprocess
                }
                onEditColumns={() =>
                  setActivePhase(2)
                }
                onPage={
                  changePreviewPage
                }
                onDownloadProcessedDataset={
                  handleDownloadProcessedDataset
                }
                onRunAnalysis={
                  handleRunAnalysis
                }
                onToggleAnalysis={(
                  key
                ) =>
                  setOpenSections(
                    (current) => ({
                      ...current,
                      [key]:
                        !current[key],
                    })
                  )
                }
                onContinueToPhase4={
                  enterPhase4
                }
                onProceedStatistical={
                  openStatisticalApproach
                }
                onProceedAutomaticDiscovery={
                  openAutomaticDiscovery
                }
              />
            )}


          {summary && autoDiscoveryView && (
            <AutomaticDiscoveryPanel
              datasetId={datasetId}
              view={autoDiscoveryView}
              approach={autoDiscoveryApproach}
              benchmark={autoDiscoveryBenchmark}
              recommendations={autoDiscoveryRecommendations}
              scoreMethod={autoDiscoveryScoreMethod}
              selectedModel={autoDiscoverySelectedModel}
              contaminationMode={autoDiscoveryContaminationMode}
              contamination={autoDiscoveryContamination}
              detection={autoDiscoveryDetection}
              records={autoDiscoveryRecords}
              column={autoDiscoveryColumn}
              detail={autoDiscoveryDetail}
              visualization={autoDiscoveryVisualization}
              loading={autoDiscoveryLoading}
              error={error}
              page={autoDiscoveryPage}
              anomaliesOnly={autoDiscoveryAnomaliesOnly}
              search={autoDiscoverySearch}
              plotType={autoDiscoveryPlotType}
              selectedPoint={autoDiscoverySelectedPoint}
              contribution={autoDiscoveryContribution}
              onChooseApproach={handleChooseAutomaticDiscoveryApproach}
              onContinue={handleAutomaticDiscoveryBenchmark}
              onScoreMethod={handleAutomaticDiscoveryScoreMethod}
              onSelectModel={setAutoDiscoverySelectedModel}
              onContaminationMode={setAutoDiscoveryContaminationMode}
              onContamination={setAutoDiscoveryContamination}
              onRun={handleRunAutomaticDiscovery}
              onOpenColumn={handleAutomaticDiscoveryColumn}
              onPage={handleAutomaticDiscoveryPage}
              onOpenRecord={handleAutomaticDiscoveryRecord}
              onSearch={handleAutomaticDiscoverySearch}
              onPlotType={handleAutomaticDiscoveryVisualization}
              onFeatureContribution={handleAutomaticDiscoveryContribution}
              onDownloadReport={handleAutomaticDiscoveryReport}
              onBack={() => {
                if (autoDiscoveryView === "results") {
                  setAutoDiscoveryView("recommendations");
                  setAutoDiscoveryDetection(null);
                  setAutoDiscoveryRecords(null);
                  setAutoDiscoveryDetail(null);
                  return;
                }
                resetAutomaticDiscovery();
                enterPhase4();
              }}
              onBackToSetup={() => setAutoDiscoveryView("setup")}
            />
          )}


          {/* ==================================================
              STATISTICAL APPROACH
          ================================================== */}

          {summary &&
            !autoDiscoveryView &&
            activePhase === 4 &&
            statisticalView === "approach" && (
              <StatisticalApproach
                datasetId={datasetId}
                onSelectApproach={(approach) => {
                  if (approach === "univariate") {
                    handleRunStatisticalBranch("univariate");
                    return;
                  }

                  if (approach === "multivariate") {
                    handleRunStatisticalBranch("multivariate");
                  }
                }}
                onBack={() => {
                  setStatisticalView("");
                  setStatisticalApproach("");
                }}
              />
            )}


          {/* ==================================================
              UNIVARIATE STATISTICAL ANALYSIS
          ================================================== */}

          {summary &&
            activePhase === 5 &&
            statisticalView === "univariate" && (
              <UnivariateAnalysis
                datasetId={datasetId}
                result={statisticalResult}
                loading={statisticalLoading}
                error={error}
                onBack={() => {
                  setStatisticalView("approach");
                  setStatisticalResult(null);
                  setStatisticalApproach("statistical");
                }}
              />
            )}


          {/* ==================================================
              MULTIVARIATE STATISTICAL ANALYSIS
          ================================================== */}

          {summary &&
            activePhase === 5 &&
            statisticalView === "multivariate" && (
              <MultivariateAnalysis
                datasetId={datasetId}
                result={statisticalResult}
                loading={statisticalLoading}
                error={error}
                onBack={() => {
                  setStatisticalView("approach");
                  setStatisticalResult(null);
                  setStatisticalApproach("statistical");
                }}
              />
            )}


          {/* ==================================================
              PHASE 4
          ================================================== */}

          {summary &&
            !autoDiscoveryView &&
            activePhase === 4 &&
            statisticalApproach !== "statistical" &&
            statisticalApproach !== "univariate" &&
            statisticalApproach !== "multivariate" && (
              <Phase4
                detectionObjective={
                  detectionObjective
                }
                objectiveValidation={
                  objectiveValidation
                }
                objectiveLoading={
                  objectiveLoading
                }
                phase4Complete={
                  phase4Complete
                }
                recommendationLoading={
                  recommendationLoading
                }
                selectedColumns={
                  selectedColumns
                }
                onReturnToPhase2={
                  returnToPhase2FromPhase4
                }
                onObjectiveChange={(
                  value
                ) => {
                  setDetectionObjective(
                    value
                  );

                  setObjectiveValidation(
                    null
                  );

                  setPhase4Complete(
                    false
                  );

                  setRecommendations(
                    null
                  );
                }}
                onValidateObjective={
                  handleValidateObjective
                }
                onRecommendModels={
                  handleRecommendModels
                }
              />
            )}


          {/* ==================================================
              PHASE 5
          ================================================== */}

          {summary &&
            !autoDiscoveryView &&
            activePhase === 5 &&
            statisticalApproach !== "statistical" &&
            statisticalApproach !== "univariate" &&
            statisticalApproach !== "multivariate" && (
              <Phase5
                recommendations={
                  recommendations
                }
                recommendationLoading={
                  recommendationLoading
                }
                anomalyType={
                  anomalyType
                }
                detectionScope={
                  detectionScope
                }
                temporalBehavior={
                  temporalBehavior
                }
                detectionObjective={
                  detectionObjective
                }
                selectedColumns={
                  selectedColumns
                }
                onContinueToPhase6={() =>
                  setActivePhase(6)
                }
              />
            )}


          {/* ==================================================
              PHASE 6
          ================================================== */}
          
          {summary &&
            !autoDiscoveryView &&
            activePhase === 6 && (
              <Phase6
                datasetId={
                  datasetId
                }
                selectedColumns={
                  selectedColumns
                }
                recommendations={
                  recommendations
                }
                objectiveValidation={
                  objectiveValidation
                }
                summary={
                  summary
                }
              />
            )}

        </main>
      </div>


      {/* ======================================================
          CONFIRMATION MODAL
      ====================================================== */}

      {confirmationOpen && (
        <ConfirmationModal
          count={
            selectedColumns.length
          }
          onProceed={
            proceedToPreprocessing
          }
          onEdit={
            editSelection
          }
        />
      )}


      {/* ======================================================
          INSPECTION MODAL
      ====================================================== */}

      {inspection && (
        <InspectionModal
          payload={inspection}
          data={
            inspectionData?.focused ||
            []
          }
          loading={
            inspectionLoading
          }
          onClose={() =>
            setInspection(null)
          }
        />
      )}

    </div>
  );
}


/* =========================================================
   UPLOAD PANEL
========================================================= */

function UploadPanel({
  onFileSelected,
  onPostgresTableSelected,
  disabled,
  currentFile,
}) {
  const [inputKey, setInputKey] = useState(0);
  const [sourceMode, setSourceMode] = useState("file");
  const [tables, setTables] = useState([]);
  const [schema, setSchema] = useState("");
  const [selectedTable, setSelectedTable] = useState("");
  const [tablesLoading, setTablesLoading] = useState(false);
  const [tablesError, setTablesError] = useState("");
  const [tableRefresh, setTableRefresh] = useState(0);

  useEffect(() => {
    if (sourceMode !== "postgres") {
      return undefined;
    }

    let active = true;
    setTablesLoading(true);
    setTablesError("");

    getPostgresTables()
      .then((result) => {
        if (!active) return;

        const availableTables = Array.isArray(result?.tables)
          ? result.tables
          : [];

        setTables(availableTables);
        setSchema(result?.schema || "");
        setSelectedTable((current) =>
          current && availableTables.includes(current)
            ? current
            : (availableTables[0] || "")
        );

        if (availableTables.length === 0) {
          setTablesError(
            "No tables were found in the configured PostgreSQL schema."
          );
        }
      })
      .catch((err) => {
        if (!active) return;
        setTables([]);
        setSelectedTable("");
        setTablesError(
          err?.message ||
            "Unable to retrieve PostgreSQL tables. Check that the backend is running and the database is reachable."
        );
      })
      .finally(() => {
        if (active) setTablesLoading(false);
      });

    return () => {
      active = false;
    };
  }, [sourceMode, tableRefresh]);

  function handleChange(event) {
    const nextFile = event.target.files?.[0];
    if (!nextFile) return;

    onFileSelected(nextFile);
    setInputKey((current) => current + 1);
  }

  function handleLoadTable() {
    if (!selectedTable || disabled) return;

    if (selectedTable === "sales_records_2m") {
      const confirmed = window.confirm(
        "This table contains approximately 2 million records and may consume substantial memory and processing time. Do you want to continue loading it?"
      );
      if (!confirmed) return;
    }

    onPostgresTableSelected(selectedTable);
  }

  return (
    <section className="upload-panel source-panel">
      <div className="source-panel-heading">
        <div className="upload-copy">
          <div className="upload-icon" aria-hidden="true">
            {sourceMode === "file" ? "↑" : "▤"}
          </div>
          <div>
            <p className="eyebrow">PHASE 01 · DATASET INPUT</p>
            <h2>Choose your data source</h2>
            <p>
              Upload a local dataset or connect to a table in the configured PostgreSQL database.
              Both sources enter the same ANOMXENSE workflow.
            </p>
          </div>
        </div>
      </div>

      <div className="source-tabs" role="tablist" aria-label="Dataset source">
        <button
          type="button"
          role="tab"
          aria-selected={sourceMode === "file"}
          className={`source-tab${sourceMode === "file" ? " active" : ""}`}
          onClick={() => setSourceMode("file")}
          disabled={disabled}
        >
          <span className="source-tab-icon" aria-hidden="true">↑</span>
          <span>
            <strong>Upload a file</strong>
            <small>CSV, TSV, JSON or Excel</small>
          </span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={sourceMode === "postgres"}
          className={`source-tab${sourceMode === "postgres" ? " active" : ""}`}
          onClick={() => setSourceMode("postgres")}
          disabled={disabled}
        >
          <span className="source-tab-icon" aria-hidden="true">▤</span>
          <span>
            <strong>PostgreSQL</strong>
            <small>Browse database tables</small>
          </span>
        </button>
      </div>

      {sourceMode === "file" ? (
        <div className="source-content file-source-content" role="tabpanel">
          <div className="source-content-copy">
            <strong>Select a dataset from your computer</strong>
            <span>Your existing file-upload workflow is unchanged.</span>
          </div>
          <label className={`upload-control${disabled ? " disabled" : ""}`}>
            <input
              key={inputKey}
              type="file"
              accept=".csv,.tsv,.json,.xlsx,.xls"
              disabled={disabled}
              onChange={handleChange}
            />
            <span className="upload-button">
              {disabled ? "Processing..." : "Choose Dataset"}
            </span>
          </label>
        </div>
      ) : (
        <div className="source-content postgres-source-content" role="tabpanel">
          <div className="postgres-source-intro">
            <span className="postgres-status-dot" aria-hidden="true" />
            <div>
              <strong>Connected database source</strong>
              <p>
                Choose an available table. ANOMXENSE reads it through the backend; database credentials are never shown here.
              </p>
            </div>
          </div>

          {schema && (
            <div className="postgres-schema-line">
              <span>Schema</span>
              <strong>{schema}</strong>
              <span className="postgres-table-count">
                {tables.length} {tables.length === 1 ? "table" : "tables"} available
              </span>
            </div>
          )}

          {tablesLoading ? (
            <div className="postgres-inline-status" role="status">
              <span className="postgres-spinner" aria-hidden="true" />
              Fetching tables from PostgreSQL...
            </div>
          ) : tablesError ? (
            <div className="postgres-error" role="alert">
              <p>{tablesError}</p>
              <button
                type="button"
                className="postgres-retry-button"
                onClick={() => setTableRefresh((current) => current + 1)}
                disabled={disabled}
              >
                Retry connection
              </button>
            </div>
          ) : (
            <>
              <div className="postgres-select-row">
                <label htmlFor="postgres-table-select">Database table</label>
                <select
                  id="postgres-table-select"
                  value={selectedTable}
                  onChange={(event) => setSelectedTable(event.target.value)}
                  disabled={disabled || tables.length === 0}
                >
                  {tables.length === 0 ? (
                    <option value="">No tables available</option>
                  ) : (
                    tables.map((tableName) => (
                      <option key={tableName} value={tableName}>
                        {tableName}
                      </option>
                    ))
                  )}
                </select>
              </div>

              {selectedTable === "sales_records_2m" && (
                <div className="postgres-large-table-warning" role="note">
                  <strong>Large table warning</strong>
                  <span>
                    This table contains approximately 2 million records. Loading it may require significant memory and time.
                  </span>
                </div>
              )}

              <div className="postgres-actions">
                <button
                  type="button"
                  className="postgres-retry-button"
                  onClick={() => setTableRefresh((current) => current + 1)}
                  disabled={disabled || tablesLoading}
                >
                  Refresh tables
                </button>
                <button
                  type="button"
                  className="postgres-load-button"
                  onClick={handleLoadTable}
                  disabled={disabled || !selectedTable || tablesLoading}
                >
                  {disabled ? "Loading dataset..." : "Load selected table"}
                  <span aria-hidden="true">→</span>
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {currentFile && (
        <div className="upload-selected-file">
          <div>
            <span>Selected dataset</span>
            <strong>{currentFile.name}</strong>
          </div>
          <span className="ready-badge">Ready</span>
        </div>
      )}
    </section>
  );
}

/* =========================================================
   AUTOMATIC ANOMALY DISCOVERY UI
   Isolated from the objective-based Phase 4–6 screens.
========================================================= */
function AutomaticDiscoveryPanel({
  datasetId, view, approach, benchmark, recommendations, scoreMethod, selectedModel,
  contaminationMode, contamination, detection, records, column, detail,
  visualization, loading, error, page, anomaliesOnly, search, plotType,
  selectedPoint, contribution, onChooseApproach, onContinue, onScoreMethod,
  onSelectModel, onContaminationMode, onContamination, onRun, onOpenColumn,
  onPage,
onOpenRecord,
onSearch,
onPlotType,
onFeatureContribution,
onDownloadReport,
onBack,
onBackToSetup,
}) {
  const card = { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: 18, marginBottom: 16, boxShadow: "0 2px 10px rgba(15,23,42,.04)" };
  const button = { border: "1px solid #cbd5e1", borderRadius: 9, padding: "9px 13px", background: "#fff", cursor: "pointer", fontWeight: 600 };
  const primary = { ...button, background: "#172554", color: "#fff", borderColor: "#172554" };
  const disabled = { opacity: .5, cursor: "not-allowed" };
  const summary = detection?.summary || records?.summary || {};
  const recommendationList = Array.isArray(recommendations?.recommendations) ? recommendations.recommendations : [];
  const recordPage = records?.records_page || records?.records || {};
  const rows = Array.isArray(recordPage?.records) ? recordPage.records : [];
  const totalPages = Math.max(1, Number(recordPage?.total_pages || 1));
  const points = Array.isArray(visualization?.points) ? visualization.points : [];
  const fmt = (value) => {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "number" && Number.isFinite(value)) return value.toLocaleString(undefined, { maximumFractionDigits: 5 });
    return String(value);
  };
  const pct = (value) => `${Number(value || 0).toFixed(2)}%`;
  const stat = (label, value) => (
    <div key={label} style={{ background: "#f8fafc", borderRadius: 10, padding: 12, minWidth: 150 }}>
      <div style={{ color: "#64748b", fontSize: 12 }}>{label}</div>
      <strong style={{ display: "block", marginTop: 4, overflowWrap: "anywhere" }}>{fmt(value)}</strong>
    </div>
  );

  const modelNames = Array.isArray(summary?.model_used)
    ? summary.model_used.join(", ")
    : summary?.model_used || summary?.selected_model || selectedModel || "—";

  const selectedRecord = selectedPoint ? points.find((point) => Number(point.record_number) === Number(selectedPoint)) : null;
  const [selectedContributionFeature, setSelectedContributionFeature] = useState(null);
  const maxScore = Math.max(1e-12, ...points.map((point) => Math.abs(Number(point.anomaly_score) || 0)));
  const minScore = points.length ? Math.min(...points.map((point) => Number(point.anomaly_score) || 0)) : 0;
  const maxScoreValue = points.length ? Math.max(...points.map((point) => Number(point.anomaly_score) || 0)) : 1;

  function renderScoreDistribution() {
    if (!points.length) return <div style={{ color: "#64748b", padding: 24 }}>No visualization points available.</div>;
    const width = 900;
    const height = 300;
    const pad = { left: 55, right: 25, top: 25, bottom: 45 };
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;
    const range = Math.max(1e-12, maxScoreValue - minScore);
    const threshold = Number(visualization?.threshold);
    const x = (i) => pad.left + (points.length <= 1 ? innerW / 2 : (i / (points.length - 1)) * innerW);
    const y = (value) => pad.top + innerH - ((Number(value) - minScore) / range) * innerH;
    return (
      <div style={{ overflowX: "auto" }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", minWidth: 720, height: 320 }} role="img" aria-label="Anomaly score distribution">
          <line x1={pad.left} y1={pad.top + innerH} x2={width - pad.right} y2={pad.top + innerH} stroke="#cbd5e1" />
          <line x1={pad.left} y1={pad.top} x2={pad.left} y2={pad.top + innerH} stroke="#cbd5e1" />
          {Number.isFinite(threshold) && <line x1={pad.left} y1={y(threshold)} x2={width - pad.right} y2={y(threshold)} stroke="#dc2626" strokeDasharray="6 5" />}
          {points.map((point, index) => {
            const px = x(index);
            const py = y(point.anomaly_score);
            const active = Number(point.record_number) === Number(selectedPoint);
            return (
              <circle key={point.record_number} cx={px} cy={py} r={active ? 6 : 3.5} fill={point.status === "Anomaly" ? "#dc2626" : "#2563eb"} stroke={active ? "#111827" : "#fff"} strokeWidth={active ? 2 : 1} style={{ cursor: "pointer" }} onClick={() => onPlotType(plotType, point.record_number)}>
                <title>{`Record ${point.record_number} · ${point.status} · score ${fmt(point.anomaly_score)}`}</title>
              </circle>
            );
          })}
          <text x={pad.left} y={height - 12} fontSize="12" fill="#64748b">Record order</text>
          <text x={10} y={pad.top + innerH / 2} fontSize="12" fill="#64748b" transform={`rotate(-90 10 ${pad.top + innerH / 2})`}>Anomaly score</text>
          {Number.isFinite(threshold) && <text x={width - 150} y={y(threshold) - 7} fontSize="12" fill="#b91c1c">Threshold {fmt(threshold)}</text>}
        </svg>
      </div>
    );
  }

  function renderFeatureVsScore() {
    if (!points.length) return <div style={{ color: "#64748b", padding: 24 }}>No visualization points available.</div>;
    const numeric = points.map((point) => Number(point.value)).every((value) => Number.isFinite(value));
    const width = 900;
    const height = 300;
    const pad = { left: 55, right: 25, top: 25, bottom: 45 };
    const values = numeric ? points.map((point) => Number(point.value)) : points.map((_, index) => index + 1);
    const minX = Math.min(...values);
    const maxX = Math.max(...values);
    const rangeX = Math.max(1e-12, maxX - minX);
    const rangeY = Math.max(1e-12, maxScoreValue - minScore);
    const px = (value) => pad.left + ((value - minX) / rangeX) * (width - pad.left - pad.right);
    const py = (value) => pad.top + (1 - ((value - minScore) / rangeY)) * (height - pad.top - pad.bottom);
    return (
      <div style={{ overflowX: "auto" }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", minWidth: 720, height: 320 }} role="img" aria-label="Feature value versus anomaly score">
          <line x1={pad.left} y1={height - pad.bottom} x2={width - pad.right} y2={height - pad.bottom} stroke="#cbd5e1" />
          <line x1={pad.left} y1={pad.top} x2={pad.left} y2={height - pad.bottom} stroke="#cbd5e1" />
          {Number.isFinite(Number(visualization?.threshold)) && <line x1={pad.left} y1={py(Number(visualization.threshold))} x2={width - pad.right} y2={py(Number(visualization.threshold))} stroke="#dc2626" strokeDasharray="6 5" />}
          {points.map((point, index) => {
            const cx = px(values[index]);
            const cy = py(Number(point.anomaly_score));
            const active = Number(point.record_number) === Number(selectedPoint);
            return (
              <circle key={point.record_number} cx={cx} cy={cy} r={active ? 7 : 4.5} fill={point.status === "Anomaly" ? "#dc2626" : "#2563eb"} stroke={active ? "#111827" : "#fff"} strokeWidth={active ? 2 : 1} style={{ cursor: "pointer" }} onClick={() => onPlotType(plotType, point.record_number)}>
                <title>{`Record ${point.record_number} · ${point.status} · value ${fmt(point.value)} · score ${fmt(point.anomaly_score)}`}</title>
              </circle>
            );
          })}
          <text x={pad.left} y={height - 12} fontSize="12" fill="#64748b">{column || "Feature value"}</text>
          <text x={10} y={height / 2} fontSize="12" fill="#64748b" transform={`rotate(-90 10 ${height / 2})`}>Anomaly score</text>
        </svg>
      </div>
    );
  }

  function renderParallelCoordinates() {
    const featureNames = Object.keys(points[0]?.values || {});
    if (!points.length || !featureNames.length) return <div style={{ color: "#64748b", padding: 24 }}>No multivariate visualization data available.</div>;
    const displayFeatures = featureNames.slice(0, 12);
    const width = Math.max(900, displayFeatures.length * 105);
    const height = 330;
    const top = 30;
    const bottom = 270;
    const x = (index) => 55 + (displayFeatures.length === 1 ? 0 : (index / (displayFeatures.length - 1)) * (width - 110));
    const ranges = Object.fromEntries(displayFeatures.map((name) => {
      const values = points.map((point) => Number(point.values?.[name])).filter(Number.isFinite);
      const min = values.length ? Math.min(...values) : 0;
      const max = values.length ? Math.max(...values) : 1;
      return [name, { min, max: Math.max(min + 1e-12, max) }];
    }));
    const y = (name, value) => {
      const range = ranges[name];
      const number = Number(value);
      if (!Number.isFinite(number)) return bottom;
      return bottom - ((number - range.min) / (range.max - range.min)) * (bottom - top);
    };
    return (
      <div style={{ overflowX: "auto" }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", minWidth: 760, height: 350 }} role="img" aria-label="Parallel coordinates visualization">
          {displayFeatures.map((name, featureIndex) => (
            <g key={name}>
              <line x1={x(featureIndex)} y1={top} x2={x(featureIndex)} y2={bottom} stroke="#cbd5e1" />
              <text x={x(featureIndex)} y={top - 8} textAnchor="middle" fontSize="11" fill="#334155">{name.length > 15 ? `${name.slice(0, 14)}…` : name}</text>
            </g>
          ))}
          {points.map((point) => {
            const active = Number(point.record_number) === Number(selectedPoint);
            const path = displayFeatures.map((name, index) => `${index === 0 ? "M" : "L"} ${x(index)} ${y(name, point.values?.[name])}`).join(" ");
            return <path key={point.record_number} d={path} fill="none" stroke={point.status === "Anomaly" ? "#dc2626" : "#94a3b8"} strokeWidth={active ? 3 : 1.2} opacity={active ? 1 : .38} style={{ cursor: "pointer" }} onClick={() => onPlotType(plotType, point.record_number)}><title>{`Record ${point.record_number} · ${point.status} · score ${fmt(point.anomaly_score)}`}</title></path>;
          })}
        </svg>
      </div>
    );
  }

  return (
    <section className="automatic-discovery-panel" style={{ padding: view === "setup" ? "20px 18px 28px" : "28px clamp(16px, 3vw, 36px)", maxWidth: view === "setup" ? 1120 : 1500, margin: "0 auto", color: "#17213f" }}>
      {view === "setup" ? (
        <div className="automatic-setup-shell" style={{ width: "min(1080px, 100%)", margin: "0 auto" }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 20,
            padding: "20px 22px",
            marginBottom: 14,
            background: "linear-gradient(135deg, #17255f 0%, #293b8f 58%, #4257ad 100%)",
            border: "1px solid rgba(41, 59, 143, 0.25)",
            borderRadius: 14,
            boxShadow: "0 12px 28px rgba(31, 47, 111, 0.18)"
          }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ color: "#d9a441", fontSize: 12, fontWeight: 800, letterSpacing: 1.1, textTransform: "uppercase", marginBottom: 4 }}>
                Automatic ML Approach
              </div>
              <h1 style={{ margin: 0, color: "#fff", fontSize: 27, lineHeight: 1.2, fontWeight: 800, letterSpacing: -0.3 }}>
                Benchmarking Approach
              </h1>
              <p style={{ margin: "7px 0 0", color: "rgba(255,255,255,.78)", fontSize: 15, lineHeight: 1.45 }}>
                Choose how the preprocessed dataset should be analyzed for machine-learning anomaly detection.
              </p>
            </div>
            <button
              type="button"
              onClick={onBack}
              disabled={loading}
              style={{
                flexShrink: 0,
                border: "1px solid rgba(255,255,255,.38)",
                background: "rgba(255,255,255,.09)",
                color: "#fff",
                borderRadius: 8,
                padding: "9px 15px",
                fontSize: 14,
                fontWeight: 750,
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? .55 : 1
              }}
            >
              ← Back
            </button>
          </div>

          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 15,
            padding: "11px 15px",
            marginBottom: 16,
            background: "#fff",
            border: "1px solid #d9e0f0",
            borderRadius: 10,
            boxShadow: "0 4px 14px rgba(32,48,110,.05)"
          }}>
            <span style={{ color: "#66718c", fontSize: 13, fontWeight: 750, textTransform: "uppercase", letterSpacing: .7 }}>
              Current Dataset
            </span>
            <span style={{ maxWidth: "70%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", padding: "5px 10px", borderRadius: 7, background: "#eef1ff", color: "#293b8f", fontSize: 14, fontWeight: 800 }}>
              {datasetId || "—"}
            </span>
          </div>

          <div style={{
            padding: 19,
            background: "#fff",
            border: "1px solid #d9e0f0",
            borderRadius: 14,
            boxShadow: "0 7px 22px rgba(27,43,94,.07)"
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 14 }}>
              <div>
                <h2 style={{ margin: 0, color: "#18265f", fontSize: 20, fontWeight: 800 }}>
                  Select Analysis Method
                </h2>
                <p style={{ margin: "4px 0 0", color: "#66718c", fontSize: 14, lineHeight: 1.4 }}>
                  Select one approach to continue with automatic anomaly detection.
                </p>
              </div>
              <span style={{ flexShrink: 0, padding: "6px 10px", border: "1px solid #d9e0f0", borderRadius: 999, background: "#f7f8fd", color: "#66718c", fontSize: 12, fontWeight: 750 }}>
                Select one
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 14 }}>
              {[
                ["univariate", "Univariate", "Analyze each selected numerical column independently to identify individual feature outliers.", "U"],
                ["multivariate", "Multivariate", "Analyze the combined behavior of selected features using their multivariate relationships.", "M"],
              ].map(([key, title, description, icon]) => {
                const selected = approach === key;
                return (
                  <button
                    key={key}
                    type="button"
                    disabled={loading}
                    onClick={() => onChooseApproach(key)}
                    style={{
                      position: "relative",
                      display: "grid",
                      gridTemplateColumns: "46px minmax(0, 1fr) 22px",
                      alignItems: "center",
                      gap: 14,
                      width: "100%",
                      minHeight: 142,
                      padding: 17,
                      textAlign: "left",
                      background: selected ? "linear-gradient(135deg,#f7f8ff 0%,#eef1ff 100%)" : "#fff",
                      border: `1.5px solid ${selected ? "#293b8f" : "#d9e0f0"}`,
                      borderRadius: 12,
                      color: "#17213f",
                      cursor: loading ? "not-allowed" : "pointer",
                      opacity: loading ? .65 : 1,
                      boxShadow: selected ? "0 0 0 2px rgba(41,59,143,.12), 0 10px 24px rgba(41,59,143,.14)" : "none",
                      transition: "border-color .18s ease, box-shadow .18s ease, transform .18s ease, background .18s ease"
                    }}
                  >
                    <span style={{
                      display: "flex", alignItems: "center", justifyContent: "center",
                      width: 46, height: 46, borderRadius: 11,
                      background: selected ? "linear-gradient(135deg,#18265f,#293b8f)" : "linear-gradient(135deg,#293b8f,#4257ad)",
                      color: "#fff", fontSize: 19, fontWeight: 850,
                      boxShadow: "0 5px 12px rgba(41,59,143,.18)"
                    }}>
                      {icon}
                    </span>

                    <span style={{ minWidth: 0 }}>
                      <strong style={{ display: "block", margin: "0 0 5px", color: "#18265f", fontSize: 19, lineHeight: 1.2, fontWeight: 800 }}>
                        {title}
                      </strong>
                      <span style={{ display: "block", margin: "0 0 10px", color: "#66718c", fontSize: 13.5, lineHeight: 1.45 }}>
                        {description}
                      </span>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "5px 9px", border: "1px solid #dce2f1", borderRadius: 6, background: "#f7f8fd", color: "#66718c", fontSize: 11, fontWeight: 750, textTransform: "uppercase", letterSpacing: .45 }}>
                        Method <strong style={{ color: "#293b8f", fontSize: 12, fontWeight: 850, textTransform: "none", letterSpacing: 0 }}>Automatic ML</strong>
                      </span>
                    </span>

                    <span style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <span style={{
                        display: "block", width: 18, height: 18, border: `2px solid ${selected ? "#293b8f" : "#b7c0d6"}`, borderRadius: "50%",
                        background: selected ? "radial-gradient(circle,#293b8f 0 42%,#fff 45% 100%)" : "#fff",
                        boxShadow: selected ? "0 0 0 3px rgba(41,59,143,.10)" : "none"
                      }} />
                    </span>
                  </button>
                );
              })}
            </div>

            {error && (
              <div style={{ marginTop: 13, padding: "10px 13px", border: "1px solid #f1c4cd", borderLeft: "4px solid #c52b48", borderRadius: 8, background: "#fff3f5", color: "#a8223b", fontSize: 13, fontWeight: 650 }}>
                {error}
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 10, marginTop: 15 }}>
              <button
                type="button"
                disabled={loading || !approach}
                onClick={() => onContinue(approach)}
                style={{
                  minWidth: 125,
                  border: "1px solid #293b8f",
                  borderRadius: 8,
                  padding: "10px 18px",
                  background: loading || !approach ? "#c5cad8" : "linear-gradient(135deg,#293b8f,#4257ad)",
                  color: "#fff",
                  fontSize: 14,
                  fontWeight: 800,
                  cursor: loading || !approach ? "not-allowed" : "pointer",
                  boxShadow: loading || !approach ? "none" : "0 5px 13px rgba(41,59,143,.18)"
                }}
              >
                {loading ? "Benchmarking…" : "Continue →"}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="automatic-discovery-results-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap", marginBottom: 20 }}>
            <div>
              <div style={{ color: "#64748b", fontSize: 12, fontWeight: 700, letterSpacing: 1.2 }}>ANOMXENSE · AUTOMATIC DISCOVERY</div>
              <h1 style={{ margin: "8px 0", fontSize: 28 }}>Automatic Anomaly Discovery</h1>
              <p style={{ color: "#64748b", margin: 0, maxWidth: 820 }}>Benchmark the compatible PyOD models, choose the scoring mode, detect anomalies, and investigate the records without entering a detection objective.</p>
            </div>
            <button style={button} onClick={onBack}>← {view === "results" ? "Back to recommendations" : "Back"}</button>
          </div>

          {error && <div role="alert" style={{ ...card, color: "#991b1b", background: "#fef2f2", borderColor: "#fecaca" }}>{error}</div>}
          {loading && <div style={{ ...card, color: "#334155" }}>Working on your dataset… larger datasets may take longer.</div>}
        </>
      )}

      {view === "recommendations" && (
        <div className="automatic-recommendations-view">
          <div className="automatic-recommendation-card" style={card}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
              <div><h2 style={{ margin: 0 }}>Model Recommendation</h2><p style={{ color: "#64748b", margin: "7px 0 0" }}>Top 3 membership and order stay fixed. The dropdown only changes which benchmark score is displayed.</p></div>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600 }}>Score to display
                <select value={scoreMethod} onChange={(event) => onScoreMethod(event.target.value)} style={{ ...button, minWidth: 160 }}>
                  <option value="best_score">Best Score</option>
                  <option value="combined_score">Combined Score</option>
                </select>
              </label>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12, marginTop: 18 }}>
              {recommendationList.map((item, index) => {
                const displayScore = item?.display_score ?? item?.[scoreMethod];
                const selectedModels = String(selectedModel || "")
                  .split(",")
                  .map((model) => model.trim())
                  .filter(Boolean);
                const active = selectedModels.includes(item.model);
                const combinedLocked = scoreMethod === "combined_score";
                return (
                  <button key={item.model} type="button" onClick={() => {
                    if (combinedLocked) return;
                    onSelectModel(item.model);
                  }} disabled={combinedLocked} style={{ ...button, textAlign: "left", padding: 16, borderColor: active ? "#2563eb" : "#e2e8f0", background: active ? "#eff6ff" : "#fff", cursor: combinedLocked ? "not-allowed" : "pointer", opacity: combinedLocked ? 1 : 1 }}>
                    <div style={{ color: "#64748b", fontSize: 12 }}>TOP {index + 1}</div>
                    <strong style={{ display: "block", fontSize: 19, margin: "7px 0" }}>{item.model}</strong>
                    <div style={{ fontSize: 13, color: "#475569" }}>
                      Benchmark Score: {fmt(item.combined_score ?? item.score ?? item.rank_score)}
                    </div>                  
                  </button>
                );
              })}
            </div>
          </div>

          <div className="automatic-settings-card" style={card}>
            <h2 style={{ marginTop: 0 }}>Detection Settings</h2>
            <div style={{ display: "flex", gap: 18, flexWrap: "wrap", marginBottom: 16 }}>
              <label style={{ display: "flex", gap: 8, alignItems: "center" }}><input type="radio" checked={contaminationMode === "default"} onChange={() => onContaminationMode("default")} />Default (0.10)</label>
              <label style={{ display: "flex", gap: 8, alignItems: "center" }}><input type="radio" checked={contaminationMode === "custom"} onChange={() => onContaminationMode("custom")} />Custom</label>
            </div>
            {contaminationMode === "custom" && <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
              <button style={button} onClick={() => onContamination(Math.max(0.01, Number((contamination - 0.01).toFixed(2))))}>−</button>
              <input type="number" min="0.01" max="0.50" step="0.01" value={contamination} onChange={(event) => onContamination(Number(event.target.value))} style={{ ...button, width: 110 }} />
              <button style={button} onClick={() => onContamination(Math.min(0.50, Number((contamination + 0.01).toFixed(2))))}>+</button>
              <span style={{ color: "#64748b" }}>{Number(contamination * 100).toFixed(0)}%</span>
            </div>}
            {scoreMethod === "best_score" && <p style={{ color: "#64748b", marginTop: 0 }}>Selected model: <strong>{selectedModel || "Choose one of the Top 3 above"}</strong></p>}
            <button disabled={loading || (scoreMethod === "best_score" && !selectedModel) || (contaminationMode === "custom" && (!Number.isFinite(Number(contamination)) || contamination < 0.01 || contamination > 0.50))} style={{ ...primary, ...((loading || (scoreMethod === "best_score" && !selectedModel)) ? disabled : {}) }} onClick={onRun}>Run Anomaly Detection →</button>
          </div>
        </div>
      )}

      {view === "results" && (
        <div id="automatic-results">
          <div style={card}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              
               <h2 style={{ margin: 0 }}>Detection Summary</h2>

<div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
  <button
    style={{
      ...button,
      background: "#172554",
      color: "#fff",
      borderColor: "#172554",
    }}
    onClick={onDownloadReport}
    disabled={loading}
  >
    {loading
      ? "Generating Report..."
      : "Download ML Benchmarking Report"}
  </button>

  <button
    style={button}
    onClick={onBackToSetup}
  >
    Change model or settings
  </button>
</div>

            </div>
            {approach === "multivariate" ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10, marginTop: 16 }}>
                {stat("Approach", "ML approach - Multivariate")}
                {stat("Detection mode", scoreMethod === "best_score" ? "Best Score" : "Ensemble")}
                {stat("Model used", modelNames)}
                {stat("Total no. of records", summary.total_records)}
                {stat("No. of normal records", summary.normal_records)}
                {stat("No. of anomalies", summary.anomaly_records)}
                {stat("% of anomalies", pct(summary.anomaly_rate_percent))}
                {stat("Contamination", Number(summary.contamination ?? contamination).toFixed(2))}
                {stat("Threshold", summary.threshold)}
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10, marginTop: 16 }}>
                {stat("Approach", "ML approach - Univariate")}
                {stat("Detection mode", scoreMethod === "best_score" ? "Best Score" : "Combined Score")}
                {scoreMethod === "best_score" && stat("Selected model", selectedModel)}
                {stat("Total no. of records", summary.total_records)}
                {stat("Contamination", Number(summary.contamination ?? contamination).toFixed(2))}
              </div>
            )}

            {approach === "univariate" && Array.isArray(detection?.column_summaries) && (
              <div style={{ marginTop: 22 }}>
                <h3>Column-level Results</h3>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 720 }}>
                    <thead><tr>{["Column Name", "Total Number of Records", "No. Normal", "No. Anomalies", "% Anomalies", "Action"].map((heading) => <th key={heading} style={{ textAlign: "left", padding: 11, borderBottom: "1px solid #e2e8f0", whiteSpace: "nowrap" }}>{heading}</th>)}</tr></thead>
                    <tbody>
                      {detection.column_summaries.map((item) => (
                        <tr key={item.column}>
                          <td style={{ padding: 11, borderBottom: "1px solid #f1f5f9", fontWeight: 600 }}>{item.column}</td>
                          <td style={{ padding: 11, borderBottom: "1px solid #f1f5f9" }}>{fmt(item.total_records)}</td>
                          <td style={{ padding: 11, borderBottom: "1px solid #f1f5f9" }}>{fmt(item.normal_records)}</td>
                          <td style={{ padding: 11, borderBottom: "1px solid #f1f5f9" }}>{fmt(item.anomaly_records)}</td>
                          <td style={{ padding: 11, borderBottom: "1px solid #f1f5f9" }}>{pct(item.anomaly_rate_percent)}</td>
                          <td style={{ padding: 11, borderBottom: "1px solid #f1f5f9" }}><button style={button} onClick={() => onOpenColumn(item.column, 1, false)}>View</button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {(approach === "multivariate" || column) && records && (
            <div id="automatic-records" style={card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <div><h2 style={{ margin: 0 }}>{column ? `Records · ${column}` : "Detection Records"}</h2><p style={{ margin: "5px 0 0", color: "#64748b" }}>{approach === "univariate" ? "Search by record number or column value." : "Search by record number, any feature name/value, or anomaly score."}</p></div>
                <label style={{ display: "flex", gap: 8, alignItems: "center" }}><input type="checkbox" checked={anomaliesOnly} onChange={(event) => onPage(1, event.target.checked)} />Anomalies only</label>
              </div>
              <div style={{ display: "flex", gap: 10, marginTop: 14, flexWrap: "wrap" }}>
                <input value={search} onChange={(event) => onSearch(event.target.value)} placeholder={approach === "univariate" ? "Search record number or column value" : "Search record number, feature, value or score"} style={{ flex: "1 1 320px", minWidth: 240, padding: "10px 12px", border: "1px solid #cbd5e1", borderRadius: 9 }} />
                {column && <button style={button} onClick={() => onOpenColumn("", 1, false)}>Back to all columns</button>}
              </div>
              <div style={{ overflowX: "auto", marginTop: 14 }}>
                <table style={{ width: "100%", borderCollapse: "collapse", minWidth: approach === "univariate" ? 760 : 850 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e2e8f0" }}>Record</th>
                      {approach === "univariate" ? <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e2e8f0" }}>Column Value</th> : Object.keys(rows[0]?.values || {}).map((name) => <th key={name} style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e2e8f0" }}>{name}</th>)}
                      <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e2e8f0" }}>Anomaly Score</th>
                      <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e2e8f0" }}>Threshold</th>
                      <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e2e8f0" }}>Status</th>
                      <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e2e8f0" }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.length === 0 ? <tr><td colSpan={approach === "univariate" ? 6 : Object.keys(rows[0]?.values || {}).length + 5} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>No records match the current search/filter.</td></tr> : rows.map((row) => {
                      const active = Number(selectedPoint) === Number(row.record_number);
                      return <tr key={row.record_number} style={{ background: active ? "#eff6ff" : "transparent" }}>
                        <td style={{ padding: 10, borderBottom: "1px solid #f1f5f9", fontWeight: 600 }}>{row.record_number}</td>
                        {approach === "univariate" ? <td style={{ padding: 10, borderBottom: "1px solid #f1f5f9" }}>{fmt(column ? row.values?.[column] : Object.values(row.values || {})[0])}</td> : Object.values(row.values || {}).map((value, index) => <td key={index} style={{ padding: 10, borderBottom: "1px solid #f1f5f9" }}>{fmt(value)}</td>)}
                        <td style={{ padding: 10 }}>{fmt(row.anomaly_score)}</td>
                        <td style={{ padding: 10 }}>{fmt(row.threshold)}</td>
                        <td style={{ padding: 10 }}><span style={{ color: row.status === "Anomaly" ? "#b91c1c" : "#166534", fontWeight: 700 }}>{row.status}</span></td>
                        <td style={{ padding: 10 }}><button style={button} onClick={() => onOpenRecord(row.record_number)}>{approach === "univariate" && column ? "Visualize" : "View"}</button></td>
                      </tr>;
                    })}
                  </tbody>
                </table>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 14, flexWrap: "wrap" }}>
                <span style={{ color: "#64748b", fontSize: 13 }}>Page {recordPage.page || page} of {totalPages} · {fmt(recordPage.total_matching_records ?? rows.length)} matching records</span>
                <div style={{ display: "flex", gap: 8 }}><button style={button} disabled={loading || page <= 1} onClick={() => onPage(page - 1)}>Previous</button><button style={button} disabled={loading || page >= totalPages} onClick={() => onPage(page + 1)}>Next</button></div>
              </div>
            </div>
          )}

          {detail && (
            <div id="automatic-detail" style={card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <h2 style={{ margin: 0 }}>Record {detail.record_number} Details</h2>
                {approach === "multivariate" && detail.status === "Anomaly" && <button style={primary} onClick={onFeatureContribution}>Feature Contribution</button>}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 10, marginTop: 15 }}>
                {stat("Status", detail.status)}{stat("Anomaly Score", detail.anomaly_score)}{stat("Threshold", detail.threshold)}
              </div>
              <h3>Feature Values</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 8 }}>
                {Object.entries(detail.values || {}).map(([key, value]) => <div key={key} style={{ background: "#f8fafc", padding: 10, borderRadius: 8 }}><div style={{ color: "#64748b", fontSize: 12 }}>{key}</div><strong style={{ overflowWrap: "anywhere" }}>{fmt(value)}</strong></div>)}
              </div>
            </div>
          )}

          {contribution && approach === "multivariate" && (
            <div id="automatic-contribution" className="automatic-contribution-card">
              <div className="automatic-contribution-header">
                <div>
                  <p className="automatic-contribution-eyebrow">LOCAL EXPLANATION</p>
                  <h2>Feature Contribution · Record {contribution.record_number}</h2>
                  <p className="automatic-contribution-description">Model-agnostic local feature ablation estimates how much each selected attribute changes the record's anomaly score.</p>
                </div>
                <div className="automatic-contribution-badge">Multivariate</div>
              </div>

              <div className="automatic-contribution-section-title">
                <div>
                  <span>TOP 3</span>
                  <h3>Contributing Attributes</h3>
                </div>
                <p>Highest-impact attributes for this record</p>
              </div>

              <div className="automatic-contribution-top-grid">
                {(contribution.top_contributing_attributes || []).map((item) => {
                  const selected = selectedContributionFeature?.feature === item.feature;
                  return (
                    <button
                      key={item.feature}
                      type="button"
                      className={`automatic-contribution-top-card${selected ? " is-selected" : ""}`}
                      onClick={() => setSelectedContributionFeature(item)}
                      aria-pressed={selected}
                    >
                      <span className="automatic-contribution-rank">#{item.rank}</span>
                      <span className="automatic-contribution-feature">{item.feature}</span>
                      <span className="automatic-contribution-value">{pct(item.contribution_percent)}</span>
                      <span className="automatic-contribution-bar"><span style={{ width: `${Math.min(100, Math.max(0, Number(item.contribution_percent) || 0))}%` }} /></span>
                      <span className="automatic-contribution-explain">Click to explain →</span>
                    </button>
                  );
                })}
              </div>

              {selectedContributionFeature && (() => {
                const feature = selectedContributionFeature.feature;
                const contributionPercent = Number(selectedContributionFeature.contribution_percent);
                const originalScore = [
                  selectedContributionFeature.original_score,
                  selectedContributionFeature.base_score,
                  selectedContributionFeature.anomaly_score,
                  detail?.anomaly_score,
                  selectedRecord?.anomaly_score,
                ].map(Number).find(Number.isFinite);
                const perturbedScore = [
                  selectedContributionFeature.perturbed_score,
                  selectedContributionFeature.ablated_score,
                  selectedContributionFeature.score_after_perturbation,
                  selectedContributionFeature.new_score,
                ].map(Number).find(Number.isFinite);
                const explicitChange = [
                  selectedContributionFeature.score_change,
                  selectedContributionFeature.anomaly_score_change,
                  selectedContributionFeature.absolute_score_change,
                  selectedContributionFeature.delta,
                ].map(Number).find(Number.isFinite);
                const scoreChange = Number.isFinite(explicitChange)
                  ? Math.abs(explicitChange)
                  : Number.isFinite(originalScore) && Number.isFinite(perturbedScore)
                    ? Math.abs(originalScore - perturbedScore)
                    : NaN;
                const explicitTotal = [
                  selectedContributionFeature.total_score_change,
                  selectedContributionFeature.total_absolute_score_change,
                  contribution.total_score_change,
                  contribution.total_absolute_score_change,
                ].map(Number).find(Number.isFinite);
                const totalScoreChange = Number.isFinite(explicitTotal)
                  ? Math.abs(explicitTotal)
                  : Number.isFinite(scoreChange) && Number.isFinite(contributionPercent) && contributionPercent > 0
                    ? scoreChange / (contributionPercent / 100)
                    : NaN;
                const valueOrDash = (value) => Number.isFinite(value) ? fmt(value) : "Not provided";
                return (
                  <div className="automatic-contribution-explanation">
                    <div className="automatic-contribution-explanation-header">
                      <div>
                        <span className="automatic-contribution-explanation-eyebrow">SELECTED ATTRIBUTE</span>
                        <h3>How is {feature} contributing to this anomaly?</h3>
                      </div>
                      <span className="automatic-contribution-explanation-result">{pct(contributionPercent)}</span>
                    </div>

                    <div className="automatic-contribution-method">
                      <span>APPROACH USED</span>
                      <strong>Local Feature Ablation</strong>
                      <p>The original record is scored using all selected features. Then only <strong>{feature}</strong> is temporarily perturbed while the other selected attributes remain unchanged. The model is scored again, and the change in anomaly score measures this feature's local influence.</p>
                    </div>

                    <div className="automatic-contribution-calculation">
                      <div className="automatic-contribution-calculation-title">STEP-BY-STEP CALCULATION</div>
                      <div className="automatic-contribution-step"><span>01</span><div><strong>Original anomaly score</strong><b>{valueOrDash(originalScore)}</b></div></div>
                      <div className="automatic-contribution-step"><span>02</span><div><strong>Perturb {feature}</strong><p>{feature} is temporarily changed/ablated. All other selected features remain unchanged.</p></div></div>
                      <div className="automatic-contribution-step"><span>03</span><div><strong>Recalculate anomaly score</strong><b>{valueOrDash(perturbedScore)}</b></div></div>
                      <div className="automatic-contribution-step"><span>04</span><div><strong>Score change</strong><b>{valueOrDash(scoreChange)}</b>{Number.isFinite(originalScore) && Number.isFinite(perturbedScore) && <p>|{fmt(originalScore)} − {fmt(perturbedScore)}| = {fmt(scoreChange)}</p>}</div></div>
                      <div className="automatic-contribution-step"><span>05</span><div><strong>Total score change across all features</strong><b>{valueOrDash(totalScoreChange)}</b></div></div>
                      <div className="automatic-contribution-step"><span>06</span><div><strong>Contribution %</strong><b>{pct(contributionPercent)}</b>{Number.isFinite(scoreChange) && Number.isFinite(totalScoreChange) && <p>({fmt(scoreChange)} ÷ {fmt(totalScoreChange)}) × 100 = {pct(contributionPercent)}</p>}</div></div>
                    </div>

                    <div className="automatic-contribution-formula">
                      <strong>FORMULA</strong>
                      <div>Contribution % = |Feature Score Change| ÷ Σ|Score Changes| × 100</div>
                    </div>

                    <div className="automatic-contribution-result-box">
                      <strong>RESULT</strong>
                      <p>{feature} contributed <b>{pct(contributionPercent)}</b> of the total local score change for Record {contribution.record_number}.</p>
                    </div>
                  </div>
                );
              })()}

              <div className="automatic-contribution-section-title automatic-contribution-all-title">
                <div>
                  <span>COMPLETE BREAKDOWN</span>
                  <h3>All Feature Contributions</h3>
                </div>
                <p>{(contribution.all_feature_contributions || []).length} selected attributes</p>
              </div>

              <div className="automatic-contribution-table-wrap">
                <table className="automatic-contribution-table">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Feature</th>
                      <th>Contribution %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(contribution.all_feature_contributions || []).map((item) => (
                      <tr key={item.feature}>
                        <td><span className="automatic-contribution-table-rank">{item.rank}</span></td>
                        <td><strong>{item.feature}</strong></td>
                        <td><span className="automatic-contribution-table-value">{pct(item.contribution_percent)}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {visualization && (
            <div id="automatic-visualization" style={card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <div><h2 style={{ margin: 0 }}>Visualization</h2><p style={{ margin: "5px 0 0", color: "#64748b", fontSize: 13 }}>Click any point or line to open the matching record and keep the table selection synchronized.</p></div>
                <select value={plotType} onChange={(event) => onPlotType(event.target.value)} style={{ ...button, minWidth: 230 }}>
                  {approach === "univariate" ? <><option value="feature_vs_score">Feature Value vs Anomaly Score</option><option value="score_distribution">Anomaly Score Distribution</option></> : <><option value="parallel_coordinates">Parallel Coordinates</option><option value="score_distribution">Anomaly Score Distribution</option></>}
                </select>
              </div>
              <div style={{ marginTop: 12 }}>
                {plotType === "feature_vs_score" ? renderFeatureVsScore() : plotType === "parallel_coordinates" ? renderParallelCoordinates() : renderScoreDistribution()}
              </div>
              {selectedRecord && <div style={{ marginTop: 10, background: "#f8fafc", borderRadius: 10, padding: 12 }}><strong>Selected record {selectedRecord.record_number}</strong> · {selectedRecord.status} · score {fmt(selectedRecord.anomaly_score)} · threshold {fmt(selectedRecord.threshold)}{column ? ` · ${column}: ${fmt(selectedRecord.value)}` : ""}</div>}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

/* =========================================================
   SIDEBAR
========================================================= */

function Sidebar({
  activePhase,
  summary,
  confirmed,
  analysis,
  phase4Complete,
  recommendations,
  statisticalApproach,
  statisticalView,
  statisticalResult,
  autoDiscoveryView,
  onNavigate,
}) {
  const isStatisticalBranch =
    statisticalApproach === "statistical" ||
    statisticalApproach === "univariate" ||
    statisticalApproach === "multivariate";

  const isMLBranch =
    statisticalApproach === "ml";
  const isAutomaticDiscovery = Boolean(autoDiscoveryView);

  const workflowItems = isAutomaticDiscovery
    ? [
        ["01", "Dataset Analysis"],
        ["02", "Column Selection"],
        ["03", "Preprocessing & Analysis"],
        ["04", "Automatic Discovery"],
      ]
    : isStatisticalBranch
    ? [
        ["01", "Dataset Analysis"],
        ["02", "Column Selection"],
        ["03", "Preprocessing & Analysis"],
        ["04", "Univariate / Multivariate"],
        ["06", "Anomaly Detection & Visualization"],
      ]
    : isMLBranch
    ? PHASES
    : PHASES.slice(0, 3);

  return (
    <aside className="sidebar">

      <div className="brand">

        <div className="brand-mark">
          IA
        </div>

        <div>
          <div>
            Intelligent
          </div>

          <div>
            Anomaly Insights
          </div>
        </div>

      </div>


      <div className="sidebar-divider" />

      <p className="sidebar-label">
        WORKFLOW
      </p>


      <nav>

        {workflowItems.map(
          ([number, label], index) => {
            const phase =
              index + 1;

            let locked = false;

            if (phase === 1) {
              locked = !summary;
            } else if (phase === 2) {
              locked = !summary;
            } else if (phase === 3) {
              locked =
                !summary ||
                !confirmed;
            } else if (isStatisticalBranch) {
              if (phase === 4) {
                locked =
                  !analysis;
              } else if (phase === 5) {
                locked =
                  !statisticalResult ||
                  !(
                    statisticalView ===
                      "univariate" ||
                    statisticalView ===
                      "multivariate"
                  );
              }
            } else if (isMLBranch) {
              if (phase === 4) {
                locked = !analysis;
              } else if (phase === 5) {
                locked =
                  !phase4Complete;
              } else if (phase === 6) {
                locked =
                  !recommendations;
              }
            }

            const isStatisticalSelectionActive =
              isStatisticalBranch &&
              phase === 4 &&
              statisticalView ===
                "approach";

            const isStatisticalDetectionActive =
              isStatisticalBranch &&
              phase === 5 &&
              (
                statisticalView ===
                  "univariate" ||
                statisticalView ===
                  "multivariate"
              );

            const isActive =
              isStatisticalSelectionActive ||
              isStatisticalDetectionActive ||
              (
                !isStatisticalBranch &&
                activePhase === phase
              );

            let className =
              "phase-nav-item";

            if (isActive) {
              className +=
                " active";
            }

            if (locked) {
              className +=
                " locked";
            }

            return (
              <button
                key={number}
                type="button"
                className={
                  className
                }
                disabled={
                  locked
                }
                onClick={() =>
                  onNavigate(
                    phase
                  )
                }
              >

                <span className="phase-number">
                  {number}
                </span>

                <span>
                  {label}
                </span>

              </button>
            );
          }
        )}

      </nav>


      <div className="sidebar-footer">

        <span className="status-dot" />

        <span>
          Analysis workspace
        </span>

      </div>

    </aside>
  );
}

/* =========================================================
   SECTION HEADING
========================================================= */

function SectionHeading({
  phase,
  title,
  subtitle,
  badge,
}) {
  return (
    <div className="section-heading">

      <div>

        <p className="eyebrow">
          {phase}
        </p>

        <h2>
          {title}
        </h2>

        <p className="section-subtitle">
          {subtitle}
        </p>

      </div>

      {badge && (
        <div className="status-badge">
          {badge}
        </div>
      )}

    </div>
  );
}


/* =========================================================
   PHASE 1
========================================================= */

function Phase1({
  summary,
  onNext,
}) {
  const fileSize =
    Number(
      summary?.file_size_mb || 0
    ).toFixed(2);

  const cards = [
    {
      label: "Rows",
      value: summary?.rows,
      description:
        "Total number of records present in the uploaded dataset.",
    },

    {
      label: "Columns",
      value: summary?.columns,
      description:
        "Total number of columns detected in the uploaded dataset.",
    },

    {
      label: "File Size",
      value:
        `${fileSize} MB`,
      description:
        "Approximate size of the uploaded dataset file.",
    },

    {
      label: "Numeric",
      value: summary?.numeric,
      names:
        summary?.numeric_column_names,
      description:
        "Columns identified as numerical features.",
    },

    {
      label: "Categorical",
      value:
        summary?.categorical,
      names:
        summary?.categorical_column_names,
      description:
        "Columns identified as categorical features.",
    },

    {
      label: "Date / Time",
      value:
        summary?.datetime,
      names:
        summary?.datetime_column_names,
      description:
        "Columns identified as dates or timestamps.",
    },

    {
      label: "Identifiers",
      value:
        summary?.identifiers,
      names:
        summary?.identifier_column_names,
      description:
        "Columns identified as record or entity identifiers.",
    },

    {
      label: "Boolean",
      value:
        summary?.boolean,
      names:
        summary?.boolean_column_names,
      description:
        "Columns containing Boolean values.",
    },

    {
      label: "Null / Empty",
      value:
        summary?.null_empty,
      names:
        summary?.null_column_names,
      description:
        "Columns containing no usable values.",
    },
  ];

  return (
    <section className="workflow-section phase3-page">

      <SectionHeading
        phase="PHASE 01"
        title="Dataset Analysis"
        subtitle="Overview of the uploaded dataset and automatically identified column characteristics."
        badge="Analysis complete"
      />


      <div className="summary-grid">

        {cards.map(
          (card) => (
            <SummaryCard
              key={
                card.label
              }
              {...card}
            />
          )
        )}

      </div>


      <div className="next-step">

        <div>

          <p className="eyebrow">
            NEXT STEP
          </p>

          <h3>
            Column Selection
          </h3>

          <p>
            Choose which dataset columns
            should participate in preprocessing
            and anomaly detection.
          </p>

        </div>

        <button
          type="button"
          className="primary-button"
          onClick={onNext}
        >
          Continue to Column Selection →
        </button>

      </div>

    </section>
  );
}


/* =========================================================
   SUMMARY CARD
========================================================= */

function SummaryCard({
  label,
  value,
  description,
  names,
}) {
  return (
    <div
      className="summary-card"
      tabIndex={0}
    >

      <span className="summary-label">
        {label}
      </span>

      <strong className="summary-value">
        {value ?? 0}
      </strong>


      <div className="summary-popover">

        <div className="popover-header">

          <div>

            <span className="popover-eyebrow">
              DATASET SUMMARY
            </span>

            <h4>
              {label}
            </h4>

          </div>

        </div>

        <p>
          {description}
        </p>


        {names !== undefined && (
          <div className="popover-columns">

            <span>
              Columns in this category
            </span>

            {names?.length ? (
              <div className="chip-list">

                {names.map(
                  (name) => (
                    <span
                      key={name}
                      className="detail-chip"
                    >
                      {name}
                    </span>
                  )
                )}

              </div>
            ) : (
              <span className="muted">
                No columns in this category.
              </span>
            )}

          </div>
        )}

      </div>

    </div>
  );
}


/* =========================================================
   PHASE 2
========================================================= */

function Phase2({
  summary,
  selectedColumns,
  selectedDetail,
  infoColumn,
  onToggle,
  onInfo,
  onCloseInfo,
  onConfirm,
  confirming,
}) {
  const columns =
    summary?.all_column_names ||
    [];


  return (
    <section className="workflow-section">

      <SectionHeading
        phase="PHASE 02"
        title="Column Selection"
        subtitle="Select the columns that will be carried into Phase 3. Click the information icon to inspect any column."
        badge={`${selectedColumns.length} / ${columns.length} selected`}
      />


      <div className="selection-layout">


        {/* ==================================================
            AVAILABLE COLUMNS
        ================================================== */}

        <div className="panel available-panel">

          <div className="panel-header">

            <div>

              <h3>
                Available Columns
              </h3>

              <p>
                Choose the columns to carry
                into preprocessing.
              </p>

            </div>

            <span className="count-pill">
              {columns.length} columns
            </span>

          </div>


          <div className="column-list">

            {columns.map(
              (column, index) => {
                const checked =
                  selectedColumns.includes(
                    column
                  );

                const isInfoOpen =
                  infoColumn ===
                  column;

                const detail =
                  isInfoOpen && selectedDetail
                    ? selectedDetail
                    : {
                        column_name: column,
                        role: "—",
                        data_type: "—",
                        missing_percentage: 0,
                        llm_description:
                          "Generating description...",
                      };
                return (
                  <div
                    className={
                      "column-row" +
                      (checked
                        ? " checked"
                        : "") +
                      (isInfoOpen
                        ? " info-open"
                        : "")
                    }
                    key={column}
                  >

                    <div className="column-main-row">

                      <label className="column-check-label">

                        <input
                          type="checkbox"
                          checked={
                            checked
                          }
                          onChange={() =>
                            onToggle(
                              column
                            )
                          }
                        />

                        <span className="column-index">
                          {String(
                            index + 1
                          ).padStart(
                            2,
                            "0"
                          )}
                        </span>

                        <strong>
                          {column}
                        </strong>

                      </label>


                      <button
                        type="button"
                        className={
                          "info-button" +
                          (isInfoOpen
                            ? " active"
                            : "")
                        }
                        title={
                          isInfoOpen
                            ? "Close column information"
                            : "View column information"
                        }
                        aria-expanded={
                          isInfoOpen
                        }
                        onClick={() =>
                          onInfo(
                            column
                          )
                        }
                      >
                        i
                      </button>

                    </div>


                    {/* ======================================
                        INLINE CLEAN INFORMATION BOX
                    ====================================== */}

                    {isInfoOpen && (
                      <ColumnDetailsDropdown
                        detail={
                          detail
                        }
                        totalRows={
                          summary?.rows
                        }
                        onClose={
                          onCloseInfo
                        }
                      />
                    )}

                  </div>
                );
              }
            )}

          </div>

        </div>


        {/* ==================================================
            SELECTED COLUMNS
        ================================================== */}

        <div className="right-stack">

          <div className="panel selected-panel">

            <div className="panel-header">

              <div>

                <h3>
                  Selected Columns
                </h3>

                <p>
                  These columns will be used
                  throughout Phase 3 and
                  downstream detection.
                </p>

              </div>

              <span className="count-pill">
                {selectedColumns.length} /{" "}
                {columns.length}
              </span>

            </div>


            <div className="selected-list">

              {selectedColumns.length ? (
                selectedColumns.map(
                  (column, index) => (
                    <div
                      className="selected-item"
                      key={column}
                    >

                      <span className="column-index">
                        {String(
                          index + 1
                        ).padStart(
                          2,
                          "0"
                        )}
                      </span>

                      <span>
                        {column}
                      </span>

                    </div>
                  )
                )
              ) : (
                <div className="empty-state">
                  Select at least one
                  column.
                </div>
              )}

            </div>


            <div className="selection-footer">

              <span>
                <strong>
                  {selectedColumns.length}
                </strong>{" "}
                selected
              </span>

              <span>
                {columns.length -
                  selectedColumns.length}{" "}
                excluded
              </span>

            </div>


            <button
              type="button"
              className="primary-button full-width"
              disabled={
                selectedColumns.length ===
                  0 ||
                confirming
              }
              onClick={
                onConfirm
              }
            >
              {confirming
                ? "Confirming..."
                : "Confirm Selection ✓"}
            </button>

          </div>

        </div>

      </div>

    </section>
  );
}


/* =========================================================
   COLUMN DETAILS
========================================================= */

/* =========================================================
   COLUMN DETAILS
   STRICTLY FIVE FIELDS
========================================================= */

function ColumnDetailsDropdown({
  detail,
  onClose,
}) {
  /*
   * ========================================================
   * ONLY THESE FIVE FIELDS ARE DISPLAYED
   * ========================================================
   *
   * 1. Column Name
   * 2. Role
   * 3. Data Type
   * 4. Missing Value %
   * 5. Description
   *
   * NOTHING ELSE.
   *
   * Do not add Object.entries(detail).
   * Do not calculate unique values.
   * Do not calculate missing count.
   * Do not display numeric statistics.
   */

  const columnName =
    detail?.column_name ||
    detail?.name ||
    detail?.column ||
    "—";

  const role =
    detail?.role ||
    "—";

  const dataType =
    detail?.data_type ||
    detail?.dtype ||
    "—";

  const missingPercentage =
    Number(
      detail?.missing_percentage
    );

  const formattedMissingPercentage =
    Number.isFinite(
      missingPercentage
    )
      ? `${missingPercentage.toFixed(2)}%`
      : "—";

  const description =
    detail?.llm_description ||
    "No description available.";


  return (
    <div
      className="column-details-dropdown"
      role="region"
      aria-label={
        `Column information for ${columnName}`
      }
      onClick={(event) =>
        event.stopPropagation()
      }
    >

      {/* ==================================================
          HEADER
      ================================================== */}

      <div className="column-details-dropdown-header">

        <div>

          <span className="popover-eyebrow">
            COLUMN INFORMATION
          </span>

          <h4>
            {columnName}
          </h4>

        </div>

        <button
          type="button"
          className="popover-close"
          onClick={onClose}
          aria-label="Close column information"
        >
          ×
        </button>

      </div>


      {/* ==================================================
          FOUR BASIC FIELDS
      ================================================== */}

      <div className="column-details-grid">

        {/* 1. COLUMN NAME */}

        <DetailItem
          label="Column Name"
          value={columnName}
        />


        {/* 2. ROLE */}

        <DetailItem
          label="Role"
          value={role}
        />


        {/* 3. DATA TYPE */}

        <DetailItem
          label="Data Type"
          value={dataType}
        />


        {/* 4. MISSING VALUE % */}

        <DetailItem
          label="Missing Value %"
          value={
            formattedMissingPercentage
          }
        />

      </div>


      {/* ==================================================
          5. LLM DESCRIPTION
      ================================================== */}

      <div className="column-detail-description">

        <span>
          Description
        </span>

        <p>
          {description}
        </p>

      </div>

    </div>
  );
}


/* =========================================================
   DETAIL ITEM
========================================================= */

function DetailItem({
  label,
  value,
}) {
  return (
    <div className="column-detail-item">

      <span>
        {label}
      </span>

      <strong>
        {value === null ||
        value === undefined ||
        value === ""
          ? "—"
          : String(value)}
      </strong>

    </div>
  );
}




function formatFieldLabel(
  value
) {
  return String(
    value
  )
    .replaceAll(
      "_",
      " "
    )
    .replace(
      /\b\w/g,
      (letter) =>
        letter.toUpperCase()
    );
}


function formatDetailValue(
  value
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  if (
    typeof value ===
    "object"
  ) {
    try {
      return JSON.stringify(
        value
      );
    } catch {
      return String(
        value
      );
    }
  }

  return String(
    value
  );
}


/* =========================================================
   PHASE 3
========================================================= */

function Phase3ActionStatus({ status }) {
  if (status === "done") {
    return (
      <span className="phase3-action-status phase3-action-status-done" aria-label="Completed">
        ✓
      </span>
    );
  }

  if (status === "loading") {
    return (
      <span className="phase3-action-status phase3-action-status-loading" aria-label="In progress">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle className="phase3-progress-track" cx="12" cy="12" r="9" />
          <circle className="phase3-progress-fill" cx="12" cy="12" r="9" />
        </svg>
      </span>
    );
  }

  return null;
}

function Phase3({
  summary,
  selectedColumns,
  inspectionData,
  preprocessResult,
  preview,
  previewPage,
  phase3Loading,
  analysis,
  analysisLoading,
  openSections,
  onInspect,
  onPreprocess,
  onEditColumns,
  onPage,
  onDownloadProcessedDataset,
  onRunAnalysis,
  onToggleAnalysis,
  onContinueToPhase4,
  onProceedStatistical,
  onProceedAutomaticDiscovery,
}) {
  const [preprocessingOpen, setPreprocessingOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [analysisPanelOpen, setAnalysisPanelOpen] = useState(false);

  const [preprocessActionStatus, setPreprocessActionStatus] = useState("idle");
  const [downloadActionStatus, setDownloadActionStatus] = useState("idle");
  const [analysisActionStatus, setAnalysisActionStatus] = useState("idle");

  const runPhase3Action = async (action, setStatus) => {
    setStatus("loading");
    try {
      const success = await action();
      setStatus(success === false ? "idle" : "done");
    } catch {
      setStatus("idle");
    }
  };

  const before =
    inspectionData || {
      row_count:
        summary?.rows,

      columns:
        selectedColumns.map(
          (column) => ({
            column,
            dtype:
              summary
                ?.column_details?.[
                column
              ]?.dtype ||
              "—",

            missing:
              summary
                ?.column_details?.[
                column
              ]?.missing_values ||
              0,

            duplicate_values:
              0,

            missing_records:
              [],

            duplicate_records:
              [],
          })
        ),

      missingTotal:
        selectedColumns.reduce(
          (
            sum,
            column
          ) =>
            sum +
            Number(
              summary
                ?.column_details?.[
                column
              ]?.missing_values ||
                0
            ),
          0
        ),

      exactDuplicateRows:
        0,

      duplicateValueTotal:
        0,
    };


  return (
    <section className="workflow-section">

      <SectionHeading
        phase="PHASE 03"
        title="Preprocessing & Statistical Analysis"
        subtitle="Phase 3 operates only on the columns confirmed in Phase 2."
        badge={`${selectedColumns.length} selected columns`}
      />


      {/* ======================================================
          PREPROCESSING INSPECTION
      ====================================================== */}

      <div className="panel phase3-collapsible-panel">

        <div className="phase3-collapsible-header">

          <button
            type="button"
            className="phase3-section-toggle"
            onClick={() =>
              setPreprocessingOpen((value) => !value)
            }
            aria-expanded={preprocessingOpen}
          >
            <span className="phase3-section-number">01</span>

            <span className="phase3-section-copy">
              <strong>Preprocessing Inspection</strong>
              <span>
                Review detected missing values and duplicate information before preprocessing.
              </span>
            </span>

            <span className="phase3-chevron" aria-hidden="true">
              {preprocessingOpen ? "▴" : "▾"}
            </span>
          </button>

          <button
            type="button"
            className="primary-button phase3-header-action"
            disabled={phase3Loading || !selectedColumns.length}
            onClick={() =>
              runPhase3Action(
                onPreprocess,
                setPreprocessActionStatus
              )
            }
          >
            <span>
              {preprocessActionStatus === "loading"
                ? "Processing..."
                : "Preprocess Dataset"}
            </span>
            <Phase3ActionStatus status={preprocessActionStatus} />
          </button>

        </div>


        {preprocessingOpen && (
          <div className="phase3-collapsible-body">

            <PreprocessingTable
              stats={before}
              onInspect={onInspect}
            />

            <div className="phase-actions">

              <button
                type="button"
                className="secondary-button"
                onClick={onEditColumns}
              >
                ← Edit Columns
              </button>

            </div>

          </div>
        )}

      </div>


      {/* ======================================================
          PREPROCESSED DATASET
      ====================================================== */}

      {preprocessResult && (
        <div className="panel phase3-collapsible-panel">

          <div className="phase3-collapsible-header">

            <button
              type="button"
              className="phase3-section-toggle"
              onClick={() =>
                setPreviewOpen((value) => !value)
              }
              aria-expanded={previewOpen}
            >
              <span className="phase3-section-number">02</span>

              <span className="phase3-section-copy">
                <strong>Preprocessed Dataset</strong>
                <span>
                  Preview the processed data carried forward to analysis.
                </span>
              </span>

              <span className="phase3-chevron" aria-hidden="true">
                {previewOpen ? "▴" : "▾"}
              </span>
            </button>

            <div className="phase3-header-actions">

              <button
                type="button"
                className="secondary-button phase3-header-action"
                disabled={phase3Loading}
                onClick={() =>
                  runPhase3Action(
                    onDownloadProcessedDataset,
                    setDownloadActionStatus
                  )
                }
              >
                <span>
                  {downloadActionStatus === "loading"
                    ? "Downloading..."
                    : "Download Preprocessed Data"}
                </span>
                <Phase3ActionStatus status={downloadActionStatus} />
              </button>

            </div>

          </div>


          {previewOpen && (
            <div className="phase3-collapsible-body">

              {preview ? (
                <DatasetPreview
                  preview={preview}
                  page={previewPage}
                  onPage={onPage}
                  loading={phase3Loading}
                />
              ) : (
                <div className="preview-placeholder">

                  <strong>
                    Preprocessing completed successfully.
                  </strong>

                  <p>
                    The processed dataset is ready.
                    Preview data is still being loaded
                    or was not returned by the backend.
                  </p>

                </div>
              )}

            </div>
          )}

        </div>
      )}


      {/* ======================================================
          STATISTICAL ANALYSIS
      ====================================================== */}

      {preprocessResult && (
        <div className="panel phase3-collapsible-panel">

          <div className="phase3-collapsible-header">

            <button
              type="button"
              className="phase3-section-toggle"
              onClick={() =>
                setAnalysisPanelOpen((value) => !value)
              }
              aria-expanded={analysisPanelOpen}
            >
              <span className="phase3-section-number">03</span>

              <span className="phase3-section-copy">
                <strong>Statistical & Dataset Characteristic Analysis</strong>
                <span>
                  Calculate characteristics used later for dynamic anomaly detection and model recommendation.
                </span>
              </span>

              <span className="phase3-chevron" aria-hidden="true">
                {analysisPanelOpen ? "▴" : "▾"}
              </span>
            </button>

            <button
              type="button"
              className="primary-button phase3-header-action"
              disabled={analysisLoading}
              onClick={() =>
                runPhase3Action(
                  onRunAnalysis,
                  setAnalysisActionStatus
                )
              }
            >
              <span>
                {analysisActionStatus === "loading"
                  ? "Calculating..."
                  : "Run Statistical Analysis"}
              </span>
              <Phase3ActionStatus status={analysisActionStatus} />
            </button>

          </div>


          {analysisPanelOpen && (
            <div className="phase3-collapsible-body">

              {analysis ? (
                <StatisticalAnalysis
                  result={analysis}
                  openSections={openSections}
                  onToggle={onToggleAnalysis}
                />
              ) : (
                <div className="phase3-analysis-empty">
                  Run the statistical analysis to view the 10 dataset characteristics.
                </div>
              )}

            </div>
          )}

        </div>
      )}

      {/* ======================================================
          DETECTION APPROACH
      ====================================================== */}

      {analysis && (
        <div className="next-step phase3-next-step">

          <div className="next-step-copy">

            <p className="eyebrow">
              NEXT STEP
            </p>

            <h3>
              Choose Detection Approach
            </h3>

            <p>
              Choose statistical detection using IQR or Mahalanobis Distance,
              or continue with the existing machine-learning workflow.
            </p>

          </div>

          <div className="phase3-approach-grid">

            <button
              type="button"
              className="phase3-approach-card phase3-approach-primary"
              onClick={onProceedStatistical}
            >
              <span className="phase3-approach-title">
                Statistical Approach
              </span>
              <span className="phase3-approach-description">
                <strong>Univariate:</strong> IQR<br />
                <strong>Multivariate:</strong> Mahalanobis Distance
              </span>
              <span className="phase3-approach-action">
                Select →
              </span>
            </button>

            <button
              type="button"
              className="phase3-approach-card"
              onClick={onProceedAutomaticDiscovery}
            >
              <span className="phase3-approach-title">
                ML Benchmarking Approach
              </span>
              <span className="phase3-approach-description">
                <strong>Model recommendation:</strong><br />
                Empirical benchmarking
              </span>
              <span className="phase3-approach-action">
                Select →
              </span>
            </button>

            <button
              type="button"
              className="phase3-approach-card"
              onClick={onContinueToPhase4}
            >
              <span className="phase3-approach-title">
                ML Objective Based
              </span>
              <span className="phase3-approach-description">
                <strong>Model recommendation:</strong><br />
                Dataset characteristics and objective understanding
              </span>
              <span className="phase3-approach-action">
                Select →
              </span>
            </button>

          </div>

        </div>
      )}

    </section>
  );
}


/* =========================================================
   PREPROCESSING TABLE
========================================================= */

function PreprocessingTable({
  stats,
  onInspect,
}) {
  const columns =
    stats?.columns ||
    [];

  const missingTotal =
    stats?.missingTotal ??
    stats?.missing_total ??
    0;

  const duplicateValueTotal =
    stats?.duplicateValueTotal ??
    stats?.duplicate_value_total ??
    0;

  const exactDuplicateRows =
    stats?.exactDuplicateRows ??
    stats?.exact_duplicate_rows ??
    0;


  return (
    <div className="data-table-wrap">

      <table className="data-table">

        <thead>

          <tr>
            <th>
              Column
            </th>

            <th>
              Data Type
            </th>

            <th>
              Missing Values
            </th>

            <th>
              Duplicate Values
            </th>
          </tr>

        </thead>


        <tbody>

          {columns.map(
            (item) => (
              <tr
                key={
                  item.column
                }
              >

                <td>
                  <strong>
                    {
                      item.column
                    }
                  </strong>
                </td>

                <td>
                  {
                    item.dtype ||
                    "—"
                  }
                </td>

                <td>

                  <CountButton
                    value={
                      item.missing ||
                      0
                    }
                    onClick={() => {

                      if (
                        Number(
                          item.missing
                        ) > 0
                      ) {
                        onInspect({
                          kind:
                            "missing-column",

                          column:
                            item.column,

                          title:
                            `Missing Values · ${item.column}`,
                        });
                      }

                    }}
                  />

                </td>


                <td>

                  <CountButton
                    value={
                      item.duplicate_values ||
                      0
                    }
                    onClick={() => {

                      if (
                        Number(
                          item.duplicate_values
                        ) > 0
                      ) {
                        onInspect({
                          kind:
                            "duplicate-column",

                          column:
                            item.column,

                          title:
                            `Duplicate Values · ${item.column}`,
                        });
                      }

                    }}
                  />

                </td>

              </tr>
            )
          )}


          <tr className="total-row">

            <td>
              <strong>
                TOTAL
              </strong>
            </td>

            <td>
              —
            </td>

            <td>

              <CountButton
                value={
                  missingTotal
                }
                onClick={() => {

                  if (
                    Number(
                      missingTotal
                    ) > 0
                  ) {
                    onInspect({
                      kind:
                        "missing-total",

                      title:
                        "All Missing Values",
                    });
                  }

                }}
              />

            </td>

            <td>

              <CountButton
                value={
                  duplicateValueTotal
                }
                onClick={() => {

                  if (
                    Number(
                      duplicateValueTotal
                    ) > 0
                  ) {
                    onInspect({
                      kind:
                        "duplicate-total",

                      title:
                        "All Duplicate Values",
                    });
                  }

                }}
              />

            </td>

          </tr>

        </tbody>

      </table>


      <div className="table-note">

        Exact duplicate records removed
        during preprocessing:{" "}

        <strong>
          {
            exactDuplicateRows
          }
        </strong>

      </div>

    </div>
  );
}


/* =========================================================
   COUNT BUTTON
========================================================= */

function CountButton({
  value,
  onClick,
}) {
  if (!value) {
    return (
      <span className="zero-count">
        0
      </span>
    );
  }

  return (
    <button
      type="button"
      className="table-count-button"
      onClick={
        onClick
      }
    >
      {value}
    </button>
  );
}


/* =========================================================
   DATASET PREVIEW
========================================================= */

function DatasetPreview({
  preview,
  page,
  onPage,
  loading,
}) {
  const rows =
    preview?.rows ||
    preview?.data ||
    [];

  const columns =
    preview?.columns ||
    Object.keys(
      rows[0] || {}
    );

  const totalPages =
    Number(
      preview?.total_pages ||
        preview?.pages ||
        1
    );


  return (
    <>
      <div className="data-table-wrap">

        {rows.length ? (

          <table className="data-table">

            <thead>

              <tr>

                {columns.map(
                  (column) => (
                    <th
                      key={
                        column
                      }
                    >
                      {
                        column
                      }
                    </th>
                  )
                )}

              </tr>

            </thead>


            <tbody>

              {rows.map(
                (
                  row,
                  index
                ) => (

                  <tr
                    key={
                      row?.__index ??
                      index
                    }
                  >

                    {columns.map(
                      (column) => (

                        <td
                          key={
                            column
                          }
                        >
                          {formatDetailValue(
                            row?.[
                              column
                            ]
                          )}
                        </td>

                      )
                    )}

                  </tr>

                )
              )}

            </tbody>

          </table>

        ) : (

          <div className="empty-state">
            No preview records available.
          </div>

        )}

      </div>


      <div className="pagination">

        <button
          type="button"
          className="secondary-button small"
          disabled={
            loading ||
            page <= 1
          }
          onClick={() =>
            onPage(
              page - 1
            )
          }
        >
          Previous
        </button>


        <span>
          Page{" "}
          {page}{" "}
          of{" "}
          {totalPages}
        </span>


        <button
          type="button"
          className="secondary-button small"
          disabled={
            loading ||
            page >=
              totalPages
          }
          onClick={() =>
            onPage(
              page + 1
            )
          }
        >
          Next
        </button>

      </div>
    </>
  );
}


/* =========================================================
   STATISTICAL ANALYSIS
========================================================= */

function StatisticalAnalysis({
  result,
  openSections,
  onToggle,
}) {
  const sections =
    result?.sections ||
    {};

  const availableSections =
    ANALYSES.filter(
      ([key]) =>
        sections[key]
    );


  return (
    <div className="statistical-section">

      {/* =====================================================
          ANALYSIS SUMMARY
      ===================================================== */}

      <div className="analysis-overview-card">

        <div>

          <strong>
            Analysis completed
          </strong>

          <span>
            {Number(
              result?.records ||
                result?.row_count ||
                0
            ).toLocaleString()}{" "}
            records ×{" "}
            {
              result?.features ??
              result?.feature_count ??
              "—"
            }{" "}
            selected features
          </span>

        </div>


        <div className="analysis-pill">
          10 Characteristics Ready
        </div>

      </div>


      {/* =====================================================
          ANALYSIS ACCORDIONS
      ===================================================== */}

      {availableSections.length >
      0 ? (

        <div className="accordion-list">

          {availableSections.map(
            ([key, title]) => {

              const section =
                sections[key];

              const isOpen =
                Boolean(
                  openSections?.[
                    key
                  ]
                );


              return (
                <div
                  className={
                    "analysis-accordion" +
                    (isOpen
                      ? " open"
                      : "")
                  }
                  key={key}
                >

                  {/* =================================================
                      ACCORDION HEADER
                  ================================================= */}

                  <button
                    type="button"
                    className="analysis-accordion-header"
                    onClick={() =>
                      onToggle(
                        key
                      )
                    }
                  >

                    <span className="accordion-arrow">

                      {isOpen
                        ? "⌄"
                        : "›"}

                    </span>


                    <span>
                      {title}
                    </span>


                    <span className="accordion-status">

                      {
                        section?.result ||
                        "Completed"
                      }

                    </span>

                  </button>


                  {/* =================================================
                      ACCORDION CONTENT
                  ================================================= */}

                  {isOpen && (

                    <div className="analysis-accordion-body">

                      <AnalysisContent
                        keyName={
                          key
                        }
                        section={
                          section
                        }
                      />

                    </div>

                  )}

                </div>
              );
            }
          )}

        </div>

      ) : (

        <div className="empty-state">

          Statistical analysis completed,
          but no analysis characteristics
          were returned by the backend.

        </div>

      )}

    </div>
  );
}


/* =========================================================
   ANALYSIS CONTENT
========================================================= */

function AnalysisContent({
  keyName,
  section,
}) {
  const s =
    section || {};

  let table = null;


  /* =========================================================
     1. DATASET SIZE & DIMENSIONALITY
  ========================================================= */

  if (
    keyName ===
    "overview"
  ) {

    const overview =
      s.dataset_overview ||
      {};

    table = (
      <SimpleTable
        header={[
          "Characteristic",
          "Value",
        ]}
        rows={[
          [
            "Records",
            overview.records,
          ],

          [
            "Selected Features",
            overview.features,
          ],

          [
            "Dataset Size",
            overview.dataset_size,
          ],

          [
            "Dimensionality",
            overview.dimensionality,
          ],

          [
            "Data Type",
            overview.data_type,
          ],
        ]}
      />
    );
  }


  /* =========================================================
     2. DATA TYPE & FEATURE COMPOSITION
  ========================================================= */

  else if (
    keyName ===
    "types"
  ) {

    const composition =
      s.feature_composition ||
      {};

    table = (
      <SimpleTable
        header={[
          "Feature Type",
          "Count",
          "Columns",
        ]}
        rows={[
          [
            "Numerical",
            composition
              .numerical
              ?.count ??
              0,

            (
              composition
                .numerical
                ?.columns ||
              []
            ).join(
              ", "
            ) ||
              "None",
          ],

          [
            "Categorical",
            composition
              .categorical
              ?.count ??
              0,

            (
              composition
                .categorical
                ?.columns ||
              []
            ).join(
              ", "
            ) ||
              "None",
          ],

          [
            "Date / Time",
            composition
              .date_time
              ?.count ??
              0,

            (
              composition
                .date_time
                ?.columns ||
              []
            ).join(
              ", "
            ) ||
              "None",
          ],
        ]}
      />
    );
  }


  /* =========================================================
     3. DISTRIBUTION ANALYSIS
  ========================================================= */

  else if (
    keyName ===
    "distribution"
  ) {

    table = (
      <ComplexTable
        headers={[
          "Feature",
          "Mean",
          "Median",
          "Std",
          "Skewness",
          "Distribution",
        ]}
        rows={(
          s.distribution_statistics ||
          []
        ).map(
          (row) => [
            row.feature,
            row.mean,
            row.median,
            row.std,
            row.skewness,
            row.distribution,
          ]
        )}
      />
    );
  }


  /* =========================================================
     4. EXTREME VALUE ANALYSIS
  ========================================================= */

  else if (
    keyName ===
    "extreme"
  ) {

    table = (
      <ComplexTable
        headers={[
          "Feature",
          "Q1",
          "Q3",
          "IQR",
          "Lower Bound",
          "Upper Bound",
          "Extreme Values",
          "Extreme %",
        ]}
        rows={(
          s.iqr_analysis ||
          []
        ).map(
          (row) => [
            row.feature,
            row.q1,
            row.q3,
            row.iqr,
            row.lower_bound,
            row.upper_bound,
            row.extreme_values,
            row.extreme_percentage,
          ]
        )}
      />
    );
  }


  /* =========================================================
     5. FEATURE SCALE ANALYSIS
  ========================================================= */

  else if (
    keyName ===
    "scale"
  ) {

    const scaleSummary =
      s.scale_summary ||
      {};

    table = (
      <>
        <SimpleTable
          header={[
            "Feature",
            "Minimum",
            "Maximum",
            "Range",
            "Std",
          ]}
          rows={(
            s.feature_scale ||
            []
          ).map(
            (row) => [
              row.feature,
              row.minimum,
              row.maximum,
              row.range,
              row.std,
            ]
          )}
        />

        <div
          className="analysis-secondary-table"
        >

          <SimpleTable
            header={[
              "Scale Measure",
              "Value",
            ]}
            rows={[
              [
                "Smallest Non-Zero Range",
                scaleSummary
                  .smallest_non_zero_range ??
                  "—",
              ],

              [
                "Largest Range",
                scaleSummary
                  .largest_range ??
                  "—",
              ],

              [
                "Range Ratio",
                scaleSummary
                  .range_ratio != null
                  ? `${scaleSummary.range_ratio}×`
                  : "—",
              ],

              [
                "Classification",
                s.result ||
                  "—",
              ],
            ]}
          />

        </div>
      </>
    );
  }


  /* =========================================================
     6. CORRELATION ANALYSIS
  ========================================================= */

  else if (
    keyName ===
    "correlation"
  ) {

    table = (
      <>

        <ComplexTable
          headers={[
            "Feature A",
            "Feature B",
            "Pearson r",
            "Relationship",
          ]}
          rows={(
            s.pearson_correlation ||
            []
          ).map(
            (row) => [
              row.feature_a,
              row.feature_b,
              row.correlation,
              row.relationship,
            ]
          )}
        />

        {s.summary && (
          <div
            className="analysis-secondary-table"
          >

            <SimpleTable
              header={[
                "Correlation Measure",
                "Value",
              ]}
              rows={[
                [
                  "Feature Pairs Analyzed",
                  s.summary
                    .feature_pairs_analyzed ??
                    "—",
                ],

                [
                  "Strongest |r|",
                  s.summary
                    .strongest_absolute_correlation ??
                    "—",
                ],
              ]}
            />

          </div>
        )}

      </>
    );
  }


  /* =========================================================
     7. CLUSTER STRUCTURE ANALYSIS
  ========================================================= */

  else if (
    keyName ===
    "cluster"
  ) {

    const cluster =
      s.cluster_analysis ||
      {};

    table = (
      <>

        <SimpleTable
          header={[
            "Characteristic",
            "Value",
          ]}
          rows={[
            [
              "Estimated Clusters",
              cluster
                .estimated_clusters ??
                "—",
            ],

            [
              "Best Silhouette Score",
              cluster
                .silhouette_score ??
                "—",
            ],

            [
              "Cluster Structure",
              cluster
                .cluster_structure ??
                "—",
            ],
          ]}
        />


        {(
          cluster.cluster_scores ||
          []
        ).length > 0 && (

          <div
            className="analysis-secondary-table"
          >

            <ComplexTable
              headers={[
                "Clusters Tested",
                "Silhouette Score",
              ]}
              rows={(
                cluster.cluster_scores ||
                []
              ).map(
                (row) => [
                  row.clusters,
                  row.silhouette_score,
                ]
              )}
            />

          </div>

        )}

      </>
    );
  }


  /* =========================================================
     8. LOCAL DENSITY & NEIGHBORHOOD
  ========================================================= */

  else if (
    keyName ===
    "density"
  ) {

    const density =
      s.density_analysis ||
      {};

    table = (
      <SimpleTable
        header={[
          "Density Measure",
          "Value",
        ]}
        rows={[
          [
            "Observations Analyzed",
            density
              .observations_analyzed ??
              "—",
          ],

          [
            "Mean Nearest-Neighbor Distance",
            density
              .mean_nearest_neighbor_distance ??
              "—",
          ],

          [
            "Density Variation (CV)",
            density
              .density_variability_cv ??
              "—",
          ],

          [
            "Local Density",
            density
              .local_density ??
              "—",
          ],
        ]}
      />
    );
  }


  /* =========================================================
     9. TEMPORAL STRUCTURE
  ========================================================= */

  else if (
    keyName ===
    "temporal"
  ) {

    const temporal =
      s.temporal_structure ||
      {};

    table = (
      <SimpleTable
        header={[
          "Temporal Measure",
          "Value",
        ]}
        rows={[
          [
            "Temporal Column",
            temporal
              .temporal_column ??
              "—",
          ],

          [
            "Valid Timestamps",
            temporal
              .valid_timestamps ??
              0,
          ],

          [
            "Invalid / Missing Timestamps",
            temporal
              .invalid_or_missing_timestamps ??
              0,
          ],

          [
            "Chronological Ordering",
            temporal
              .chronological_ordering ??
              "—",
          ],

          [
            "Typical Interval",
            temporal.interval != null
              ? `${temporal.interval} ${temporal.interval_unit || ""}`.trim()
              : "—",
          ],

          [
            "Regular Intervals",
            temporal
              .regular_intervals ??
              "—",
          ],

          [
            "Temporal Structure",
            temporal
              .temporal_structure ??
              "—",
          ],
        ]}
      />
    );
  }


  /* =========================================================
     10. TIME-SERIES PATTERN ANALYSIS
  ========================================================= */

  else if (
    keyName ===
    "timeseries"
  ) {

    const summary =
      s.time_series_summary ||
      {};

    table = (
      <>

        <SimpleTable
          header={[
            "Measure",
            "Value",
          ]}
          rows={[
            [
              "Temporal Column",
              summary
                .temporal_column ??
                "—",
            ],

            [
              "Selected Numerical Signal",
              summary
                .selected_signal ??
                "—",
            ],

            [
              "Lag",
              summary
                .lag ??
                "—",
            ],

            [
              "Strongest Lag-1 Autocorrelation",
              summary
                .autocorrelation ??
                "—",
            ],

            [
              "Result",
              s.result ||
                "—",
            ],
          ]}
        />


        {(
          s.pattern_analysis ||
          []
        ).length > 0 && (

          <div
            className="analysis-secondary-table"
          >

            <ComplexTable
              headers={[
                "Feature",
                "Observations",
                "Lag",
                "Autocorrelation",
                "Interpretation",
              ]}
              rows={(
                s.pattern_analysis ||
                []
              ).map(
                (row) => [
                  row.feature,
                  row.observations,
                  row.lag,
                  row.autocorrelation,
                  row.interpretation,
                ]
              )}
            />

          </div>

        )}

      </>
    );
  }


  /* =========================================================
     FALLBACK
  ========================================================= */

  else {

    const genericRows =
      Object.entries(s)
        .filter(
          ([key]) =>
            key !==
            "inferences"
        )
        .map(
          ([key, value]) => [
            formatFieldLabel(
              key
            ),

            typeof value ===
            "object"
              ? JSON.stringify(
                  value
                )
              : value,
          ]
        );


    table =
      genericRows.length
        ? (
          <SimpleTable
            header={[
              "Characteristic",
              "Value",
            ]}
            rows={
              genericRows
            }
          />
        )
        : (
          <div className="empty-state">
            No detailed observations
            available.
          </div>
        );
  }


  /* =========================================================
     FINAL CONTENT
  ========================================================= */

  return (
    <>

      <h4>
        {contentTitle(
          keyName
        )}
      </h4>


      {table}


      {/* =====================================================
          WHAT THIS ANALYSIS INDICATES
      ===================================================== */}

      {(
        s.inferences ||
        []
      ).length > 0 && (

        <div className="inference-box">

          <strong>
            What this analysis indicates
          </strong>


          <ul>

            {(
              s.inferences ||
              []
            )
              .slice(
                0,
                3
              )
              .map(
                (
                  text,
                  index
                ) => (

                  <li
                    key={
                      index
                    }
                  >
                    {text}
                  </li>

                )
              )}

          </ul>

        </div>

      )}

    </>
  );
}



function SimpleTable({
  header,
  rows,
}) {
  return (
    <div className="data-table-wrap">

      <table className="data-table">

        {header && (
          <thead>
            <tr>
              {header.map(
                (item) => (
                  <th
                    key={
                      item
                    }
                  >
                    {item}
                  </th>
                )
              )}
            </tr>
          </thead>
        )}

        <tbody>

          {rows.map(
            (row, index) => (
              <tr
                key={
                  index
                }
              >

                {row.map(
                  (
                    value,
                    valueIndex
                  ) => (
                    <td
                      key={
                        valueIndex
                      }
                    >
                      {formatDetailValue(
                        value
                      )}
                    </td>
                  )
                )}

              </tr>
            )
          )}

        </tbody>

      </table>

    </div>
  );
}


function ComplexTable({
  headers,
  rows,
}) {
  if (
    !rows?.length
  ) {
    return (
      <div className="empty-state">
        No valid observations were
        available for this analysis.
      </div>
    );
  }

  return (
    <div className="data-table-wrap">

      <table className="data-table">

        <thead>

          <tr>

            {headers.map(
              (heading) => (
                <th
                  key={
                    heading
                  }
                >
                  {heading}
                </th>
              )
            )}

          </tr>

        </thead>


        <tbody>

          {rows.map(
            (
              row,
              rowIndex
            ) => (

              <tr
                key={
                  rowIndex
                }
              >

                {row.map(
                  (
                    value,
                    valueIndex
                  ) => (

                    <td
                      key={
                        valueIndex
                      }
                    >
                      {valueIndex ===
                      0 ? (
                        <strong>
                          {formatDetailValue(
                            value
                          )}
                        </strong>
                      ) : (
                        formatDetailValue(
                          value
                        )
                      )}
                    </td>

                  )
                )}

              </tr>

            )
          )}

        </tbody>

      </table>

    </div>
  );
}


function contentTitle(
  key
) {
  const titles = {
    overview:
      "Dataset Overview",

    types:
      "Feature Composition",

    distribution:
      "Distribution Statistics",

    extreme:
      "IQR Extreme-Value Analysis",

    scale:
      "Feature Range & Scale",

    correlation:
      "Pearson Correlation",

    cluster:
      "K-Means Cluster Structure",

    density:
      "Nearest-Neighbor Density",

    temporal:
      "Temporal Structure",

    timeseries:
      "Time-Series Pattern Analysis",
  };

  return (
    titles[key] ||
    "Analysis"
  );
}


/* =========================================================
   PHASE 4
========================================================= */

function formatAnomalyType(value) {
  if (!value) {
    return "Not determined";
  }

  const normalized = String(value)
    .trim()
    .toLowerCase();

  if (normalized === "point") {
    return "Point Anomaly";
  }

  if (normalized === "contextual") {
    return "Contextual Anomaly";
  }

  if (normalized === "collective") {
    return "Collective Anomaly";
  }

  return String(value);
}

function Phase4({
  detectionObjective,
  objectiveValidation,
  objectiveLoading,
  phase4Complete,
  recommendationLoading,
  selectedColumns = [],
  onObjectiveChange,
  onValidateObjective,
  onRecommendModels,
  onReturnToPhase2,
}) {

  const understanding =
    objectiveValidation?.objective_understanding ||
    objectiveValidation?.objective ||
    objectiveValidation ||
    {};

  const interpretedObjective =
    understanding?.interpreted_objective ||
    understanding?.objective_understanding ||
    understanding?.explanation ||
    objectiveValidation?.interpreted_objective ||
    "";

  const anomalyTypeValue =
    understanding?.anomaly_type ||
    objectiveValidation?.anomaly_type ||
    "";

  const anomalyReason =
    understanding?.anomaly_type_reason ||
    understanding?.why_anomaly_type ||
    understanding?.reason ||
    objectiveValidation?.anomaly_type_reason ||
    objectiveValidation?.reason ||
    "";

  /*
   * ==========================================================
   * ATTRIBUTE SELECTION VALIDATION
   * ==========================================================
   *
   * This comparison is deterministic.
   *
   * Required columns come from the backend's semantic
   * attributes_involved result. Selected columns come from
   * the latest Phase 2 state held by App.jsx.
   */
  const requiredObjectiveColumns =
    getObjectiveRequiredColumns(
      objectiveValidation
    );

  const missingObjectiveColumns =
    getMissingObjectiveColumns(
      objectiveValidation,
      selectedColumns
    );

  const attributeSelectionValid =
    missingObjectiveColumns.length === 0;

  const showAttributeValidation =
    Boolean(objectiveValidation) &&
    requiredObjectiveColumns.length > 0 &&
    !attributeSelectionValid;

  /*
   * ==========================================================
   * ATTRIBUTES INVOLVED
   * ==========================================================
   *
   * Primary source:
   *
   *     attributes_involved
   *
   * Compatibility fallback:
   *
   *     target_columns
   *     reference_columns
   *     context_columns
   *
   * No domain-specific column names are hardcoded.
   */

  const rawAttributes =
    understanding?.attributes_involved ||
    objectiveValidation?.attributes_involved ||
    [];

  const rawTargets =
    understanding?.target_columns ||
    objectiveValidation?.target_columns ||
    [];

  const rawReferences =
    understanding?.reference_columns ||
    objectiveValidation?.reference_columns ||
    [];

  const rawContexts =
    understanding?.context_columns ||
    objectiveValidation?.context_columns ||
    [];


  /*
   * Normalize any backend representation into the
   * frontend representation used by the table.
   */

  const normalizeAttribute = (
    item,
    fallbackRole = "supporting_feature"
  ) => {

    if (typeof item === "string") {

      return {
        name: item,
        role: fallbackRole,
        reason: "",
        confidence: 0,
      };

    }

    if (!item || typeof item !== "object") {
      return null;
    }

    return {
      name:
        item.column ||
        item.name ||
        item.column_name ||
        "",

      role:
        item.role ||
        fallbackRole,

      reason:
        item.reason ||
        item.evidence ||
        item.explanation ||
        item.why_relevant ||
        "",

      confidence:
        Number(
          item.confidence
        ) || 0,
    };
  };


  /*
   * Preferred semantic attribute list.
   */

  let attributesInvolved =
    Array.isArray(rawAttributes)
      ? rawAttributes
          .map((item) =>
            normalizeAttribute(
              item
            )
          )
          .filter(
            (item) =>
              item &&
              item.name
          )
      : [];


  /*
   * Compatibility fallback.
   *
   * This only uses information already returned by the backend.
   * It never invents column names.
   */

  if (
    attributesInvolved.length === 0
  ) {

    const fallback = [
      ...(
        Array.isArray(
          rawTargets
        )
          ? rawTargets.map(
              (item) =>
                normalizeAttribute(
                  item,
                  "detection_feature"
                )
            )
          : []
      ),

      ...(
        Array.isArray(
          rawReferences
        )
          ? rawReferences.map(
              (item) =>
                normalizeAttribute(
                  item,
                  "reference_feature"
                )
            )
          : []
      ),

      ...(
        Array.isArray(
          rawContexts
        )
          ? rawContexts.map(
              (item) =>
                normalizeAttribute(
                  item,
                  "context_feature"
                )
            )
          : []
      ),
    ].filter(Boolean);


    /*
     * Deduplicate by actual column name.
     */

    const seen =
      new Set();

    attributesInvolved =
      fallback.filter(
        (item) => {

          if (
            seen.has(
              item.name
            )
          ) {
            return false;
          }

          seen.add(
            item.name
          );

          return true;
        }
      );
  }


  function formatAttributeRole(
    value
  ) {

    if (!value) {
      return "Relevant Attribute";
    }

    const normalized =
      String(value)
        .trim()
        .toLowerCase()
        .replace(
          /\s+/g,
          "_"
        );

    if (
      normalized ===
        "detection_feature" ||
      normalized ===
        "detection" ||
      normalized ===
        "target"
    ) {
      return "Detection Feature";
    }

    if (
      normalized ===
        "entity_identifier" ||
      normalized ===
        "entity"
    ) {
      return "Entity Identifier";
    }

    if (
      normalized ===
        "temporal_feature" ||
      normalized ===
        "temporal"
    ) {
      return "Temporal Feature";
    }

    if (
      normalized ===
        "reference_feature" ||
      normalized ===
        "reference"
    ) {
      return "Reference Feature";
    }

    if (
      normalized ===
        "context_feature" ||
      normalized ===
        "context"
    ) {
      return "Context Feature";
    }

    if (
      normalized ===
        "supporting_feature" ||
      normalized ===
        "supporting"
    ) {
      return "Supporting Feature";
    }

    return String(
      value
    );
  }


  return (
    <section className="workflow-section phase4-objective-section">

      <SectionHeading
        phase="PHASE 04"
        title="Objective Understanding"
        subtitle="Describe what you want to detect in natural language. The system interprets your objective using the current dataset context."
        badge={
          phase4Complete
            ? "Objective understood"
            : "Objective required"
        }
      />


      {/* ======================================================
          OBJECTIVE INPUT
      ====================================================== */}

      <div className="panel phase4-objective-input">

        <div className="panel-header">

          <div>

            <h3>
              Describe what you want to detect
            </h3>

            <p>
              You do not need to specify an anomaly
              type or machine-learning method. The
              backend determines the appropriate
              interpretation from your objective and
              dataset context.
            </p>

          </div>

        </div>


        <textarea
          className="objective-textarea"
          rows={6}
          value={
            detectionObjective
          }
          onChange={(event) =>
            onObjectiveChange(
              event.target.value
            )
          }
          placeholder="Example: I want to identify transactions that are normal overall but unusual for the specific entity involved or during the relevant time period."
        />


        <div className="phase-actions">

          <button
            type="button"
            className="primary-button"
            disabled={
              objectiveLoading ||
              !detectionObjective.trim()
            }
            onClick={
              onValidateObjective
            }
          >
            {objectiveLoading
              ? "Understanding Objective..."
              : "Understand Objective"}
          </button>

        </div>

      </div>


      {/* ======================================================
          SEMANTIC RESULT
      ====================================================== */}

      {objectiveValidation && (

        <div className="phase4-result-card">


          {/* ==================================================
              OBJECTIVE UNDERSTANDING
          ================================================== */}

          <div className="phase4-result-block">

            <div className="phase4-result-label">
              Objective Understanding
            </div>

            <p className="phase4-understanding-text">

              {interpretedObjective ||
                "No objective interpretation was returned."}

            </p>

          </div>


          {/* ==================================================
              ANOMALY TYPE
          ================================================== */}

          <div className="phase4-result-block">

            <div className="phase4-result-label">
              Anomaly Type
            </div>

            <div className="phase4-anomaly-type">

              {formatAnomalyType(
                anomalyTypeValue
              )}

            </div>

          </div>


          {/* ==================================================
              WHY THIS FITS
          ================================================== */}

          <div className="phase4-result-block">

            <div className="phase4-result-label">
              Why this fits
            </div>

            <p className="phase4-reason-text">

              {anomalyReason ||
                "The inferred anomaly type is based on the semantic interpretation of the objective and the available dataset context."}

            </p>

          </div>


          {/* ==================================================
              ATTRIBUTES INVOLVED
          ================================================== */}

          <div className="phase4-result-block">

            <div className="phase4-result-label">
              Attributes Involved in Objective
            </div>

            <p className="phase4-attribute-intro">
              These are the selected dataset attributes that
              materially participate in the objective, including
              the variable being examined and the attributes
              that define its comparison context.
            </p>


            {attributesInvolved.length > 0 ? (

              <div className="phase4-target-table-wrap">

                <table className="phase4-target-table phase4-attributes-table">

                  <thead>

                    <tr>

                      <th>
                        #
                      </th>

                      <th>
                        Column
                      </th>

                      <th>
                        Role
                      </th>

                      <th>
                        Why it is relevant
                      </th>

                    </tr>

                  </thead>


                  <tbody>

                    {attributesInvolved.map(
                      (
                        item,
                        index
                      ) => (

                        <tr
                          key={
                            `${item.name}-${index}`
                          }
                        >

                          <td className="phase4-index-cell">

                            {index + 1}

                          </td>


                          <td>

                            <strong>
                              {item.name}
                            </strong>

                          </td>


                          <td>

                            <span className="phase4-role-badge">

                              {formatAttributeRole(
                                item.role
                              )}

                            </span>

                          </td>


                          <td>

                            {item.reason ||
                              "This attribute was identified through semantic analysis as materially relevant to the stated objective."}

                          </td>

                        </tr>

                      )
                    )}

                  </tbody>

                </table>

              </div>

            ) : (

              <div className="phase4-no-targets">

                No objective-relevant attributes could
                be identified confidently from the current
                objective and selected dataset columns.

              </div>

            )}

          </div>

        </div>

      )}


      {/* ======================================================
          ATTRIBUTE SELECTION VALIDATION
      ====================================================== */}

      {showAttributeValidation && (
        <div
          className="panel"
          style={{
            marginTop: "18px",
            border: "1px solid rgba(248, 113, 113, 0.38)",
            background:
              "linear-gradient(145deg, rgba(127,29,29,.16), rgba(69,10,10,.10))",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "12px",
            }}
          >
            <div
              style={{
                flex: "0 0 30px",
                width: "30px",
                height: "30px",
                display: "grid",
                placeItems: "center",
                borderRadius: "9px",
                background: "rgba(248,113,113,.14)",
                border: "1px solid rgba(248,113,113,.22)",
                color: "#fca5a5",
                fontWeight: 900,
              }}
            >
              !
            </div>

            <div style={{ flex: 1 }}>
              <p
                className="eyebrow"
                style={{
                  marginBottom: "5px",
                  color: "#fca5a5",
                }}
              >
                ATTRIBUTE SELECTION VALIDATION
              </p>

              <h3
                style={{
                  margin: 0,
                  fontSize: "15px",
                  color: "#fee2e2",
                }}
              >
                Required attribute not selected in Phase 2
              </h3>

              <p
                style={{
                  margin: "10px 0 0",
                  color: "#c7b8c1",
                  lineHeight: 1.6,
                  fontSize: "12px",
                }}
              >
                The current investigation objective requires the
                following attribute(s), but they were not included
                in your confirmed Phase 2 Dataset-Level Attribute
                Selection.
              </p>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "8px",
                  marginTop: "12px",
                }}
              >
                {missingObjectiveColumns.map(
                  (column) => (
                    <span
                      key={column}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "7px 10px",
                        borderRadius: "8px",
                        background: "rgba(248,113,113,.10)",
                        border: "1px solid rgba(248,113,113,.22)",
                        color: "#fecaca",
                        fontSize: "11px",
                        fontWeight: 800,
                      }}
                    >
                      <span>✕</span>
                      {column}
                    </span>
                  )
                )}
              </div>

              <div
                style={{
                  marginTop: "14px",
                  padding: "12px 13px",
                  borderRadius: "10px",
                  background: "rgba(255,255,255,.025)",
                  border:
                    "1px solid rgba(248,113,113,.12)",
                }}
              >
                <strong
                  style={{
                    color: "#fda4af",
                    fontSize: "11px",
                  }}
                >
                  Action Required
                </strong>

                <ol
                  style={{
                    margin: "8px 0 0 18px",
                    padding: 0,
                    color: "#c7b8c1",
                    fontSize: "11px",
                    lineHeight: 1.7,
                  }}
                >
                  <li>
                    Return to Phase 2 and reselect the required
                    attribute(s).
                  </li>
                  <li>
                    Confirm the Phase 2 selection.
                  </li>
                  <li>
                    Proceed through Phase 3 Preprocessing and
                    Statistical Analysis.
                  </li>
                  <li>
                    Return to Phase 4. The framework will
                    automatically revalidate the objective.
                  </li>
                </ol>
              </div>

              <div
                style={{
                  marginTop: "12px",
                  color: "#fca5a5",
                  fontSize: "10px",
                  fontWeight: 800,
                }}
              >
                ● Validation Failed — Required attribute missing
              </div>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "10px",
                  marginTop: "14px",
                }}
              >
                <button
                  type="button"
                  className="secondary-button"
                  onClick={
                    onReturnToPhase2
                  }
                >
                  ← Return to Phase 2
                </button>

                <button
                  type="button"
                  className="primary-button"
                  disabled
                  title="Complete the required Phase 2 and Phase 3 steps first."
                >
                  Next: Model Recommendation 🔒
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================
          NEXT PHASE
      ====================================================== */}

      {phase4Complete && attributeSelectionValid && (

        <div className="next-step phase4-next-step">

          <div>

            <p className="eyebrow">
              NEXT PHASE
            </p>

            <h3>
              Model Recommendation
            </h3>

            <p>
              Continue to Phase 5 to select suitable
              anomaly detection models using the
              statistical evidence and objective
              understanding.
            </p>

          </div>


          <button
            type="button"
            className="primary-button"
            disabled={
              recommendationLoading ||
              !attributeSelectionValid
            }
            onClick={
              onRecommendModels
            }
          >

            {recommendationLoading
              ? "Recommending..."
              : "Continue to Phase 5 →"}

          </button>

        </div>

      )}

    </section>
  );
}

/* =========================================================
   PHASE 5
========================================================= */

function Phase5({
  recommendations,
  recommendationLoading,
  onContinueToPhase6,
}) {
  /*
   * The backend ranks the supported models.
   * Phase 5 intentionally displays ONLY the top three.
   *
   * No Phase 1–4 logic is changed here.
   */
  const rawModels =
    recommendations?.recommendations ||
    recommendations?.recommended_models ||
    recommendations?.models ||
    [];

  const models =
    Array.isArray(rawModels)
      ? rawModels.slice(0, 3)
      : [];

  return (
    <section className="workflow-section">

      <SectionHeading
        phase="PHASE 05"
        title="Model Recommendation"
        subtitle="Top model recommendations generated from the 10 Phase 3 statistical characteristics and Phase 4 objective compatibility."
        badge={
          models.length
            ? "Top 3 recommendations"
            : "Recommendation"
        }
      />

      {recommendationLoading && (
        <StatusCard
          text="Generating recommendations"
          detail="The backend is evaluating the supported anomaly detection models using the dataset evidence and Phase 4 objective."
        />
      )}

      {!recommendationLoading && !models.length && (
        <div className="empty-state">
          No model recommendations were returned.
        </div>
      )}

      {!recommendationLoading && models.length > 0 && (
        <div className="phase5-recommendations">

          <div className="phase5-section-heading">
            <div>
              <p className="eyebrow">
                MODEL SELECTION
              </p>

              <h3>
                🏆 Recommended Models
              </h3>

              <p>
                The three highest-scoring models are shown below.
                Click the score on the right to view the complete
                scoring breakdown.
              </p>
            </div>
          </div>


          <div className="phase5-model-list">

            {models.map((model, index) => (
              <Phase5ModelCard
                key={
                  model?.model ||
                  model?.display_name ||
                  index
                }
                model={model}
                rank={
                  Number(model?.rank) > 0
                    ? Number(model.rank)
                    : index + 1
                }
              />
            ))}

          </div>

        </div>
      )}

      {!recommendationLoading &&
        models.length > 0 &&
        onContinueToPhase6 && (
          <div className="next-step phase5-next-step">
            <div>
              <p className="eyebrow">
                NEXT PHASE
              </p>

              <h3>
                Anomaly Detection
              </h3>

              <p>
                Configure Best Score or Combined Score, choose any
                Phase 2 selected columns for detection and explanation,
                then train the recommended PyOD model or models.
              </p>
            </div>

            <button
              type="button"
              className="primary-button"
              onClick={
                onContinueToPhase6
              }
            >
              Continue to Phase 6 →
            </button>
          </div>
        )}

    </section>
  );
}


/* =========================================================
   PHASE 5 MODEL CARD
========================================================= */

function Phase5ModelCard({
  model,
  rank,
}) {
  const [open, setOpen] = useState(false);

  const MODEL_DISPLAY_NAMES = {
    ECOD: "Empirical Cumulative Distribution-based Outlier Detection",
    IForest: "Isolation Forest",
    IsolationForest: "Isolation Forest",
    COPOD: "Copula-Based Outlier Detection",
    KNN: "K-Nearest Neighbors",
    LOF: "Local Outlier Factor",
    CBLOF: "Cluster-Based Local Outlier Factor",
    HBOS: "Histogram-Based Outlier Score",
    MatrixProfile: "Matrix Profile",
    SpectralResidual: "Spectral Residual",
    KShape: "K-Shape",
  };

  const rawModelName =
    model?.display_name ||
    model?.model ||
    model?.name ||
    "Unknown Model";

  const modelName =
    MODEL_DISPLAY_NAMES[String(rawModelName).trim()] ||
    rawModelName;

  const category =
    model?.category ||
    model?.model_category ||
    "";

  const description =
    model?.description ||
    "";

  const finalScore = Number(
    model?.final_score ?? 0
  );

  const statisticalScore = Number(
    model?.statistical_score ?? 0
  );

  const objectiveScore = Number(
    model?.objective_score ?? 0
  );

  const statisticalDetails =
    Array.isArray(
      model?.statistical_details
    )
      ? model.statistical_details
      : [];

  const objectiveDetails =
    Array.isArray(
      model?.objective_details
    )
      ? model.objective_details
      : [];

  const formatScore = (value) => {
    const number = Number(value);

    return Number.isFinite(number)
      ? number.toFixed(2)
      : "0.00";
  };

  return (
    <article
      className={
        "phase5-model-card" +
        (rank === 1
          ? " phase5-top-card"
          : "")
      }
    >

      {/* ==================================================
          CARD HEADER
          The final score itself is the ONLY score toggle.
      ================================================== */}

      <div className="phase5-card-header">

        <div className="phase5-rank-block">

          <span className="phase5-rank">
            #{rank}
          </span>

          <span className="phase5-rank-label">
            {rank === 1
              ? "TOP RECOMMENDATION"
              : "RECOMMENDED MODEL"}
          </span>

        </div>


        <button
          type="button"
          className={
            "phase5-final-score" +
            (open
              ? " phase5-final-score-open"
              : "")
          }
          onClick={() =>
            setOpen(
              (current) => !current
            )
          }
          aria-expanded={open}
          aria-label={
            `${open ? "Hide" : "Show"} score details for ${modelName}`
          }
        >

          <strong>
            {formatScore(finalScore)}
          </strong>

          <span>
            /100
          </span>

          <small
            aria-hidden="true"
          >
            {open ? "⌃" : "⌄"}
          </small>

        </button>

      </div>


      {/* ==================================================
          COMPACT MODEL INFORMATION
          This is all that is visible before score click.
      ================================================== */}

      <div className="phase5-model-main">

        <div className="phase5-model-title">

          <h3>
            {modelName}
          </h3>

          {category && (
            <span className="phase5-model-category">
              {category}
            </span>
          )}

        </div>


        {description && (
          <p className="phase5-model-description">
            {description}
          </p>
        )}


        {/* ==================================================
            COMPLETE SCORE DETAILS
            Appears only after clicking the final score.
        ================================================== */}

        {open && (
          <div className="phase5-score-breakdown">

            <Phase5ScoreSection
              title="Statistical Suitability"
              score={statisticalScore}
              maximum={70}
              details={statisticalDetails}
            />

            <Phase5ScoreSection
              title="Objective Compatibility"
              score={objectiveScore}
              maximum={30}
              details={objectiveDetails}
            />

          </div>
        )}

      </div>

    </article>
  );
}


/* =========================================================
   PHASE 5 SCORE SECTION
   Details are shown immediately when the model score is opened.
========================================================= */

function Phase5ScoreSection({
  title,
  score,
  maximum,
  details,
}) {
  const safeScore = Number(score);

  return (
    <div className="phase5-score-section">

      <div className="phase5-score-section-header">

        <span>
          <span
            className="phase5-score-section-arrow"
            aria-hidden="true"
          >
            ▼
          </span>

          {title}
        </span>

        <strong>
          {Number.isFinite(safeScore)
            ? safeScore.toFixed(2)
            : "0.00"}
          /{maximum}
        </strong>

      </div>


      <div className="phase5-detail-table-wrapper">

        {Array.isArray(details) &&
        details.length ? (

          <table className="phase5-detail-table">

            <thead>

              <tr>

                <th>
                  Characteristic
                </th>

                <th>
                  Score
                </th>

                <th>
                  Maximum
                </th>

              </tr>

            </thead>


            <tbody>

              {details.map(
                (item, index) => {

                  const name =
                    item?.factor ||
                    item?.name ||
                    "—";

                  const itemScore =
                    Number(
                      item?.score ?? 0
                    );

                  const maximumScore =
                    item?.maximum ??
                    item?.max_score ??
                    "—";

                  return (
                    <tr
                      key={
                        `${name}-${index}`
                      }
                    >

                      <td>
                        <strong>
                          {name}
                        </strong>
                      </td>

                      <td>
                        {Number.isFinite(
                          itemScore
                        )
                          ? itemScore.toFixed(2)
                          : "0.00"}
                      </td>

                      <td>
                        {maximumScore}
                      </td>

                    </tr>
                  );
                }
              )}

            </tbody>

          </table>

        ) : (

          <div className="phase5-no-details">
            No detailed scoring evidence was returned.
          </div>

        )}

      </div>

    </div>
  );
}


/* =========================================================
   INSPECTION MODAL
========================================================= */

function InspectionModal({
  payload,
  data,
  loading,
  onClose,
}) {
  const title =
    payload?.title ||
    "Record Inspection";


  return (
    <div className="modal-backdrop">

      <div className="modal-card inspection-modal">

        <button
          type="button"
          className="modal-close"
          onClick={
            onClose
          }
        >
          ×
        </button>


        <p className="eyebrow">
          DATA INSPECTION
        </p>

        <h3>
          {title}
        </h3>


        {loading ? (

          <div className="inspection-loading">
            Loading affected records…
          </div>

        ) : payload?.kind ===
            "missing-column" &&
          Array.isArray(
            data
          ) ? (

          <InspectionMissing
            rows={
              data
            }
          />

        ) : payload?.kind ===
            "duplicate-column" &&
          Array.isArray(
            data
          ) ? (

          <InspectionDuplicate
            groups={
              data
            }
          />

        ) : payload?.kind ===
            "missing-total" &&
          Array.isArray(
            data
          ) ? (

          <InspectionMissing
            rows={
              data
            }
            showColumn
          />

        ) : payload?.kind ===
            "duplicate-total" &&
          Array.isArray(
            data
          ) ? (

          <InspectionExactDuplicate
            rows={
              data
            }
          />

        ) : (

          <div className="empty-state">
            No affected records were found.
          </div>

        )}


        <button
          type="button"
          className="secondary-button"
          onClick={
            onClose
          }
        >
          Close
        </button>

      </div>

    </div>
  );
}


function InspectionMissing({
  rows,
  showColumn = false,
}) {
  return (
    <>
      <p>
        {rows.length} missing
        value(s) found.
      </p>

      <div className="data-table-wrap modal-table">

        <table className="data-table">

          <thead>

            <tr>

              {showColumn && (
                <th>
                  Column
                </th>
              )}

              <th>
                Index
              </th>

              <th>
                Identifier
              </th>

              <th>
                Missing Value
              </th>

            </tr>

          </thead>


          <tbody>

            {rows.map(
              (
                row,
                index
              ) => (

                <tr
                  key={
                    index
                  }
                >

                  {showColumn && (
                    <td>
                      {
                        row.column ||
                        "—"
                      }
                    </td>
                  )}

                  <td>
                    {
                      row.index ??
                      row.__index ??
                      "—"
                    }
                  </td>

                  <td>
                    {
                      row.identifier ??
                      row.id ??
                      "—"
                    }
                  </td>

                  <td>
                    {formatMissingValue(
                      row
                    )}
                  </td>

                </tr>

              )
            )}

          </tbody>

        </table>

      </div>
    </>
  );
}


function formatMissingValue(
  record
) {
  if (
    record?.missing_value !==
      undefined &&
    record?.missing_value !==
      null
  ) {
    return String(
      record.missing_value
    );
  }

  if (
    record?.value !==
      undefined &&
    record?.value !==
      null
  ) {
    return String(
      record.value
    );
  }

  if (
    record?.original_value !==
      undefined &&
    record?.original_value !==
      null
  ) {
    return String(
      record.original_value
    );
  }

  return "Missing";
}


function InspectionDuplicate({
  groups,
}) {
  return (
    <>
      <p>
        {groups.length} repeated
        value group(s) found.
      </p>

      <div className="data-table-wrap modal-table">

        <table className="data-table">

          <thead>

            <tr>

              <th>
                Value
              </th>

              <th>
                Index
              </th>

              <th>
                Identifier
              </th>

            </tr>

          </thead>


          <tbody>

            {groups.map(
              (
                group,
                index
              ) => {

                const indices =
                  group?.indices ||
                  group?.index ||
                  group?.records ||
                  [];

                const value =
                  group?.value ??
                  group?.duplicate_value ??
                  "—";

                const identifier =
                  group?.identifier ??
                  group?.id ??
                  "—";

                return (
                  <tr
                    key={
                      index
                    }
                  >

                    <td>
                      {String(
                        value
                      )}
                    </td>

                    <td>
                      {Array.isArray(
                        indices
                      )
                        ? indices.join(
                            ", "
                          )
                        : String(
                            indices
                          )}
                    </td>

                    <td>
                      {String(
                        identifier
                      )}
                    </td>

                  </tr>
                );
              }
            )}

          </tbody>

        </table>

      </div>
    </>
  );
}


function InspectionExactDuplicate({
  rows,
}) {
  return (
    <>
      <p>
        {rows.length} exact
        duplicate record group(s)
        found.
      </p>

      <div className="data-table-wrap modal-table">

        <table className="data-table">

          <thead>

            <tr>

              <th>
                Index
              </th>

              <th>
                Record
              </th>

            </tr>

          </thead>


          <tbody>

            {rows.map(
              (
                row,
                index
              ) => (

                <tr
                  key={
                    index
                  }
                >

                  <td>
                    {
                      row?.index ??
                      row?.indices ??
                      index
                    }
                  </td>

                  <td>
                    {formatDetailValue(
                      row
                    )}
                  </td>

                </tr>

              )
            )}

          </tbody>

        </table>

      </div>
    </>
  );
}


/* =========================================================
   STATUS
========================================================= */

function StatusCard({
  text,
  detail,
}) {
  return (
    <div className="status-card">

      <div className="loader" />

      <div>

        <strong>
          {text}
        </strong>

        <p>
          {detail}
        </p>

      </div>

    </div>
  );
}


/* =========================================================
   CONFIRMATION MODAL
========================================================= */

function ConfirmationModal({
  count,
  onProceed,
  onEdit,
}) {
  return (
    <div className="modal-backdrop">

      <div className="modal-card">

        <button
          type="button"
          className="modal-close"
          onClick={
            onEdit
          }
        >
          ×
        </button>


        <p className="eyebrow">
          SELECTION CONFIRMED
        </p>


        <h3>
          {count} column
          {count === 1
            ? ""
            : "s"}{" "}
          selected
        </h3>


        <p>
          Your current column selection
          is ready for preprocessing.
        </p>


        <div className="modal-actions">

          <button
            type="button"
            className="secondary-button"
            onClick={
              onEdit
            }
          >
            Edit Column Selection
          </button>


          <button
            type="button"
            className="primary-button"
            onClick={
              onProceed
            }
          >
            Proceed to Preprocessing →
          </button>

        </div>

      </div>

    </div>
  );
}


/* =========================================================
   TEMPORAL NORMALIZATION
========================================================= */

function normalizeTemporal(
  value
) {
  const text =
    String(
      value || ""
    ).toLowerCase();

  if (
    text.includes(
      "non"
    ) &&
    text.includes(
      "temporal"
    )
  ) {
    return "non-temporal";
  }

  if (
    text.includes(
      "temporal"
    ) ||
    text.includes(
      "time"
    )
  ) {
    return "temporal";
  }

  return text.trim();
}
/*=========================================================
   EXPORT
========================================================= */

export default App;
