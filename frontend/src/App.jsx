import { useEffect, useState } from "react";

import {
  confirmSelection,
  getColumnDetails,
  getPreview,
  getPreprocessingInspection,
  saveSelection,
  preprocessDataset,
  runStatisticalAnalysis,
  uploadDataset,
  validateDetectionObjective,
  recommendModels,
} from "./services/api";

import "./App.css";


/* =========================================================
   CONSTANTS
========================================================= */

const PHASES = [
  ["01", "Dataset Analysis"],
  ["02", "Column Selection"],
  ["03", "Preprocessing & Analysis"],
  ["04", "Detection Configuration"],
  ["05", "Model Recommendation"],
  ["06", "Training"],
  ["07", "Visualization"],
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
   MAIN APP
========================================================= */

function App() {
  const [summary, setSummary] = useState(null);
  const [file, setFile] = useState(null);

  const [activePhase, setActivePhase] =
    useState(1);

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
    useState({
      overview: true,
    });


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

  function resetPhase4And5() {
    setAnomalyType("");
    setDetectionScope("");
    setTemporalBehavior("");
    setDetectionObjective("");

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

    resetPhase4And5();
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
      await saveSelection(
        datasetId,
        selectedColumns
      );

      await confirmSelection(
        datasetId
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
      return;
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

      resetPhase4And5();

      setOpenSections({
        overview: true,
      });

      setActivePhase(3);
    } catch (err) {
      /*
       * Actual preprocessing backend failure.
       */
      setError(
        err?.message ||
          "Unable to preprocess dataset."
      );
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

      return;
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
    } catch (err) {
      setError(
        err?.message ||
          "Unable to calculate statistical analysis."
      );
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
      !anomalyType ||
      !detectionScope ||
      !temporalBehavior ||
      !detectionObjective.trim()
    ) {
      setError(
        "Complete all detection configuration fields before validation."
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
       * The actual semantic understanding is performed
       * by the backend.
       *
       * selectedColumns are included in the local
       * interpretation context, while the existing
       * backend endpoint receives the objective.
       */
      const result =
        await validateDetectionObjective(
          datasetId,
          {
            selected_columns:
              selectedColumns,

            anomaly_type:
              anomalyType,

            scope:
              detectionScope,

            temporal_behavior:
              temporalBehavior,

            objective:
              detectionObjective.trim(),
          }
        );

      /*
       * Preserve the complete backend response.
       */
      const validation =
        result || {};

      /*
       * The backend may use different names
       * depending on the schema version.
       */
      const detectedType =
        validation?.detected_type ||
        validation?.anomaly_type ||
        validation?.inferred_anomaly_type ||
        validation?.anomalyType ||
        null;

      const detectedScope =
        validation?.detected_scope ||
        validation?.scope ||
        validation?.comparison_scope ||
        null;

      const detectedTemporal =
        validation?.detected_temporal_behavior ||
        validation?.temporal_behavior ||
        validation?.temporal ||
        null;

      const backendExplicitValidity =
        validation?.valid ??
        validation?.matched ??
        validation?.is_valid ??
        validation?.compatible;

      /*
       * Type matching.
       */
      const typeMatches =
        !detectedType ||
        String(detectedType)
          .trim()
          .toLowerCase() ===
          String(anomalyType)
            .trim()
            .toLowerCase();

      /*
       * Scope matching.
       *
       * If the backend does not provide a scope,
       * we do not falsely reject the objective.
       */
      const scopeMatches =
        !detectedScope ||
        String(detectedScope)
          .trim()
          .toLowerCase() ===
          String(detectionScope)
            .trim()
            .toLowerCase();

      /*
       * Temporal matching.
       *
       * Again, absence of backend field does not
       * create a false negative.
       */
      const temporalMatches =
        !detectedTemporal ||
        normalizeTemporal(
          detectedTemporal
        ) ===
          normalizeTemporal(
            temporalBehavior
          );

      let valid;

      if (
        typeof backendExplicitValidity ===
        "boolean"
      ) {
        valid =
          backendExplicitValidity &&
          typeMatches &&
          scopeMatches &&
          temporalMatches;
      } else {
        /*
         * If the current backend response does not
         * expose an explicit validity flag, successful
         * objective analysis plus matching information
         * is enough to continue.
         */
        valid =
          typeMatches &&
          scopeMatches &&
          temporalMatches;
      }

      const enrichedValidation = {
        ...validation,

        selected_anomaly_type:
          anomalyType,

        selected_scope:
          detectionScope,

        selected_temporal_behavior:
          temporalBehavior,

        detected_type:
          detectedType,

        detected_scope:
          detectedScope,

        detected_temporal_behavior:
          detectedTemporal,

        matched_columns:
          validation?.matched_columns ||
          validation?.referenced_columns ||
          validation?.columns ||
          [],

        valid:
          Boolean(valid),
      };

      setObjectiveValidation(
        enrichedValidation
      );

      setPhase4Complete(
        Boolean(valid)
      );

      if (!valid) {
        setError(
          "The objective does not match the selected detection configuration. Please review the highlighted interpretation."
        );
      }
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


/* =========================================================
   PHASE 5
   RECOMMEND MODELS
========================================================= */

  async function handleRecommendModels() {
    if (
      !datasetId ||
      !analysis ||
      !phase4Complete
    ) {
      return;
    }

    setRecommendationLoading(true);
    setError("");

    try {
      /*
       * Phase 5 backend expects the statistical profile,
       * interpretation and column profiles.
       */
      const result =
        await recommendModels(
          datasetId,
          {
            statistical_profile:
              analysis,

            interpretation:
              objectiveValidation || {
                anomaly_type:
                  anomalyType,

                scope:
                  detectionScope,

                temporal_behavior:
                  temporalBehavior,

                objective:
                  detectionObjective,
              },

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
      openPhase3();
      return;
    }

    if (
      phase === 4 &&
      analysis
    ) {
      setActivePhase(4);
      return;
    }

    if (
      phase === 5 &&
      phase4Complete &&
      recommendations
    ) {
      setActivePhase(5);
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
            activePhase === 3 && (
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
                onContinueToPhase4={() =>
                  setActivePhase(4)
                }
              />
            )}


          {/* ==================================================
              PHASE 4
          ================================================== */}

          {summary &&
            activePhase === 4 && (
              <Phase4
                selectedColumns={
                  selectedColumns
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
                onAnomalyTypeChange={(
                  value
                ) => {
                  setAnomalyType(
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
                onScopeChange={(
                  value
                ) => {
                  setDetectionScope(
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
                onTemporalBehaviorChange={(
                  value
                ) => {
                  setTemporalBehavior(
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
            activePhase === 5 && (
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
  disabled,
  currentFile,
}) {
  const [inputKey, setInputKey] =
    useState(0);

  function handleChange(event) {
    const nextFile =
      event.target.files?.[0];

    if (!nextFile) {
      return;
    }

    onFileSelected(nextFile);

    /*
     * Allows the same file to be selected again
     * after an error.
     */
    setInputKey(
      (current) => current + 1
    );
  }

  return (
    <section className="upload-panel">

      <div className="upload-copy">

        <div className="upload-icon">
          ↑
        </div>

        <div>
          <p className="eyebrow">
            DATASET INPUT
          </p>

          <h2>
            Upload your dataset
          </h2>

          <p>
            Upload a CSV, TSV, JSON or Excel
            dataset. The backend will analyze
            the dataset automatically.
          </p>
        </div>

      </div>

      <label
        className={
          "upload-control" +
          (disabled
            ? " disabled"
            : "")
        }
      >

        <input
          key={inputKey}
          type="file"
          accept=".csv,.tsv,.json,.xlsx,.xls"
          disabled={disabled}
          onChange={
            handleChange
          }
        />

        <span className="upload-button">
          {disabled
            ? "Processing..."
            : "Choose Dataset"}
        </span>

      </label>

      {currentFile && (
        <div className="upload-selected-file">

          <div>
            <span>
              Selected dataset
            </span>

            <strong>
              {currentFile.name}
            </strong>
          </div>

          <span className="ready-badge">
            Ready
          </span>

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
  onNavigate,
}) {
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

        {PHASES.map(
          ([number, label], index) => {
            const phase =
              index + 1;

            const locked =
              !summary ||
              (phase === 3 &&
                !confirmed) ||
              (phase === 4 &&
                !analysis) ||
              (phase === 5 &&
                !phase4Complete) ||
              phase >= 6;

            const isActive =
              activePhase === phase;

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
    <section className="workflow-section">

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
  onRunAnalysis,
  onToggleAnalysis,
  onContinueToPhase4,
}) {
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


      <div className="info-panel">

        <strong>
          Preprocessing Scope
        </strong>

        <span>
          Only missing values and exact
          duplicate records are handled.
          Extreme values are retained for
          anomaly detection.
        </span>

      </div>


      <div className="scope-rule-box">

        <p>

          <strong>
            Duplicate rule:
          </strong>{" "}

          A record is removed only when
          every selected column has exactly
          the same value as another record.

        </p>

      </div>


      <div className="panel">

        <div className="panel-header">

          <div>

            <h3>
              Preprocessing Inspection
            </h3>

            <p>
              Review detected missing
              values and duplicate information
              before preprocessing.
            </p>

          </div>

        </div>


        <PreprocessingTable
          stats={before}
          onInspect={onInspect}
        />


        <div className="phase-actions">

          <button
            type="button"
            className="secondary-button"
            onClick={
              onEditColumns
            }
          >
            ← Edit Columns
          </button>


          <button
            type="button"
            className="primary-button"
            disabled={
              phase3Loading ||
              !selectedColumns.length
            }
            onClick={
              onPreprocess
            }
          >
            {phase3Loading
              ? "Processing..."
              : "Preprocess Dataset"}
          </button>

        </div>

      </div>


      {/* ======================================================
          PREPROCESSED DATASET
      ====================================================== */}

      {preprocessResult && (
        <div className="panel">

          <div className="panel-header">

            <div>

              <h3>
                Preprocessed Dataset Preview
              </h3>

              <p>
                Only selected columns are
                carried forward.
              </p>

            </div>

            <span className="status-badge">
              Preprocessing complete
            </span>

          </div>


          {preview ? (
            <DatasetPreview
              preview={
                preview
              }
              page={
                previewPage
              }
              onPage={
                onPage
              }
              loading={
                phase3Loading
              }
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


      {/* ======================================================
          STATISTICAL ANALYSIS
      ====================================================== */}

      {preprocessResult && (
        <div className="panel">

          <div className="phase3-analysis-header">

            <div>

              <p className="eyebrow">
                3.2 STATISTICAL & DATASET CHARACTERISTIC ANALYSIS
              </p>

              <h3>
                Dataset Characteristics
              </h3>

              <p className="section-subtitle">
                Calculate the characteristics
                used later for dynamic anomaly
                detection and model recommendation.
              </p>

            </div>

          </div>


          <div className="phase-actions">

            <button
              type="button"
              className="primary-button"
              disabled={
                analysisLoading
              }
              onClick={
                onRunAnalysis
              }
            >
              {analysisLoading
                ? "Calculating..."
                : "Run Statistical Analysis"}
            </button>

          </div>


          {analysis && (
            <StatisticalAnalysis
              result={
                analysis
              }
              openSections={
                openSections
              }
              onToggle={
                onToggleAnalysis
              }
            />
          )}


          {analysis && (
            <div className="next-step">

              <div>

                <p className="eyebrow">
                  NEXT PHASE
                </p>

                <h3>
                  Detection Configuration
                </h3>

                <p>
                  Configure anomaly type,
                  comparison scope, temporal
                  behavior and the detection
                  objective.
                </p>

              </div>


              <button
                type="button"
                className="primary-button"
                onClick={
                  onContinueToPhase4
                }
              >
                Continue to Detection Configuration →
              </button>

            </div>
          )}

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

function Phase4({
  selectedColumns,
  anomalyType,
  detectionScope,
  temporalBehavior,
  detectionObjective,
  objectiveValidation,
  objectiveLoading,
  phase4Complete,
  recommendationLoading,
  onAnomalyTypeChange,
  onScopeChange,
  onTemporalBehaviorChange,
  onObjectiveChange,
  onValidateObjective,
  onRecommendModels,
}) {
  const detectedType =
    objectiveValidation?.detected_type ||
    objectiveValidation?.anomaly_type ||
    objectiveValidation?.inferred_anomaly_type;

  const detectedScope =
    objectiveValidation?.detected_scope ||
    objectiveValidation?.scope;

  const detectedTemporal =
    objectiveValidation?.detected_temporal_behavior ||
    objectiveValidation?.temporal_behavior;

  const matchedColumns =
    objectiveValidation?.matched_columns ||
    objectiveValidation?.referenced_columns ||
    objectiveValidation?.columns ||
    [];

  const reasoning =
    objectiveValidation?.reasoning ||
    objectiveValidation?.reason ||
    objectiveValidation?.explanation ||
    objectiveValidation?.objective_explanation;

  const validationValid =
    objectiveValidation?.valid ??
    false;


  return (
    <section className="workflow-section">

      <SectionHeading
        phase="PHASE 04"
        title="Detection Configuration"
        subtitle="Define the anomaly behavior and describe the detection objective. The backend performs semantic objective understanding using the current dataset."
        badge={
          phase4Complete
            ? "Configuration validated"
            : "Configuration required"
        }
      />


      {/* ======================================================
          ANALYZE BY
      ====================================================== */}

      <div className="panel">

        <div className="panel-header">

          <div>

            <h3>
              Analyze By
            </h3>

            <p>
              These are the columns confirmed
              in Phase 2. Phase 4 does not create
              a second column selection.
            </p>

          </div>

          <span className="count-pill">
            {selectedColumns.length} columns
          </span>

        </div>


        <div className="selected-list">

          {selectedColumns.map(
            (column, index) => (
              <div
                className="selected-item"
                key={
                  column
                }
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
          )}

        </div>

      </div>


      {/* ======================================================
          CONFIGURATION
      ====================================================== */}

      <div className="config-grid">

        <ConfigGroup
          title="Anomaly Type"
          description="Primary anomaly behavior."
          value={
            anomalyType
          }
          options={
            ANOMALY_TYPES
          }
          onChange={
            onAnomalyTypeChange
          }
        />


        <ConfigGroup
          title="Comparison Scope"
          description="Whether behavior is evaluated globally or within a local/entity context."
          value={
            detectionScope
          }
          options={
            DETECTION_SCOPES
          }
          onChange={
            onScopeChange
          }
        />


        <ConfigGroup
          title="Temporal Behavior"
          description="Whether the detection objective depends on time or temporal patterns."
          value={
            temporalBehavior
          }
          options={
            TEMPORAL_BEHAVIORS
          }
          onChange={
            onTemporalBehaviorChange
          }
        />

      </div>


      {/* ======================================================
          OBJECTIVE
      ====================================================== */}

      <div className="panel">

        <div className="panel-header">

          <div>

            <h3>
              Detection Objective
            </h3>

            <p>
              Describe what you want the system
              to detect in natural language.
              The backend interprets the objective
              dynamically.
            </p>

          </div>

        </div>


        <textarea
          className="objective-textarea"
          rows={6}
          value={
            detectionObjective
          }
          onChange={(
            event
          ) =>
            onObjectiveChange(
              event.target.value
            )
          }
          placeholder="Example: Find unusual transaction amounts for individual customers compared with their normal transaction behavior."
        />


        <div className="phase-actions">

          <button
            type="button"
            className="primary-button"
            disabled={
              objectiveLoading ||
              !anomalyType ||
              !detectionScope ||
              !temporalBehavior ||
              !detectionObjective.trim()
            }
            onClick={
              onValidateObjective
            }
          >
            {objectiveLoading
              ? "Understanding Objective..."
              : "Validate Objective"}
          </button>

        </div>

      </div>


      {/* ======================================================
          VALIDATION RESULT
      ====================================================== */}

      {objectiveValidation && (
        <div
          className={
            "validation-card " +
            (validationValid
              ? "valid"
              : "invalid")
          }
        >

          <div className="validation-heading">

            <strong>
              {validationValid
                ? "✓ Objective is compatible with the configuration"
                : "⚠ Objective needs revision"}
            </strong>

          </div>


          <div className="validation-grid">

            <ValidationItem
              label="Selected Type"
              value={
                anomalyType
              }
            />

            <ValidationItem
              label="Detected Type"
              value={
                detectedType
              }
            />

            <ValidationItem
              label="Selected Scope"
              value={
                detectionScope
              }
            />

            <ValidationItem
              label="Detected Scope"
              value={
                detectedScope
              }
            />

            <ValidationItem
              label="Selected Temporal Behavior"
              value={
                temporalBehavior
              }
            />

            <ValidationItem
              label="Detected Temporal Behavior"
              value={
                detectedTemporal
              }
            />

          </div>


          {matchedColumns.length >
            0 && (
            <div className="validation-detail">

              <span>
                Referenced Columns
              </span>

              <div className="chip-list">

                {matchedColumns.map(
                  (column) => (
                    <span
                      className="detail-chip"
                      key={
                        column
                      }
                    >
                      {column}
                    </span>
                  )
                )}

              </div>

            </div>
          )}


          {reasoning && (
            <div className="validation-detail">

              <span>
                Backend Interpretation
              </span>

              <p>
                {reasoning}
              </p>

            </div>
          )}

        </div>
      )}


      {/* ======================================================
          NEXT PHASE
      ====================================================== */}

      <div className="next-step">

        <div>

          <p className="eyebrow">
            NEXT PHASE
          </p>

          <h3>
            Model Recommendation
          </h3>

          <p>
            Generate model recommendations
            using the backend statistical profile,
            selected columns and validated
            detection intent.
          </p>

        </div>


        <button
          type="button"
          className="primary-button"
          disabled={
            !phase4Complete ||
            recommendationLoading
          }
          onClick={
            onRecommendModels
          }
        >
          {recommendationLoading
            ? "Recommending..."
            : "Recommend Models →"}
        </button>

      </div>

    </section>
  );
}


/* =========================================================
   CONFIG GROUP
========================================================= */

function ConfigGroup({
  title,
  description,
  value,
  options,
  onChange,
}) {
  return (
    <div className="panel config-group">

      <div>

        <h3>
          {title}
        </h3>

        <p>
          {description}
        </p>

      </div>


      <div className="option-list">

        {options.map(
          (option) => (
            <label
              className={
                "config-option" +
                (value ===
                option
                  ? " selected"
                  : "")
              }
              key={
                option
              }
            >

              <input
                type="radio"
                name={
                  title
                }
                value={
                  option
                }
                checked={
                  value ===
                  option
                }
                onChange={() =>
                  onChange(
                    option
                  )
                }
              />

              <span>
                {option}
              </span>

            </label>
          )
        )}

      </div>

    </div>
  );
}


/* =========================================================
   VALIDATION ITEM
========================================================= */

function ValidationItem({
  label,
  value,
}) {
  return (
    <div className="validation-item">

      <span>
        {label}
      </span>

      <strong>
        {value ||
          "Not provided"}
      </strong>

    </div>
  );
}


/* =========================================================
   PHASE 5
========================================================= */

function Phase5({
  recommendations,
  recommendationLoading,
  anomalyType,
  detectionScope,
  temporalBehavior,
  detectionObjective,
  selectedColumns,
}) {
  const rawModels =
    recommendations?.recommendations ||
    recommendations?.recommended_models ||
    recommendations?.models ||
    [];

  const models =
    Array.isArray(
      rawModels
    )
      ? rawModels.slice(
          0,
          3
        )
      : [];


  return (
    <section className="workflow-section">

      <SectionHeading
        phase="PHASE 05"
        title="Model Recommendation"
        subtitle="Top model recommendations generated from the backend dataset characteristics and validated detection configuration."
        badge={
          models.length
            ? `${models.length} recommendations`
            : "Recommendation"
        }
      />


      <div className="panel">

        <div className="panel-header">

          <div>

            <h3>
              Validated Detection Configuration
            </h3>

            <p>
              This configuration is passed to
              the recommendation pipeline.
            </p>

          </div>

        </div>


        <div className="validation-grid">

          <ValidationItem
            label="Anomaly Type"
            value={
              anomalyType
            }
          />

          <ValidationItem
            label="Scope"
            value={
              detectionScope
            }
          />

          <ValidationItem
            label="Temporal Behavior"
            value={
              temporalBehavior
            }
          />

        </div>


        <div className="validation-detail">

          <span>
            Analyze By
          </span>

          <div className="chip-list">

            {selectedColumns.map(
              (column) => (
                <span
                  className="detail-chip"
                  key={
                    column
                  }
                >
                  {column}
                </span>
              )
            )}

          </div>

        </div>


        <div className="validation-detail">

          <span>
            Detection Objective
          </span>

          <p>
            {
              detectionObjective ||
              "—"
            }
          </p>

        </div>

      </div>


      {recommendationLoading && (
        <StatusCard
          text="Generating recommendations"
          detail="The backend is scoring suitable anomaly detection models..."
        />
      )}


      {!recommendationLoading &&
        !models.length && (
          <div className="empty-state">
            No model recommendations were returned.
          </div>
        )}


      <div className="recommendation-list">

        {models.map(
          (
            model,
            index
          ) => (
            <ModelRecommendationCard
              key={
                model?.model ||
                model?.name ||
                index
              }
              model={
                model
              }
              rank={
                index + 1
              }
            />
          )
        )}

      </div>

    </section>
  );
}


/* =========================================================
   MODEL RECOMMENDATION CARD
========================================================= */

function ModelRecommendationCard({
  model,
  rank,
}) {
  const name =
    model?.model ||
    model?.name ||
    model?.detector ||
    "Unknown Model";

  const score =
    model?.score ??
    model?.suitability_score ??
    model?.total_score ??
    model?.final_score;

  const explanation =
    model?.why_selected ||
    model?.recommendation_reason ||
    model?.reason ||
    model?.explanation ||
    model?.reasoning;

  const datasetSuitability =
    model?.dataset_suitability ||
    model?.dataset_fit ||
    model?.statistical_details;

  const detectionSuitability =
    model?.detection_suitability ||
    model?.anomaly_type_suitability ||
    model?.detection_fit;

  const objectiveCompatibility =
    model?.objective_compatibility ||
    model?.objective_fit ||
    model?.objective_details;


  return (
    <div className="panel recommendation-card">

      <div className="recommendation-rank">
        #{rank}
      </div>


      <div className="recommendation-main">

        <div className="recommendation-title-row">

          <h3>
            {name}
          </h3>

          <div className="recommendation-score">

            <span>
              Score
            </span>

            <strong>
              {score !==
                undefined &&
              score !==
                null
                ? Number.isFinite(
                    Number(
                      score
                    )
                  )
                  ? Number(
                      score
                    ).toFixed(
                      2
                    )
                  : String(
                      score
                    )
                : "—"}
            </strong>

          </div>

        </div>


        {explanation && (
          <div className="recommendation-reason">

            <span>
              Why this model was selected
            </span>

            <p>
              {formatDetailValue(
                explanation
              )}
            </p>

          </div>
        )}


        <div className="recommendation-evidence">

          <EvidenceItem
            label="Dataset Suitability"
            value={
              datasetSuitability
            }
          />

          <EvidenceItem
            label="Detection Suitability"
            value={
              detectionSuitability
            }
          />

          <EvidenceItem
            label="Objective Compatibility"
            value={
              objectiveCompatibility
            }
          />

        </div>

      </div>

    </div>
  );
}


function EvidenceItem({
  label,
  value,
}) {
  return (
    <div className="evidence-item">

      <span>
        {label}
      </span>

      <p>
        {formatDetailValue(
          value ||
            "Not provided"
        )}
      </p>

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
