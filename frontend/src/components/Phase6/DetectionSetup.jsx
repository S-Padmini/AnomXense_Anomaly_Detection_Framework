import { useEffect, useMemo, useRef, useState } from "react";

/* =========================================================
   MODEL HELPERS
========================================================= */

function normalizeModelName(model) {
  if (!model) return "Unknown model";

  const raw =
    typeof model === "object"
      ? model?.display_name ||
        model?.model ||
        model?.name ||
        model?.model_name ||
        "Unknown model"
      : model;

  return String(raw).trim() || "Unknown model";
}

/* =========================================================
   OBJECTIVE / ANOMALY TYPE
========================================================= */

function normalizeAnomalyType(value) {
  const text = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");

  if (text.includes("point")) return "point";
  if (text.includes("contextual")) return "contextual";
  if (text.includes("collective")) return "collective";

  return "";
}

function getAnomalyType(config) {
  const objective =
    config?.objective_understanding ||
    config?.objective ||
    config?.phase4_objective ||
    {};

  const raw =
    objective?.anomaly_type ||
    objective?.type ||
    objective?.anomalyType ||
    config?.anomaly_type ||
    "";

  return normalizeAnomalyType(raw);
}

/* =========================================================
   MODEL INFO POPUP
========================================================= */

function ApproachInfo({ title, children }) {
  const [open, setOpen] = useState(false);

  function toggle(event) {
    event.stopPropagation();
    setOpen((current) => !current);
  }

  return (
    <span className="p6-info-wrap">
      <span
        className="p6-info-button"
        role="button"
        tabIndex={0}
        aria-label={`Information about ${title}`}
        aria-expanded={open}
        onClick={toggle}
        onMouseDown={(event) => event.stopPropagation()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            toggle(event);
          }
        }}
      >
        i
      </span>

      {open && (
        <span
          className="p6-info-popup"
          role="dialog"
          aria-label={`${title} explanation`}
          onClick={(event) => event.stopPropagation()}
          onMouseDown={(event) => event.stopPropagation()}
        >
          <strong>{title}</strong>

          {children}
        </span>
      )}
    </span>
  );
}

/* =========================================================
   MULTI SELECT
========================================================= */

function MultiSelect({
  label,
  help,
  options,
  value,
  onChange,
  maxSelections = null,
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const dropdownRef = useRef(null);

  /*
   * Close the dropdown whenever the user clicks anywhere
   * outside this particular dropdown.
   */
  useEffect(() => {
    function handleOutsideClick(event) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target)
      ) {
        setOpen(false);
        setSearch("");
      }
    }

    if (open) {
      document.addEventListener(
        "mousedown",
        handleOutsideClick
      );
    }

    return () => {
      document.removeEventListener(
        "mousedown",
        handleOutsideClick
      );
    };
  }, [open]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) return options;

    return options.filter((item) =>
      String(item).toLowerCase().includes(query)
    );
  }, [options, search]);

  function toggle(item) {
    if (value.includes(item)) {
      onChange(value.filter((x) => x !== item));
      return;
    }

    if (
      Number.isInteger(maxSelections) &&
      maxSelections > 0 &&
      value.length >= maxSelections
    ) {
      return;
    }

    onChange([...value, item]);
  }

  function handleTriggerClick(event) {
    event.stopPropagation();

    setOpen((current) => {
      const next = !current;

      if (!next) {
        setSearch("");
      }

      return next;
    });
  }

  return (
    <div
      className="p6-field p6-multiselect-field"
      ref={dropdownRef}
    >
      <div className="p6-field-label">{label}</div>

      {help && (
        <div className="p6-field-help">
          {help}
        </div>
      )}

      <div className="p6-dropdown-container">
        <button
          type="button"
          className={
            "p6-select-trigger" +
            (open ? " p6-select-trigger-open" : "")
          }
          onClick={handleTriggerClick}
          aria-haspopup="listbox"
          aria-expanded={open}
        >
          <span className="p6-chip-area">
            {value.length ? (
              value.map((item) => (
                <span
                  className="p6-chip"
                  key={item}
                >
                  {item}

                  <span
                    className="p6-chip-x"
                    role="button"
                    tabIndex={0}
                    aria-label={`Remove ${item}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      toggle(item);
                    }}
                    onKeyDown={(event) => {
                      if (
                        event.key === "Enter" ||
                        event.key === " "
                      ) {
                        event.preventDefault();
                        event.stopPropagation();
                        toggle(item);
                      }
                    }}
                  >
                    ×
                  </span>
                </span>
              ))
            ) : (
              <span className="p6-placeholder">
                Select columns
              </span>
            )}
          </span>

          <span
            className={
              "p6-chevron" +
              (open ? " p6-chevron-open" : "")
            }
            aria-hidden="true"
          >
            {open ? "⌃" : "⌄"}
          </span>
        </button>

        {open && (
          <div
            className="p6-dropdown"
            role="listbox"
            aria-label={`${label} selection`}
            onClick={(event) =>
              event.stopPropagation()
            }
            onMouseDown={(event) =>
              event.stopPropagation()
            }
          >
            <div className="p6-dropdown-search-wrap">
              <span
                className="p6-dropdown-search-icon"
                aria-hidden="true"
              >
                ⌕
              </span>

              <input
                className="p6-dropdown-search"
                value={search}
                onChange={(event) =>
                  setSearch(event.target.value)
                }
                placeholder="Search columns..."
                autoFocus
              />

              {search && (
                <button
                  type="button"
                  className="p6-dropdown-clear-search"
                  aria-label="Clear column search"
                  onClick={() => setSearch("")}
                >
                  ×
                </button>
              )}
            </div>

            <div className="p6-dropdown-count">
              <span>
                {filtered.length} available
              </span>

              <span>
                {value.length} selected
              </span>
            </div>

            <div className="p6-option-list">
              {filtered.length ? (
                filtered.map((item) => {
                  const checked =
                    value.includes(item);

                  const selectionLimitReached =
                    Number.isInteger(maxSelections) &&
                    maxSelections > 0 &&
                    value.length >= maxSelections &&
                    !checked;

                  return (
                    <button
                      type="button"
                      key={item}
                      className={
                        "p6-option" +
                        (checked
                          ? " selected"
                          : "") +
                        (selectionLimitReached
                          ? " disabled"
                          : "")
                      }
                      onClick={() =>
                        toggle(item)
                      }
                      disabled={selectionLimitReached}
                      role="option"
                      aria-selected={checked}
                      aria-disabled={selectionLimitReached}
                    >
                      <span
                        className={
                          "p6-checkbox" +
                          (checked
                            ? " checked"
                            : "")
                        }
                      >
                        {checked ? "✓" : ""}
                      </span>

                      <span className="p6-option-label">
                        {item}
                      </span>

                      {checked && (
                        <span className="p6-option-selected">
                          Selected
                        </span>
                      )}
                    </button>
                  );
                })
              ) : (
                <div className="p6-dropdown-empty">
                  No matching columns.
                </div>
              )}
            </div>

            {value.length > 0 && (
              <div className="p6-dropdown-footer">
                <span>
                  {value.length} column
                  {value.length === 1
                    ? ""
                    : "s"} selected
                </span>

                <button
                  type="button"
                  onClick={() => {
                    onChange([]);
                    setSearch("");
                  }}
                >
                  Clear selection
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* =========================================================
   TRAINING PROGRESS
========================================================= */

export function TrainingProgress({
  step = 0,
  approach,
  models = [],
}) {
  const steps = [
    "Preparing selected features",
    approach === "combined_score"
      ? "Training recommended models"
      : "Training PyOD model",
    "Calculating anomaly scores",
    "Determining detection threshold",
  ];

  const progress = Math.min(
    100,
    Math.max(
      8,
      step >= 99 ? 100 : step * 25
    )
  );

  return (
    <div className="p6-training-card">
      <div className="p6-training-heading">
        <div>
          <span>MODEL TRAINING</span>

          <strong>
            {step >= 99
              ? "Detection completed"
              : "Training anomaly detector"}
          </strong>
        </div>

        {step < 99 && (
          <div className="p6-spinner" />
        )}
      </div>

      <div className="p6-progress-track">
        <div
          className="p6-progress-fill"
          style={{
            width: `${progress}%`,
          }}
        />
      </div>

      <div className="p6-training-steps">
        {steps.map((label, index) => {
          const number = index + 1;

          const completed =
            step >= number + 1 ||
            step >= 99;

          const active =
            !completed &&
            step === number;

          return (
            <div
              className={
                completed
                  ? "completed"
                  : active
                  ? "active"
                  : ""
              }
              key={label}
            >
              <span>
                {completed ? "✓" : number}
              </span>

              <label>{label}</label>
            </div>
          );
        })}
      </div>

      {approach === "combined_score" &&
        models.length > 0 && (
          <div className="p6-training-models">
            <span>
              Models being evaluated
            </span>

            <div>
              {models.map(
                (model, index) => (
                  <span
                    key={
                      model?.model ||
                      model?.name ||
                      index
                    }
                  >
                    {normalizeModelName(model)}
                  </span>
                )
              )}
            </div>
          </div>
        )}
    </div>
  );
}

/* =========================================================
   DETECTION SETUP
========================================================= */

export default function DetectionSetup({
  config,
  onTrain,
  loading,
}) {
  const [approach, setApproach] =
    useState("best_score");

  /*
   * Contamination is an explicit investigator choice.
   * No option is pre-selected so the user must intentionally
   * choose Default PyOD (10%) or Custom Contamination.
   */
  const [contaminationMode, setContaminationMode] =
    useState("");
  const [customContamination, setCustomContamination] =
    useState(0.10);

  const allColumns = useMemo(
    () =>
      Array.isArray(
        config?.selected_columns
      )
        ? config.selected_columns
        : [],
    [config]
  );

  const anomalyType = useMemo(
    () => getAnomalyType(config),
    [config]
  );

  const isPointAnomaly =
    anomalyType === "point";

  /*
   * IMPORTANT:
   * Target columns intentionally start EMPTY.
   *
   * We do NOT pre-populate them from:
   * - suggested_target_columns
   * - target_columns
   *
   * The user must manually select the target.
   */
  const [targets, setTargets] =
    useState([]);

  /*
   * Explain By can still restore the configuration
   * supplied by Phase 5/previous Phase 6 state.
   *
   * This is separate from Target because the new
   * requirement specifically says Target must remain empty.
   */
  const [explainBy, setExplainBy] =
    useState(
      Array.isArray(
        config?.explain_by_columns
      )
        ? config.explain_by_columns
        : []
    );

  const models = useMemo(
    () =>
      Array.isArray(
        config?.recommendations
      )
        ? config.recommendations.slice(
            0,
            3
          )
        : [],
    [config]
  );

  const selectedModels =
    approach === "best_score"
      ? models.slice(0, 1)
      : models.slice(0, 3);

  function submit() {
    if (!targets.length) return;

    if (
      isPointAnomaly &&
      targets.length !== 1
    ) {
      return;
    }

    if (contaminationMode !== "default" && contaminationMode !== "custom") {
      return;
    }

    onTrain({
      approach,
      contamination_mode: contaminationMode,
      contamination:
        contaminationMode === "default"
          ? 0.10
          : customContamination,
      target_columns: targets,
      explain_by_columns: explainBy,
    });
  }

  return (
    <div className="p6-stack p6-enterprise-setup">
      {/* =====================================================
          APPROACH
      ===================================================== */}

      <section className="p6-panel p6-approach-panel">
        <div className="p6-panel-head">
          <div>
            <div className="p6-eyebrow">
              DETECTION METHOD
            </div>

            <h3>
              How would you like to detect anomalies?
            </h3>

            <p>
              Choose one recommended model or
              combine the top three recommendation
              perspectives from Phase 5.
            </p>
          </div>
        </div>

        <div className="p6-approach-grid">
          {/* =================================================
              BEST SCORE
          ================================================= */}

          <div
            className={
              "p6-approach-card" +
              (approach ===
              "best_score"
                ? " active"
                : "")
            }
          >
            <button
              type="button"
              className="p6-approach-select"
              onClick={() =>
                setApproach("best_score")
              }
              aria-pressed={
                approach ===
                "best_score"
              }
            >
              <span className="p6-approach-icon">
                🏆
              </span>

              <span className="p6-approach-title">
                <span>
                  Best Score
                </span>

                <ApproachInfo title="Best Score">
                  <p>
                    Uses the highest-ranked
                    model from Phase 5
                    recommendations.
                  </p>

                  <p>
                    That single PyOD model is
                    trained on the selected
                    Target Columns, anomaly
                    scores are generated, and
                    the model's native PyOD
                    threshold/contamination
                    handling is used to
                    classify records.
                  </p>
                </ApproachInfo>
              </span>

              <span className="p6-approach-text">
                Train the highest-ranked
                Phase 5 model and use its
                actual anomaly scores.
              </span>

              <span className="p6-approach-action">
                {approach ===
                "best_score"
                  ? "Selected"
                  : "Select Best Score"}
              </span>
            </button>
          </div>

          {/* =================================================
              COMBINED SCORE
          ================================================= */}

          <div
            className={
              "p6-approach-card" +
              (approach ===
              "combined_score"
                ? " active"
                : "")
            }
          >
            <button
              type="button"
              className="p6-approach-select"
              onClick={() =>
                setApproach(
                  "combined_score"
                )
              }
              aria-pressed={
                approach ===
                "combined_score"
              }
            >
              <span className="p6-approach-icon">
                🔗
              </span>

              <span className="p6-approach-title">
                <span>
                  Combined Score
                </span>

                <ApproachInfo title="Combined Score">
                  <p>
                    Uses the top three
                    Phase 5 recommended
                    models.
                  </p>

                  <p>
                    Each model is trained and
                    produces its own anomaly
                    scores. The backend
                    normalizes those scores
                    and combines them using
                    weights derived from the
                    actual Phase 5
                    recommendation scores.
                  </p>

                  <p>
                    The final combined
                    classification is
                    determined from the
                    combined score and the
                    fitted models' native
                    threshold information.
                  </p>
                </ApproachInfo>
              </span>

              <span className="p6-approach-text">
                Combine the top three Phase 5
                models using their
                recommendation-score weights.
              </span>

              <span className="p6-approach-action">
                {approach ===
                "combined_score"
                  ? "Selected"
                  : "Select Combined Score"}
              </span>
            </button>
          </div>
        </div>
      </section>

      {/* =====================================================
          FEATURE CONFIGURATION
      ===================================================== */}

      <section className="p6-panel p6-selection-panel">
        <div className="p6-panel-head compact">
          <div>
            <div className="p6-eyebrow">
              FEATURE CONFIGURATION
            </div>

            <h3>
              Detection Columns
            </h3>

            <p>
              Select the columns that should be
              used for detection and investigation.
              Target Columns must be selected
              manually.
            </p>
          </div>

          <span className="p6-count-badge">
            {allColumns.length} available
          </span>
        </div>

        {/* =================================================
            TARGET
        ================================================= */}

        <MultiSelect
          label="Target Columns"
          help={
            isPointAnomaly
              ? "Point Anomaly detected: select exactly one column for the anomaly-detection feature matrix. No target is selected automatically."
              : "Columns used to build the anomaly-detection feature matrix. No target is selected automatically."
          }
          options={allColumns}
          value={targets}
          onChange={setTargets}
          maxSelections={
            isPointAnomaly ? 1 : null
          }
        />

        {isPointAnomaly && (
          <div className="p6-field-help">
            Point Anomaly requires exactly one Target Column.
          </div>
        )}

        {/* =================================================
            EXPLAIN BY
        ================================================= */}

        <MultiSelect
          label="Explain By Columns"
          help="Columns retained for investigation context and feature-level explanation."
          options={allColumns}
          value={explainBy}
          onChange={setExplainBy}
        />
      </section>

      {/* =====================================================
          CONTAMINATION CONFIGURATION
      ===================================================== */}

      <section className="p6-panel p6-contamination-panel">
        <div className="p6-panel-head compact p6-contamination-head">
          <div>
            <div className="p6-eyebrow">
              CONTAMINATION CONFIGURATION
            </div>

            <h3>
              How should PyOD determine the anomaly proportion?
            </h3>

            <p>
              Choose one method. The selected value is passed directly to the PyOD detector.
            </p>
          </div>

          <span className="p6-contamination-range">
            0.01–0.50 · 1%–50%
          </span>
        </div>

        <div className="p6-contamination-options">
          <button
            type="button"
            className={
              "p6-contamination-option" +
              (contaminationMode === "default" ? " active" : "")
            }
            onClick={() => setContaminationMode("default")}
            aria-pressed={contaminationMode === "default"}
          >
            <span className="p6-contamination-radio">
              {contaminationMode === "default" ? "✓" : ""}
            </span>

            <span className="p6-contamination-copy">
              <strong>Default PyOD</strong>
              <small>
                Uses an explicit contamination value of 0.10 (10%).
              </small>
            </span>

            <span className="p6-contamination-value">
              0.10 · 10%
            </span>
          </button>

          <div
            className={
              "p6-contamination-option p6-contamination-custom" +
              (contaminationMode === "custom" ? " active" : "")
            }
          >
            <button
              type="button"
              className="p6-contamination-choice"
              onClick={() => setContaminationMode("custom")}
              aria-pressed={contaminationMode === "custom"}
            >
              <span className="p6-contamination-radio">
                {contaminationMode === "custom" ? "✓" : ""}
              </span>

              <span className="p6-contamination-copy">
                <strong>Custom Contamination</strong>
                <small>
                  Set the expected anomaly proportion for this run.
                </small>
              </span>
            </button>

            <div
              className={
                "p6-contamination-stepper" +
                (contaminationMode !== "custom" ? " disabled" : "")
              }
            >
              <button
                type="button"
                aria-label="Decrease contamination"
                disabled={contaminationMode !== "custom" || customContamination <= 0.01}
                onClick={() =>
                  setCustomContamination((current) =>
                    Math.max(0.01, Number((current - 0.01).toFixed(2)))
                  )
                }
              >
                −
              </button>

              <span>
                {customContamination.toFixed(2)}
                <small>
                  ({Math.round(customContamination * 100)}%)
                </small>
              </span>

              <button
                type="button"
                aria-label="Increase contamination"
                disabled={contaminationMode !== "custom" || customContamination >= 0.50}
                onClick={() =>
                  setCustomContamination((current) =>
                    Math.min(0.50, Number((current + 0.01).toFixed(2)))
                  )
                }
              >
                +
              </button>
            </div>
          </div>
        </div>

        <div className="p6-contamination-helper">
          <span>Allowed range: 0.01–0.50 (1%–50%)</span>
          <strong>
            {contaminationMode === "default"
              ? "Default PyOD · 0.10 (10%)"
              : contaminationMode === "custom"
              ? `Custom Contamination · ${customContamination.toFixed(2)} (${Math.round(customContamination * 100)}%)`
              : "Select a contamination method to continue."}
          </strong>
        </div>
      </section>

      {/* =====================================================
          READY TO RUN
      ===================================================== */}

      <section className="p6-panel p6-summary-panel p6-ready-panel">
        <div className="p6-panel-head compact">
          <div>
            <div className="p6-eyebrow">
              READY TO RUN
            </div>

            <h3>
              Detection Configuration
            </h3>

            <p>
              Review the actual Phase 5
              recommendation models that
              will be used by this run.
            </p>
          </div>
        </div>

        <div className="p6-summary-grid">
          {/* APPROACH */}

          <div>
            <span>
              Approach
            </span>

            <strong>
              {approach ===
              "best_score"
                ? "🏆 Best Score"
                : "🔗 Combined Score"}
            </strong>
          </div>

          {/* MODELS */}

          <div className="p6-summary-models">
            <span>
              Models to be Trained
            </span>

            {selectedModels.length ? (
              <div className="p6-ready-model-list">
                {selectedModels.map(
                  (model, index) => (
                    <span
                      className="p6-ready-model"
                      key={
                        model?.model ||
                        model?.name ||
                        index
                      }
                    >
                      {normalizeModelName(
                        model
                      )}
                    </span>
                  )
                )}
              </div>
            ) : (
              <strong>
                No Phase 5 recommendation
              </strong>
            )}
          </div>

          {/* RECORDS */}

          <div>
            <span>
              Records
            </span>

            <strong>
              {config?.records ?? "—"}
            </strong>
          </div>

          {/* TARGET COUNT */}

          <div>
            <span>
              Target Columns
            </span>

            <strong>
              {targets.length
                ? `${targets.length} selected`
                : "None selected"}
            </strong>
          </div>
        </div>

        <div className="p6-contamination-summary">
          <div>
            <span>Method</span>
            <strong>
              {contaminationMode === "default"
                ? "Default PyOD"
                : contaminationMode === "custom"
                ? "Custom Contamination"
                : "Not selected"}
            </strong>
          </div>

          <div>
            <span>Contamination</span>
            <strong>
              {contaminationMode === "default"
                ? "0.10 (10%)"
                : contaminationMode === "custom"
                ? `${customContamination.toFixed(2)} (${Math.round(customContamination * 100)}%)`
                : "—"}
            </strong>
          </div>
        </div>

        {/* =================================================
            SELECTED TARGET / EXPLAIN BY
        ================================================= */}

        <div className="p6-summary-lines">
          <div>
            <span>
              Target
            </span>

            <div className="p6-chip-area">
              {targets.length ? (
                targets.map(
                  (item) => (
                    <span
                      className="p6-chip muted"
                      key={item}
                    >
                      {item}
                    </span>
                  )
                )
              ) : (
                <span className="p6-empty-inline">
                  Select at least one
                  target column.
                </span>
              )}
            </div>
          </div>

          <div>
            <span>
              Explain By
            </span>

            <div className="p6-chip-area">
              {explainBy.length ? (
                explainBy.map(
                  (item) => (
                    <span
                      className="p6-chip muted"
                      key={item}
                    >
                      {item}
                    </span>
                  )
                )
              ) : (
                <span className="p6-empty-inline">
                  None selected
                </span>
              )}
            </div>
          </div>
        </div>

        {/* =================================================
            TRAIN BUTTON
        ================================================= */}

        <button
          type="button"
          className="p6-primary-button"
          disabled={
            loading ||
            !targets.length ||
            !selectedModels.length ||
            !contaminationMode
          }
          onClick={submit}
        >
          {loading
            ? "Training & Detecting..."
            : "▶ Train & Detect Anomalies"}
        </button>

      </section>
    </div>
  );
}