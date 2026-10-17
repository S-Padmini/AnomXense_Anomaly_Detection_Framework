import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getPhase6Config,
  detectPhase6Anomalies,
  getPhase6Result,
} from "../services/phase6Api";

import DetectionSetup, {
  TrainingProgress,
} from "../components/Phase6/DetectionSetup";

import DetectionResults from "../components/Phase6/DetectionResults";

import "../styles/Phase6.css";

/* =========================================================
   MODEL DISPLAY NAMES
========================================================= */

const MODEL_DISPLAY_NAMES = {
  ECOD:
    "Empirical Cumulative Distribution-based Outlier Detection",

  IForest:
    "Isolation Forest",

  IsolationForest:
    "Isolation Forest",

  "Isolation Forest":
    "Isolation Forest",

  COPOD:
    "Copula-Based Outlier Detection",

  KNN:
    "K-Nearest Neighbors",

  LOF:
    "Local Outlier Factor",

  CBLOF:
    "Cluster-Based Local Outlier Factor",

  HBOS:
    "Histogram-Based Outlier Score",

  MatrixProfile:
    "Matrix Profile",

  SpectralResidual:
    "Spectral Residual",

  KShape:
    "K-Shape",

  CombinedScore:
    "Combined Score",

  combined_score:
    "Combined Score",

  "Combined Score":
    "Combined Score",
};

/* =========================================================
   HELPERS
========================================================= */

function unwrapResult(response) {
  return (
    response?.result ||
    response ||
    null
  );
}

function normalizeText(value) {
  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  return String(value).trim();
}

function displayModelName(value) {
  if (!value) {
    return "";
  }

  const raw =
    typeof value === "object"
      ? value?.display_name ||
        value?.model ||
        value?.name ||
        value?.model_name ||
        value?.actual_trained_model ||
        value?.selected_model ||
        ""
      : value;

  const text = normalizeText(raw);

  return (
    MODEL_DISPLAY_NAMES[text] ||
    text
  );
}

function normalizeAnomalyType(value) {
  const text = normalizeText(value)
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");

  if (text.includes("point")) return "point";
  if (text.includes("contextual")) return "contextual";
  if (text.includes("collective")) return "collective";

  return "";
}

function getConfigAnomalyType(config) {
  const objective =
    config?.objective_understanding ||
    config?.objective ||
    config?.phase4_objective ||
    {};

  return normalizeAnomalyType(
    objective?.anomaly_type ||
      objective?.type ||
      objective?.anomalyType ||
      config?.anomaly_type ||
      ""
  );
}

function getObjective(validation) {
  const understanding =
    validation?.objective_understanding ||
    validation?.objective ||
    validation ||
    {};

  return (
    understanding?.interpreted_objective ||
    understanding?.objective_understanding ||
    understanding?.explanation ||
    validation?.interpreted_objective ||
    ""
  );
}

function modelListText(models) {
  if (!Array.isArray(models)) {
    return "";
  }

  return models
    .map((model) =>
      displayModelName(model)
    )
    .filter(Boolean)
    .join(" · ");
}

/* =========================================================
   MAIN PHASE 6
========================================================= */

export default function Phase6({
  datasetId,
  selectedColumns = [],
  recommendations = null,
  objectiveValidation = null,
  summary = null,
}) {
  /* =======================================================
     CONFIG
  ======================================================= */

  const [config, setConfig] =
    useState(null);

  const [
    configLoading,
    setConfigLoading,
  ] = useState(true);

  const [
    configError,
    setConfigError,
  ] = useState("");

  const [
    trainingApproach,
    setTrainingApproach,
  ] = useState("best_score");

  /* =======================================================
     DETECTION
  ======================================================= */

  const [
    detecting,
    setDetecting,
  ] = useState(false);

  const [
    detectionResult,
    setDetectionResult,
  ] = useState(null);

  const [
    detectionError,
    setDetectionError,
  ] = useState("");

  const [
    trainingStep,
    setTrainingStep,
  ] = useState(0);

  /* =======================================================
     RESET WHEN DATASET CHANGES
  ======================================================= */

  useEffect(() => {
    setConfig(null);
    setDetectionResult(null);
    setConfigError("");
    setDetectionError("");
    setDetectionResult(null);
    setTrainingStep(0);
    setTrainingApproach("best_score");
  }, [datasetId]);

  /* =======================================================
     LOAD PHASE 6 CONFIGURATION
  ======================================================= */

  useEffect(() => {
    let cancelled = false;

    async function loadConfig() {
      if (!datasetId) {
        setConfigLoading(false);
        return;
      }

      setConfigLoading(true);
      setConfigError("");

      try {
        const response =
          await getPhase6Config(
            datasetId
          );

        if (!cancelled) {
          setConfig(response || {});
        }
      } catch (error) {
        if (!cancelled) {
          setConfigError(
            error?.message ||
              "Unable to load Phase 6 configuration."
          );
        }
      } finally {
        if (!cancelled) {
          setConfigLoading(false);
        }
      }
    }

    loadConfig();

    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  /* =======================================================
     LOAD PREVIOUS DETECTION
  ======================================================= */

  useEffect(() => {
    let cancelled = false;

    async function loadExistingResult() {
      if (!datasetId) {
        return;
      }

      try {
        const response =
          await getPhase6Result(
            datasetId
          );

        const result =
          unwrapResult(response);

        if (
          !cancelled &&
          result
        ) {
          setDetectionResult(result);

          if (
            result?.approach ===
            "combined_score"
          ) {
            setTrainingApproach(
              "combined_score"
            );
          } else {
            setTrainingApproach(
              "best_score"
            );
          }
        }
      } catch {
        /*
         * No previous Phase 6 result is
         * expected before the first
         * detection run.
         */
      }
    }

    loadExistingResult();

    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  /* =======================================================
     AVAILABLE PHASE 5 RECOMMENDATIONS
  ======================================================= */

  const models = useMemo(() => {
    const fromConfig =
      config?.recommendations;

    const fromProps =
      recommendations?.recommendations;

    const directProps =
      Array.isArray(recommendations)
        ? recommendations
        : null;

    const source =
      Array.isArray(fromConfig)
        ? fromConfig
        : Array.isArray(fromProps)
        ? fromProps
        : Array.isArray(directProps)
        ? directProps
        : [];

    /*
     * Phase 6 supports:
     *
     * Best Score:
     *   first Phase 5 recommendation
     *
     * Combined Score:
     *   top 3 Phase 5 recommendations
     */
    return source.slice(0, 3);
  }, [
    config,
    recommendations,
  ]);

  /* =======================================================
     TRAINING PROGRESS
  ======================================================= */

  useEffect(() => {
    if (!detecting) {
      return undefined;
    }

    /*
     * These are visual progress stages only.
     * They do NOT fabricate backend results.
     */

    const interval =
      window.setInterval(() => {
        setTrainingStep(
          (current) =>
            Math.min(
              current + 1,
              7
            )
        );
      }, 650);

    return () => {
      window.clearInterval(interval);
    };
  }, [detecting]);

  /* =======================================================
     TRAIN / DETECT
  ======================================================= */

  async function handleTrain(payload) {
    if (detecting) {
      return;
    }

    if (!datasetId) {
      setDetectionError(
        "Dataset ID is missing."
      );
      return;
    }

    if (
      !Array.isArray(
        payload?.target_columns
      ) ||
      payload.target_columns.length === 0
    ) {
      setDetectionError(
        "Please select at least one Target / Detection Column."
      );
      return;
    }

    const approach =
      payload?.approach ===
      "combined_score"
        ? "combined_score"
        : "best_score";

    const contaminationMode =
      payload?.contamination_mode === "custom"
        ? "custom"
        : payload?.contamination_mode === "default"
        ? "default"
        : "";

    if (!contaminationMode) {
      setDetectionError(
        "Please select a contamination method to continue."
      );
      return;
    }

    const contamination = Number(
      payload?.contamination
    );

    if (
      !Number.isFinite(contamination) ||
      contamination < 0.01 ||
      contamination > 0.50
    ) {
      setDetectionError(
        "Contamination must be between 0.01 (1%) and 0.50 (50%)."
      );
      return;
    }

    const effectiveContamination =
      contaminationMode === "default"
        ? 0.10
        : contamination;

    const targetColumns = [
      ...new Set(
        payload.target_columns
          .map(normalizeText)
          .filter(Boolean)
      ),
    ];

    const anomalyType =
      getConfigAnomalyType(config);

    if (
      anomalyType === "point" &&
      targetColumns.length !== 1
    ) {
      setDetectionError(
        "Point Anomaly requires exactly one Target / Detection Column."
      );
      return;
    }

    const explainByColumns =
      Array.isArray(
        payload?.explain_by_columns
      )
        ? [
            ...new Set(
              payload.explain_by_columns
                .map(normalizeText)
                .filter(Boolean)
            ),
          ]
        : [];

    /*
     * IMPORTANT:
     *
     * Phase 6 sends ONLY investigator selections.
     *
     * There is intentionally NO:
     *   - user-defined anomaly rate
     *
     * PyOD determines its native threshold/contamination
     * during backend model training.
     */

    const requestPayload = {
      approach,
      contamination_mode: contaminationMode,
      contamination: effectiveContamination,
      target_columns: targetColumns,
      explain_by_columns:
        explainByColumns,
    };

    setTrainingApproach(approach);
    setDetectionError("");
    setDetectionResult(null);
    setTrainingStep(0);
    setDetecting(true);

    try {
      console.log(
        "PHASE 6 DETECTION REQUEST:",
        {
          datasetId,
          requestPayload,
        }
      );

      const response =
        await detectPhase6Anomalies(
          datasetId,
          requestPayload
        );

      const result =
        unwrapResult(response);

      if (!result) {
        throw new Error(
          "The backend completed the request but returned no detection result."
        );
      }

      console.log(
        "PHASE 6 DETECTION RESULT:",
        result
      );

      setTrainingStep(99);
      setDetectionResult(result);
    } catch (error) {
      console.error(
        "PHASE 6 DETECTION ERROR:",
        error
      );

      /*
       * The backend error is shown directly so
       * model-training problems such as CBLOF
       * configuration failures are visible.
       */
      setDetectionError(
        error?.message ||
          "Unable to train the PyOD model and detect anomalies."
      );
    } finally {
      setDetecting(false);
    }
  }

  /* =======================================================
     BACKEND RESULT SUMMARY
  ======================================================= */

  const completedModels =
    Array.isArray(
      detectionResult?.trained_models
    )
      ? detectionResult.trained_models
      : Array.isArray(
          detectionResult?.models
        )
      ? detectionResult.models
      : [];

  const actualTrainedModelRaw =
    detectionResult?.trained_model ||
    detectionResult?.selected_model ||
    detectionResult?.phase5_recommended_model ||
    "";

  const actualTrainedModel =
    displayModelName(
      actualTrainedModelRaw
    );

  const resultApproach =
    detectionResult?.approach ||
    trainingApproach;

  const isCombined =
    resultApproach ===
    "combined_score";

  const trainedModelsText =
    modelListText(
      detectionResult?.trained_models ||
        detectionResult?.models ||
        completedModels
    );

  const recordsProcessed =
    detectionResult?.records_analyzed ??
    detectionResult?.total_records ??
    detectionResult
      ?.detection_summary
      ?.total_records ??
    "—";

  /* =======================================================
     LOADING
  ======================================================= */

  if (configLoading) {
    return (
      <section className="p6-page p6-enterprise-page">
        <div className="p6-page-header">
          <div>
            <span className="p6-section-kicker">
              PHASE 06
            </span>

            <h2>
              Anomaly Detection
            </h2>

            <p>
              Preparing your detection
              workspace...
            </p>
          </div>
        </div>

        <div className="p6-loading-card large">
          <div className="p6-spinner" />

          <div>
            <strong>
              Loading Phase 6
              configuration
            </strong>

            <span>
              Reading the Phase 2
              selected columns and
              Phase 5 recommendations.
            </span>
          </div>
        </div>
      </section>
    );
  }

  /* =======================================================
     CONFIG ERROR
  ======================================================= */

  if (configError) {
    return (
      <section className="p6-page p6-enterprise-page">
        <div className="p6-page-header">
          <div>
            <span className="p6-section-kicker">
              PHASE 06
            </span>

            <h2>
              Anomaly Detection
            </h2>

            <p>
              Configure → Train →
              Investigate
            </p>
          </div>
        </div>

        <div className="p6-error-card large">
          <strong>
            Phase 6 could not be loaded
          </strong>

          <span>
            {configError}
          </span>
        </div>
      </section>
    );
  }

  /* =======================================================
     RESULTS
  ======================================================= */

  if (detectionResult) {
    return (
      <section className="p6-page p6-enterprise-page">
        <div className="p6-page-header">
          <div>
            <span className="p6-section-kicker">
              PHASE 06
            </span>

            <h2>
              Anomaly Detection
            </h2>

            <p>
              Configure → Train →
              Investigate
            </p>
          </div>

          <div className="p6-header-complete">
            <span>✓</span>
            Detection complete
          </div>
        </div>

        {/* =================================================
            ACTUAL DETECTION RESULT
        ================================================= */}

        <div className="p6-success-card">
          <div className="p6-success-icon">
            ✓
          </div>

          <div className="p6-success-copy">
            <strong>
              {isCombined
                ? "Combined Detection Successfully Completed"
                : actualTrainedModel
                ? `${actualTrainedModel} Successfully Trained`
                : completedModels.length > 1
                ? "Models Successfully Trained"
                : "Detection Successfully Completed"}
            </strong>

            <span>
              This result is based
              entirely on the actual
              backend PyOD training and
              anomaly detection run.
            </span>
          </div>

          <div className="p6-success-details">
            <div>
              <span>
                Detection Approach
              </span>

              <strong>
                {isCombined
                  ? "Combined Score"
                  : "Best Recommended Model"}
              </strong>
            </div>

            <div>
              <span>
                Models Included
              </span>

              <strong>
                {isCombined
                  ? trainedModelsText ||
                    "—"
                  : actualTrainedModel ||
                    trainedModelsText ||
                    "—"}
              </strong>
            </div>

            <div>
              <span>
                Records Processed
              </span>

              <strong>
                {recordsProcessed}
              </strong>
            </div>
          </div>
        </div>

        <DetectionResults
          datasetId={datasetId}
          result={detectionResult}
          objective={getObjective(
            objectiveValidation
          )}
          onBack={() => {
            setDetectionResult(null);
            setDetectionError("");
          }}
        />
      </section>
    );
  }

  /* =======================================================
     CONFIGURATION + TRAINING
  ======================================================= */

  return (
    <section className="p6-page">
      <div className="p6-page-header">
        <div>
          <span className="p6-section-kicker">
            PHASE 06
          </span>

          <h2>
            Anomaly Detection
          </h2>

          <p>
            Configure the detection
            strategy, train the
            recommended PyOD model, and
            investigate the resulting
            observations.
          </p>
        </div>

        <div className="p6-header-status">
          <span className="p6-status-dot" />
          Ready to configure
        </div>
      </div>

      {!detecting &&
        detectionError && (
          <div className="p6-error-card">
            <strong>
              Detection could not be
              completed
            </strong>

            <span>
              {detectionError}
            </span>
          </div>
        )}

      {detecting ? (
        <TrainingProgress
          approach={trainingApproach}
          models={models}
          step={trainingStep}
        />
      ) : (
        <DetectionSetup
          config={config}
          onTrain={handleTrain}
          loading={detecting}
        />
      )}
    </section>
  );
}