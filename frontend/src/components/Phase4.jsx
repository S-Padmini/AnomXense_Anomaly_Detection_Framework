import React, { useMemo, useState } from "react";

const listValue = (v) =>
  Array.isArray(v)
    ? v
        .map((x) =>
          typeof x === "string"
            ? x
            : x?.column || x?.name || x?.field || x?.value || ""
        )
        .map(String)
        .map((x) => x.trim())
        .filter(Boolean)
    : [];

const modelsOf = (r) =>
  Array.isArray(r?.recommendations)
    ? r.recommendations.slice(0, 3)
    : Array.isArray(r?.recommended_models)
      ? r.recommended_models.slice(0, 3)
      : Array.isArray(r?.models)
        ? r.models.slice(0, 3)
        : [];

const num = (v) => (Number.isFinite(Number(v)) ? Number(v) : 0);

const width = (v, max) =>
  `${Math.max(0, Math.min(100, (num(v) / max) * 100))}%`;

export default function Phase4({
  detectionObjective = "",
  status,
  message,
  intent,
  configuration,
  recommendations,
  recommendationLoading,
  selectedColumns = [],
  onObjectiveChange,
  onContinue,
  onRetryRecommendations,
  onOpenPhase5,
  onReturnToPhase2,
}) {
  const [open, setOpen] = useState(null);

  /*
   * --------------------------------------------------------------------------
   * EXISTING PHASE 4 DATA
   * --------------------------------------------------------------------------
   */

  const cols = listValue(
    intent?.target_columns ||
      intent?.related_columns ||
      intent?.matched_columns ||
      intent?.referenced_columns ||
      configuration?.related_columns ||
      []
  );

  const type =
    intent?.anomaly_type ||
    intent?.inferred_anomaly_type ||
    configuration?.anomaly_type ||
    "—";

  const explanation =
    intent?.objective_explanation ||
    configuration?.objective_explanation ||
    intent?.explanation ||
    "The objective was interpreted from its natural-language meaning and matched against the available dataset context.";

  const reason =
    intent?.anomaly_type_reason ||
    configuration?.anomaly_type_reason ||
    intent?.reason ||
    intent?.reasoning ||
    `The objective is most consistent with ${String(
      type
    ).toLowerCase()} anomaly detection based on the behavior described.`;

  const models = modelsOf(recommendations);

  const understood = status === "analyzed" && !!intent;

  /*
   * --------------------------------------------------------------------------
   * ATTRIBUTE SELECTION VALIDATION
   *
   * IMPORTANT:
   *
   * The Phase 4 objective can identify attributes through:
   *
   *     intent.attributes_involved
   *
   * The backend may also provide:
   *
   *     intent.attribute_selection_validation
   *     intent.attribute_selection_valid
   *     intent.missing_attributes
   *     intent.required_attributes
   *
   * The live validation below intentionally uses the LATEST
   * selectedColumns prop as the source of truth for Phase 2 selection.
   *
   * This is important because the investigator may:
   *
   *     Phase 4
   *       ↓
   *     Phase 2
   *       ↓
   *     Change selected columns
   *       ↓
   *     Phase 3
   *       ↓
   *     Return to Phase 4
   *
   * In that situation we must compare the objective requirements again
   * against the latest confirmed Phase 2 selection.
   *
   * We do NOT silently add missing columns.
   * --------------------------------------------------------------------------
   */

  const attributeValidation = useMemo(() => {
    /*
     * ------------------------------------------------------------------------
     * STEP 1
     * Determine the objective-required attributes.
     *
     * Primary source:
     *
     *     intent.attributes_involved
     *
     * This is the field produced by the current Phase 4 objective matcher.
     *
     * Compatibility fallbacks are retained for older/newer response formats.
     * ------------------------------------------------------------------------
     */

    const requiredColumns = listValue(
      intent?.attributes_involved ||
        configuration?.attributes_involved ||
        intent?.required_attributes ||
        configuration?.required_attributes ||
        intent?.attribute_selection_validation?.required_columns ||
        configuration?.attribute_selection_validation?.required_columns ||
        []
    );

    /*
     * ------------------------------------------------------------------------
     * STEP 2
     * Read the LATEST Phase 2 selection.
     *
     * selectedColumns is supplied by the parent workflow.
     *
     * This is deliberately recalculated whenever selectedColumns changes.
     * ------------------------------------------------------------------------
     */

    const latestSelectedColumns = listValue(selectedColumns);

    /*
     * ------------------------------------------------------------------------
     * STEP 3
     * If the objective did not identify any required attributes, there is
     * nothing to validate.
     *
     * Do not show a warning in this case.
     * ------------------------------------------------------------------------
     */

    if (requiredColumns.length === 0) {
      return {
        exists: false,
        valid: true,
        requiredColumns: [],
        selectedColumns: latestSelectedColumns,
        missingColumns: [],
        status: "",
      };
    }

    /*
     * ------------------------------------------------------------------------
     * STEP 4
     * Compare objective-required attributes with the CURRENT Phase 2
     * selection.
     *
     * Exact column-name matching is intentional because the objective parser
     * has already resolved the semantic attribute to an actual dataset
     * column.
     * ------------------------------------------------------------------------
     */

    const selectedSet = new Set(latestSelectedColumns);

    const missingColumns = requiredColumns.filter(
      (column) => !selectedSet.has(column)
    );

    const valid = missingColumns.length === 0;

    /*
     * ------------------------------------------------------------------------
     * STEP 5
     * Prefer backend validation status only when it agrees with the current
     * live comparison.
     *
     * The live comparison always controls valid/missingColumns.
     * ------------------------------------------------------------------------
     */

    const backendValidation =
      intent?.attribute_selection_validation ||
      configuration?.attribute_selection_validation ||
      null;

    const statusText =
      valid
        ? "Validation Passed — All required attributes selected"
        : backendValidation?.status ||
          "Validation Failed — Required attribute missing";

    return {
      exists: true,
      valid,
      requiredColumns,
      selectedColumns: latestSelectedColumns,
      missingColumns,
      status: statusText,
    };
  }, [
    intent,
    configuration,
    selectedColumns,
  ]);

  /*
   * --------------------------------------------------------------------------
   * ONLY SHOW THE DISCLAIMER WHEN THE LIVE VALIDATION FAILS.
   *
   * If all required attributes are present:
   *
   *     showAttributeValidation = false
   *
   * Therefore Phase 4 visually remains in its existing successful state.
   * --------------------------------------------------------------------------
   */

  const showAttributeValidation =
    understood &&
    attributeValidation.exists &&
    !attributeValidation.valid;

  /*
   * --------------------------------------------------------------------------
   * NEXT BUTTON
   *
   * Model Recommendation can only be opened when:
   *
   * 1. All objective-required attributes are present in Phase 2.
   * 2. Model recommendations exist.
   * 3. Recommendations are not currently loading.
   * --------------------------------------------------------------------------
   */

  const canProceedToPhase5 =
    attributeValidation.valid &&
    models.length > 0 &&
    !recommendationLoading;

  /*
   * --------------------------------------------------------------------------
   * UI
   * --------------------------------------------------------------------------
   */

  return (
    <section className="workflow-section p4">
      <style>{`
        .p4{
          position:relative;
          overflow:hidden;
          padding:28px;
          background:
            radial-gradient(circle at 88% 0%,rgba(124,92,255,.13),transparent 30%),
            linear-gradient(145deg,#0b1730,#111634 55%,#17143d);
          border:1px solid rgba(139,92,246,.24);
          border-radius:22px;
          color:#eef2ff
        }

        .p4 *{
          box-sizing:border-box
        }

        .p4-head{
          display:flex;
          justify-content:space-between;
          gap:20px;
          margin-bottom:22px
        }

        .p4-k{
          margin:0 0 7px;
          color:#a78bfa;
          font-size:10px;
          font-weight:900;
          letter-spacing:.18em
        }

        .p4-title{
          margin:0;
          color:#f7f7ff;
          font-size:24px;
          line-height:1.2
        }

        .p4-sub{
          max-width:780px;
          margin:9px 0 0;
          color:#9eabc3;
          font-size:12px;
          line-height:1.65
        }

        .p4-status{
          padding:8px 12px;
          height:max-content;
          border:1px solid rgba(167,139,250,.28);
          border-radius:999px;
          background:rgba(124,92,255,.09);
          color:#c4b5fd;
          font-size:10px;
          font-weight:800;
          white-space:nowrap
        }

        .p4-input,
        .p4-card,
        .p4-mini{
          border:1px solid rgba(139,92,246,.19);
          border-radius:16px;
          background:rgba(6,16,34,.66);
          box-shadow:inset 0 1px 0 rgba(255,255,255,.025)
        }

        .p4-input{
          padding:19px
        }

        .p4-input-title{
          margin:0;
          color:#f1f5ff;
          font-size:14px
        }

        .p4-hint{
          margin:5px 0 10px;
          color:#8190aa;
          font-size:11px;
          line-height:1.5
        }

        .p4-text{
          display:block;
          width:100%;
          min-height:116px;
          resize:vertical;
          padding:14px 15px;
          border:1px solid rgba(139,92,246,.25);
          border-radius:12px;
          outline:0;
          background:#071022;
          color:#f2f5ff;
          font:inherit;
          font-size:13px;
          line-height:1.6
        }

        .p4-text:focus{
          border-color:#a78bfa;
          box-shadow:0 0 0 3px rgba(139,92,246,.12)
        }

        .p4-text::placeholder{
          color:#596780
        }

        .p4-foot{
          display:flex;
          justify-content:space-between;
          margin-top:8px;
          color:#66758f;
          font-size:10px
        }

        .p4-actions{
          display:flex;
          justify-content:flex-end;
          margin-top:13px
        }

        .p4-primary,
        .p4-secondary{
          border-radius:9px;
          padding:10px 14px;
          font-size:10px;
          font-weight:800;
          cursor:pointer
        }

        .p4-primary{
          border:0;
          background:linear-gradient(135deg,#8b5cf6,#6d5bd0);
          color:#fff;
          box-shadow:0 9px 22px rgba(80,58,180,.22)
        }

        .p4-secondary{
          border:1px solid rgba(139,92,246,.22);
          background:rgba(255,255,255,.025);
          color:#aeb9cc
        }

        .p4-primary:disabled,
        .p4-secondary:disabled{
          opacity:.5;
          cursor:not-allowed
        }

        .p4-alert,
        .p4-working{
          display:flex;
          gap:12px;
          margin-top:14px;
          padding:14px 16px;
          border-radius:13px
        }

        .p4-alert{
          border:1px solid rgba(248,113,113,.25);
          background:rgba(127,29,29,.16)
        }

        .p4-alert strong{
          color:#fecaca;
          font-size:12px
        }

        .p4-alert p{
          margin:4px 0 0;
          color:#b6a7b3;
          font-size:11px
        }

        .p4-icon{
          display:grid;
          flex:0 0 25px;
          width:25px;
          height:25px;
          place-items:center;
          border-radius:50%;
          background:rgba(248,113,113,.13);
          color:#fca5a5;
          font-weight:900
        }

        .p4-working{
          align-items:center;
          border:1px solid rgba(139,92,246,.2);
          background:rgba(124,92,255,.07)
        }

        .p4-spinner{
          width:18px;
          height:18px;
          border:2px solid rgba(196,181,253,.2);
          border-top-color:#c4b5fd;
          border-radius:50%;
          animation:p4spin .8s linear infinite
        }

        @keyframes p4spin{
          to{
            transform:rotate(360deg)
          }
        }

        .p4-working strong{
          color:#ddd6fe;
          font-size:11px
        }

        .p4-working span{
          display:block;
          margin-top:2px;
          color:#8e9bb3;
          font-size:10px
        }

        /*
         * --------------------------------------------------------------------
         * ATTRIBUTE VALIDATION
         * --------------------------------------------------------------------
         */

        .p4-validation{
          margin-top:14px;
          border:1px solid rgba(248,113,113,.30);
          border-radius:15px;
          background:
            linear-gradient(
              145deg,
              rgba(127,29,29,.18),
              rgba(69,10,10,.12)
            );
          overflow:hidden
        }

        .p4-validation-head{
          display:flex;
          align-items:flex-start;
          gap:12px;
          padding:16px 17px;
          border-bottom:1px solid rgba(248,113,113,.12)
        }

        .p4-validation-icon{
          display:grid;
          flex:0 0 29px;
          width:29px;
          height:29px;
          place-items:center;
          border-radius:9px;
          background:rgba(248,113,113,.13);
          border:1px solid rgba(248,113,113,.20);
          color:#fca5a5;
          font-size:13px;
          font-weight:900
        }

        .p4-validation-label{
          margin:0 0 4px;
          color:#fca5a5;
          font-size:9px;
          font-weight:900;
          letter-spacing:.15em
        }

        .p4-validation-title{
          margin:0;
          color:#fee2e2;
          font-size:14px;
          font-weight:850
        }

        .p4-validation-body{
          padding:16px 17px
        }

        .p4-validation-intro{
          margin:0;
          color:#c7b8c1;
          font-size:11px;
          line-height:1.6
        }

        .p4-missing-list{
          display:flex;
          flex-wrap:wrap;
          gap:8px;
          margin-top:11px
        }

        .p4-missing-chip{
          display:inline-flex;
          align-items:center;
          gap:6px;
          max-width:100%;
          padding:7px 10px;
          border:1px solid rgba(248,113,113,.27);
          border-radius:8px;
          background:rgba(127,29,29,.20);
          color:#fecaca;
          font-size:10px;
          font-weight:800;
          overflow-wrap:anywhere
        }

        .p4-missing-x{
          color:#f87171;
          font-size:10px;
          font-weight:900
        }

        .p4-action-box{
          margin-top:14px;
          padding:13px 14px;
          border:1px solid rgba(255,255,255,.055);
          border-radius:10px;
          background:rgba(255,255,255,.018)
        }

        .p4-action-title{
          margin:0 0 7px;
          color:#e2e8f0;
          font-size:10px;
          font-weight:850
        }

        .p4-action-list{
          margin:0;
          padding-left:18px;
          color:#9faabd;
          font-size:10px;
          line-height:1.75
        }

        .p4-validation-status{
          display:flex;
          align-items:center;
          gap:7px;
          margin-top:13px;
          color:#fca5a5;
          font-size:9px;
          font-weight:850
        }

        .p4-status-dot{
          width:6px;
          height:6px;
          border-radius:50%;
          background:#f87171
        }

        .p4-validation-actions{
          display:flex;
          justify-content:space-between;
          align-items:center;
          gap:10px;
          margin-top:14px;
          padding-top:13px;
          border-top:1px solid rgba(248,113,113,.11)
        }

        .p4-return-button{
          border:1px solid rgba(248,113,113,.24);
          border-radius:9px;
          padding:9px 12px;
          background:rgba(127,29,29,.12);
          color:#fecaca;
          font-size:10px;
          font-weight:800;
          cursor:pointer
        }

        .p4-return-button:hover{
          background:rgba(127,29,29,.22)
        }

        .p4-blocked-button{
          display:inline-flex;
          align-items:center;
          gap:6px;
          border:1px solid rgba(139,92,246,.16);
          border-radius:9px;
          padding:9px 12px;
          background:rgba(255,255,255,.025);
          color:#77839a;
          font-size:10px;
          font-weight:800;
          cursor:not-allowed
        }

        /*
         * --------------------------------------------------------------------
         * EXISTING RESULTS
         * --------------------------------------------------------------------
         */

        .p4-results{
          display:grid;
          gap:13px;
          margin-top:22px
        }

        .p4-two{
          display:grid;
          grid-template-columns:1.15fr .85fr;
          gap:13px
        }

        .p4-mini{
          padding:17px;
          min-height:150px
        }

        .p4-no{
          margin:0 0 6px;
          color:#a78bfa;
          font-size:9px;
          font-weight:900;
          letter-spacing:.16em
        }

        .p4-mini h3{
          margin:5px 0 9px;
          color:#f1f5ff;
          font-size:17px
        }

        .p4-copy{
          margin:0;
          color:#aab5c8;
          font-size:11px;
          line-height:1.7
        }

        .p4-badge{
          display:inline-flex;
          padding:7px 10px;
          border:1px solid rgba(167,139,250,.3);
          border-radius:8px;
          background:rgba(139,92,246,.1);
          color:#ddd6fe;
          font-size:12px;
          font-weight:850;
          text-transform:capitalize
        }

        .p4-card-head{
          display:flex;
          justify-content:space-between;
          gap:15px;
          padding:17px 18px;
          border-bottom:1px solid rgba(255,255,255,.055)
        }

        .p4-card-title{
          margin:0;
          color:#f3f5ff;
          font-size:14px
        }

        .p4-desc{
          margin:5px 0 0;
          color:#7f8da5;
          font-size:10px;
          line-height:1.5
        }

        .p4-count{
          min-width:58px;
          height:max-content;
          padding:7px 9px;
          border:1px solid rgba(139,92,246,.2);
          border-radius:8px;
          background:rgba(255,255,255,.025);
          color:#c4b5fd;
          font-size:10px;
          font-weight:800;
          text-align:center
        }

        .p4-body{
          padding:17px 18px
        }

        .p4-chips{
          display:flex;
          flex-wrap:wrap;
          gap:8px
        }

        .p4-chip{
          display:inline-flex;
          max-width:100%;
          padding:7px 10px;
          border:1px solid rgba(139,92,246,.23);
          border-radius:8px;
          background:rgba(124,92,255,.08);
          color:#cbd5e1;
          font-size:10px;
          overflow-wrap:anywhere
        }

        .p4-note{
          margin-top:10px;
          color:#718099;
          font-size:9px
        }

        .p4-empty{
          padding:13px;
          border:1px dashed rgba(139,92,246,.2);
          border-radius:10px;
          color:#78869e;
          background:rgba(255,255,255,.015);
          font-size:10px;
          line-height:1.5
        }

        .p4-empty strong{
          color:#b8c3d5
        }

        .p4-models{
          display:grid;
          gap:10px
        }

        .p4-model{
          padding:15px;
          border:1px solid rgba(139,92,246,.16);
          border-radius:13px;
          background:
            linear-gradient(
              145deg,
              rgba(13,25,51,.78),
              rgba(25,18,53,.64)
            )
        }

        .p4-model-top{
          display:flex;
          justify-content:space-between;
          gap:14px;
          align-items:center
        }

        .p4-rank{
          color:#a78bfa;
          font-size:9px;
          font-weight:900;
          letter-spacing:.1em
        }

        .p4-name{
          margin:3px 0 4px;
          color:#f4f5ff;
          font-size:14px
        }

        .p4-reason{
          margin:0;
          color:#8795ad;
          font-size:10px;
          line-height:1.5
        }

        .p4-final{
          min-width:92px;
          padding:9px 10px;
          border:1px solid rgba(167,139,250,.2);
          border-radius:10px;
          background:rgba(124,92,255,.07);
          text-align:center
        }

        .p4-final span,
        .p4-metric span{
          display:block;
          color:#77859d;
          font-size:8px;
          font-weight:800;
          letter-spacing:.08em
        }

        .p4-final strong{
          display:block;
          margin-top:2px;
          color:#e9d5ff;
          font-size:20px
        }

        .p4-final small{
          font-size:9px;
          color:#8f83b7
        }

        .p4-metrics{
          display:grid;
          grid-template-columns:1fr 1fr;
          gap:10px;
          margin-top:12px
        }

        .p4-metric{
          padding:10px;
          border:1px solid rgba(255,255,255,.05);
          border-radius:9px;
          background:rgba(255,255,255,.025)
        }

        .p4-metric strong{
          display:block;
          margin-top:3px;
          color:#dbe5f0;
          font-size:11px
        }

        .p4-bar{
          height:5px;
          margin-top:7px;
          overflow:hidden;
          border-radius:99px;
          background:rgba(255,255,255,.07)
        }

        .p4-bar i{
          display:block;
          height:100%;
          border-radius:inherit;
          background:linear-gradient(90deg,#7c5cff,#b69cff)
        }

        .p4-details{
          margin-top:11px;
          border-top:1px solid rgba(255,255,255,.05);
          padding-top:10px
        }

        .p4-details summary{
          cursor:pointer;
          color:#c4b5fd;
          font-size:10px;
          font-weight:800;
          list-style:none
        }

        .p4-details summary::-webkit-details-marker{
          display:none
        }

        .p4-details summary:before{
          content:"▸";
          display:inline-block;
          margin-right:6px
        }

        .p4-details[open] summary:before{
          transform:rotate(90deg)
        }

        .p4-factors{
          display:grid;
          gap:7px;
          margin-top:9px
        }

        .p4-factor{
          padding:9px 10px;
          border:1px solid rgba(255,255,255,.045);
          border-radius:8px;
          background:rgba(255,255,255,.018)
        }

        .p4-factor-top{
          display:flex;
          justify-content:space-between;
          gap:12px
        }

        .p4-factor strong{
          color:#d8e1ee;
          font-size:9px
        }

        .p4-factor em{
          color:#c4b5fd;
          font-size:9px;
          font-style:normal;
          white-space:nowrap
        }

        .p4-factor p{
          margin:4px 0 0;
          color:#77859b;
          font-size:9px;
          line-height:1.45
        }

        .p4-bottom{
          display:flex;
          justify-content:space-between;
          align-items:center;
          gap:10px;
          margin-top:12px
        }

        @media(max-width:850px){
          .p4-head,
          .p4-model-top,
          .p4-bottom,
          .p4-validation-actions{
            flex-direction:column;
            align-items:stretch
          }

          .p4-two{
            grid-template-columns:1fr
          }

          .p4-final{
            width:100%
          }

          .p4-blocked-button{
            justify-content:center
          }
        }
      `}</style>

      {/* ------------------------------------------------------------------ */}
      {/* HEADER                                                             */}
      {/* ------------------------------------------------------------------ */}

      <div className="p4-head">
        <div>
          <p className="p4-k">PHASE 04 · INTELLIGENT DETECTION</p>

          <h2 className="p4-title">
            Objective Understanding &amp; Model Recommendation
          </h2>

          <p className="p4-sub">
            Describe only what you want to detect. The semantic/NLP/LLM layer
            interprets the objective, identifies the anomaly type, maps related
            columns, and ranks models using Phase 3 dataset characteristics.
          </p>
        </div>

        <div className="p4-status">
          {status === "analyzing"
            ? "● Understanding"
            : understood
              ? "✓ Objective understood"
              : "Natural language"}
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* OBJECTIVE INPUT                                                    */}
      {/* ------------------------------------------------------------------ */}

      <div className="p4-input">
        <h3 className="p4-input-title">
          What do you want to detect?
        </h3>

        <p className="p4-hint">
          Enter only your objective. Do not select anomaly type, scope, or
          temporal mode. The system infers them automatically.
        </p>

        <textarea
          className="p4-text"
          value={detectionObjective}
          onChange={(e) => onObjectiveChange(e.target.value)}
          placeholder="Example: Identify unusual transaction amounts that are significantly different from the normal transaction pattern."
          rows={5}
          maxLength={1000}
          disabled={status === "analyzing"}
        />

        <div className="p4-foot">
          <span>
            Natural language objective • no manual anomaly configuration
          </span>

          <span>{detectionObjective.length}/1000</span>
        </div>

        <div className="p4-actions">
          <button
            className="p4-primary"
            type="button"
            onClick={onContinue}
            disabled={
              status === "analyzing" ||
              !detectionObjective.trim()
            }
          >
            {status === "analyzing"
              ? "Understanding..."
              : "Understand Objective →"}
          </button>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* ERROR                                                              */}
      {/* ------------------------------------------------------------------ */}

      {status === "error" && (
        <div className="p4-alert">
          <div className="p4-icon">!</div>

          <div>
            <strong>
              Unable to understand objective
            </strong>

            <p>
              {message ||
                "Phase 4 could not complete the request."}
            </p>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* WORKING                                                            */}
      {/* ------------------------------------------------------------------ */}

      {status === "analyzing" && (
        <div className="p4-working">
          <div className="p4-spinner" />

          <div>
            <strong>
              Semantic analysis in progress
            </strong>

            <span>
              Understanding the objective, identifying anomaly behavior,
              mapping columns, and preparing model scoring...
            </span>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* RESULTS                                                            */}
      {/* ------------------------------------------------------------------ */}

      {understood && (
        <div className="p4-results">

          {/* -------------------------------------------------------------- */}
          {/* OBJECTIVE + ANOMALY TYPE                                      */}
          {/* -------------------------------------------------------------- */}

          <div className="p4-two">

            <article className="p4-mini">
              <p className="p4-no">
                01 · OBJECTIVE EXPLANATION
              </p>

              <h3>
                What the system understood
              </h3>

              <p className="p4-copy">
                {explanation}
              </p>
            </article>

            <article className="p4-mini">
              <p className="p4-no">
                02 · ANOMALY TYPE
              </p>

              <div style={{ margin: "8px 0 11px" }}>
                <span className="p4-badge">
                  {String(type).replace(/_/g, " ")}
                </span>
              </div>

              <p className="p4-copy">
                {reason}
              </p>
            </article>

          </div>

          {/* -------------------------------------------------------------- */}
          {/* RELATED COLUMNS                                               */}
          {/* -------------------------------------------------------------- */}

          <article className="p4-card">
            <div className="p4-card-head">
              <div>
                <p className="p4-no">
                  03 · RELATED COLUMNS
                </p>

                <h3 className="p4-card-title">
                  Columns related to this objective
                </h3>

                <p className="p4-desc">
                  Semantically inferred from the objective and Phase 1/2
                  dataset metadata. Nothing is re-selected here.
                </p>
              </div>

              <div className="p4-count">
                {cols.length} matched
              </div>
            </div>

            <div className="p4-body">

              {cols.length ? (
                <div className="p4-chips">
                  {cols.map((c, i) => (
                    <span
                      className="p4-chip"
                      key={`${c}-${i}`}
                    >
                      {c}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="p4-empty">
                  No specific column was confidently mapped. The
                  recommendation engine will use the selected Phase 2
                  column context.
                </div>
              )}

              <div className="p4-note">
                {selectedColumns.length} columns selected in Phase 2
              </div>
            </div>
          </article>

          {/* -------------------------------------------------------------- */}
          {/* ATTRIBUTE SELECTION VALIDATION                                */}
          {/* -------------------------------------------------------------- */}

          {showAttributeValidation && (
            <article className="p4-validation">

              <div className="p4-validation-head">

                <div className="p4-validation-icon">
                  !
                </div>

                <div>
                  <p className="p4-validation-label">
                    ATTRIBUTE SELECTION VALIDATION
                  </p>

                  <h3 className="p4-validation-title">
                    Required attribute not selected in Phase 2
                  </h3>
                </div>

              </div>

              <div className="p4-validation-body">

                <p className="p4-validation-intro">
                  The current investigation objective requires:
                </p>

                <div className="p4-missing-list">
                  {attributeValidation.missingColumns.map(
                    (column, index) => (
                      <span
                        className="p4-missing-chip"
                        key={`${column}-${index}`}
                      >
                        <span className="p4-missing-x">
                          ❌
                        </span>

                        {column}
                      </span>
                    )
                  )}
                </div>

                <p
                  className="p4-validation-intro"
                  style={{ marginTop: 12 }}
                >
                  These attribute(s) were not included in your confirmed
                  Phase 2 Dataset-Level Attribute Selection.
                </p>

                <div className="p4-action-box">

                  <p className="p4-action-title">
                    ACTION REQUIRED
                  </p>

                  <p
                    style={{
                      margin: "0 0 8px",
                      color: "#c7b8c1",
                      fontSize: "10px",
                      lineHeight: 1.65,
                    }}
                  >
                    Please go to Phase 2 → review/reselect the required
                    attribute(s) in Dataset-Level Attribute Selection →
                    confirm your selection → proceed through Phase 3
                    Preprocessing → perform Statistical Analysis → return to
                    Phase 4.
                  </p>

                  <p
                    style={{
                      margin: 0,
                      color: "#c7b8c1",
                      fontSize: "10px",
                      lineHeight: 1.65,
                    }}
                  >
                    The objective will be revalidated automatically when you
                    return.
                  </p>

                </div>

                <div className="p4-validation-status">
                  <span className="p4-status-dot" />

                  {attributeValidation.status ||
                    "Validation Failed — Required attribute missing"}
                </div>

                <div className="p4-validation-actions">

                  <button
                    className="p4-return-button"
                    type="button"
                    onClick={() => {
                      if (typeof onReturnToPhase2 === "function") {
                        onReturnToPhase2();
                      }
                    }}
                    disabled={
                      typeof onReturnToPhase2 !== "function"
                    }
                  >
                    ← Return to Phase 2
                  </button>

                  <button
                    className="p4-blocked-button"
                    type="button"
                    disabled
                    title="Complete the required Phase 2 and Phase 3 steps first."
                  >
                    Next: Model Recommendation 🔒
                  </button>

                </div>

              </div>
            </article>
          )}

          {/* -------------------------------------------------------------- */}
          {/* MODEL RECOMMENDATION                                          */}
          {/* -------------------------------------------------------------- */}

          <article className="p4-card">

            <div className="p4-card-head">

              <div>
                <p className="p4-no">
                  04 · MODEL RECOMMENDATION
                </p>

                <h3 className="p4-card-title">
                  Best-fit anomaly detection models
                </h3>

                <p className="p4-desc">
                  Ranking combines Phase 3 statistical suitability with
                  Phase 4 objective suitability.
                </p>
              </div>

              <div className="p4-count">
                {recommendationLoading
                  ? "..."
                  : `${models.length} ranked`}
              </div>

            </div>

            <div className="p4-body">

              {/* ---------------------------------------------------------- */}
              {/* RECOMMENDATION LOADING                                    */}
              {/* ---------------------------------------------------------- */}

              {recommendationLoading && (
                <div
                  className="p4-working"
                  style={{ marginTop: 0 }}
                >
                  <div className="p4-spinner" />

                  <div>
                    <strong>
                      Scoring candidate models
                    </strong>

                    <span>
                      Comparing dataset characteristics with the
                      interpreted objective...
                    </span>
                  </div>
                </div>
              )}

              {/* ---------------------------------------------------------- */}
              {/* NO MODELS                                                 */}
              {/* ---------------------------------------------------------- */}

              {!recommendationLoading &&
                !models.length && (
                  <div className="p4-empty">

                    <strong>
                      No model ranking is available yet.
                    </strong>

                    <br />

                    Objective understanding succeeded, but the
                    recommendation service returned no models.
                    Retry the recommendation.

                    <div style={{ marginTop: 10 }}>
                      <button
                        className="p4-secondary"
                        type="button"
                        onClick={onRetryRecommendations}
                      >
                        Retry Recommendation
                      </button>
                    </div>

                  </div>
                )}

              {/* ---------------------------------------------------------- */}
              {/* MODELS                                                    */}
              {/* ---------------------------------------------------------- */}

              {!recommendationLoading &&
                models.length > 0 && (
                  <div className="p4-models">

                    {models.map((m, i) => {

                      const final = num(m.final_score);
                      const stat = num(m.statistical_score);
                      const obj = num(m.objective_score);

                      const sd = Array.isArray(
                        m.statistical_details
                      )
                        ? m.statistical_details
                        : [];

                      const od = Array.isArray(
                        m.objective_details
                      )
                        ? m.objective_details
                        : [];

                      return (
                        <div
                          className="p4-model"
                          key={m.model || i}
                        >

                          <div className="p4-model-top">

                            <div style={{ minWidth: 0 }}>

                              <div className="p4-rank">
                                RANK #{m.rank || i + 1}
                              </div>

                              <h4 className="p4-name">
                                {m.model || "Unknown Model"}
                              </h4>

                              <p className="p4-reason">
                                {m.recommendation_reason ||
                                  "Recommended from combined dataset and objective suitability."}
                              </p>

                            </div>

                            <div className="p4-final">

                              <span>
                                FINAL SCORE
                              </span>

                              <strong>
                                {final.toFixed(2)}
                                <small>
                                  /100
                                </small>
                              </strong>

                            </div>

                          </div>

                          <div className="p4-metrics">

                            <div className="p4-metric">

                              <span>
                                STATISTICAL FIT
                              </span>

                              <strong>
                                {stat.toFixed(2)} / 70
                              </strong>

                              <div className="p4-bar">
                                <i
                                  style={{
                                    width: width(stat, 70)
                                  }}
                                />
                              </div>

                            </div>

                            <div className="p4-metric">

                              <span>
                                OBJECTIVE FIT
                              </span>

                              <strong>
                                {obj.toFixed(2)} / 30
                              </strong>

                              <div className="p4-bar">
                                <i
                                  style={{
                                    width: width(obj, 30)
                                  }}
                                />
                              </div>

                            </div>

                          </div>

                          <details
                            className="p4-details"
                            open={open === i}
                            onToggle={(e) =>
                              setOpen(
                                e.currentTarget.open
                                  ? i
                                  : null
                              )
                            }
                          >

                            <summary>
                              View Score Breakdown
                            </summary>

                            <div className="p4-factors">

                              {[...sd, ...od].map(
                                (d, j) => (
                                  <div
                                    className="p4-factor"
                                    key={`${d?.factor || "factor"}-${j}`}
                                  >

                                    <div className="p4-factor-top">

                                      <strong>
                                        {d?.factor ||
                                          "Score factor"}
                                      </strong>

                                      <em>
                                        {num(
                                          d?.score
                                        ).toFixed(2)}{" "}
                                        /{" "}
                                        {d?.maximum ??
                                          "—"}
                                      </em>

                                    </div>

                                    <p>
                                      {d?.reason ||
                                        "No factor explanation was returned."}
                                    </p>

                                  </div>
                                )
                              )}

                            </div>

                          </details>

                        </div>
                      );
                    })}

                  </div>
                )}

              {/* ---------------------------------------------------------- */}
              {/* BOTTOM ACTIONS                                            */}
              {/* ---------------------------------------------------------- */}

              {models.length > 0 && (
                <div className="p4-bottom">

                  <span className="p4-note">
                    Phase 3 dataset evidence + Phase 4 objective fit
                  </span>

                  <div
                    style={{
                      display: "flex",
                      gap: 8
                    }}
                  >

                    <button
                      className="p4-secondary"
                      type="button"
                      onClick={onRetryRecommendations}
                    >
                      Refresh Scores
                    </button>

                    <button
                      className="p4-primary"
                      type="button"
                      onClick={onOpenPhase5}
                      disabled={!canProceedToPhase5}
                      title={
                        !attributeValidation.valid
                          ? "Required Phase 2 attributes are missing."
                          : recommendationLoading
                            ? "Recommendation is still loading."
                            : !models.length
                              ? "No model recommendation is available."
                              : ""
                      }
                    >
                      {attributeValidation.valid
                        ? "View Detailed Scores →"
                        : "Next: Model Recommendation 🔒"}
                    </button>

                  </div>

                </div>
              )}

            </div>
          </article>

        </div>
      )}
    </section>
  );
}