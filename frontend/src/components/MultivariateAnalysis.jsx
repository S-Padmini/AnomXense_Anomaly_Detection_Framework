import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

const COLORS = {
  page: "#eef2ff",
  page2: "#f8f9ff",
  royal: "#33438b",
  royalDark: "#33438b",
  royalMid: "#4257ad",
  royalLight: "#eef1ff",
  gold: "#c8a45d",
  goldSoft: "#fbf5e8",
  ink: "#223264",
  muted: "#66718c",
  border: "#d9e0f0",
  surface: "#ffffff",
  surfaceSoft: "#f8f9fd",
  blue: "#315fba",
  red: "#c52b48",
  redSoft: "#fff0f3",
  green: "#13795b",
  greenSoft: "#edf8f3",
};

const styles = {
  page: {
    minHeight: "100%",
    zoom: "0.80",
    padding: "22px",
    background:
      "linear-gradient(180deg, #e9edff 0%, #f4f6fc 42%, #f8f9fd 100%)",
    color: COLORS.ink,
    fontFamily:
      "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontSize: "18px",
  },

  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "18px",
    padding: "22px 24px",
    marginBottom: "14px",
    borderRadius: "16px",
    color: "#fff",
    background:
      "linear-gradient(135deg, #17255f 0%, #293b8f 58%, #4257ad 100%)",
    boxShadow:
      "0 14px 34px rgba(35,53,125,.22)",
  },

  headerTitle: {
    margin: 0,
    fontSize: "29px",
    fontWeight: 800,
  },

  headerText: {
    margin: "7px 0 0",
    color: "rgba(255,255,255,.78)",
    fontSize: "18px",
    lineHeight: 1.5,
  },

  backButton: {
    border:
      "1px solid rgba(255,255,255,.35)",
    background:
      "rgba(255,255,255,.10)",
    color: "#fff",
    borderRadius: "9px",
    padding: "10px 15px",
    fontSize: "17px",
    fontWeight: 700,
    cursor: "pointer",
  },

  banner: {
    display: "grid",
    gridTemplateColumns:
      "repeat(auto-fit,minmax(190px,1fr))",
    gap: "1px",
    marginBottom: "14px",
    overflow: "hidden",
    borderRadius: "13px",
    background: COLORS.border,
    border: `1px solid ${COLORS.border}`,
  },

  bannerItem: {
    padding: "13px 17px",
    background: "#f1f5ff",
  },

  label: {
    display: "block",
    color: COLORS.muted,
    fontSize: "16px",
    fontWeight: 700,
    marginBottom: "4px",
  },

  value: {
    color: COLORS.royalDark,
    fontSize: "20px",
    fontWeight: 850,
  },

  section: {
    background: COLORS.surface,
    border: `1px solid ${COLORS.border}`,
    borderTop:
      `4px solid ${COLORS.royal}`,
    borderRadius: "14px",
    marginBottom: "14px",
    overflow: "hidden",
    boxShadow:
      "0 7px 22px rgba(27,43,94,.07)",
    transition:
      "transform .18s ease,box-shadow .18s ease",
  },

  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "15px",
    padding: "16px 18px",
    background:
      "linear-gradient(90deg,#f4f6ff 0%,#fff 70%)",
    borderBottom:
      `1px solid ${COLORS.border}`,
  },

  sectionTitle: {
    margin: 0,
    fontSize: "23px",
    fontWeight: 800,
    color: COLORS.royalDark,
  },

  sectionText: {
    margin: "5px 0 0",
    color: COLORS.muted,
    fontSize: "17px",
    lineHeight: 1.45,
  },

  tableWrap: {
    width: "100%",
    overflowX: "auto",
  },

  recordsTableWrap: {
    width: "100%",
    maxHeight: "520px",
    overflowX: "auto",
    overflowY: "auto",
    border: `1px solid ${COLORS.border}`,
    borderRadius: "10px",
  },

  table: {
    width: "100%",
    borderCollapse: "separate",
    borderSpacing: 0,
    fontSize: "18px",
  },

  th: {
    padding: "13px 15px",
    textAlign: "left",
    whiteSpace: "nowrap",
    background: COLORS.royalDark,
    color: "#fff",
    fontWeight: 800,
    borderRight:
      "1px solid rgba(255,255,255,.12)",
  },

  td: {
    padding: "13px 15px",
    borderBottom:
      `1px solid ${COLORS.border}`,
    verticalAlign: "middle",
    background: "#f1f5ff",
    color: COLORS.ink,
  },

  normal: {
    display: "inline-flex",
    padding: "5px 10px",
    borderRadius: "999px",
    background: COLORS.greenSoft,
    color: COLORS.green,
    fontSize: "16px",
    fontWeight: 800,
  },

  anomaly: {
    display: "inline-flex",
    padding: "5px 10px",
    borderRadius: "999px",
    background: COLORS.redSoft,
    color: COLORS.red,
    fontSize: "16px",
    fontWeight: 800,
  },

  score: {
    color: COLORS.royalDark,
    fontWeight: 850,
    fontVariantNumeric: "tabular-nums",
  },

  filter: {
    border: `1px solid ${COLORS.border}`,
    background: "#fff",
    color: COLORS.ink,
    borderRadius: "8px",
    padding: "9px 12px",
    fontSize: "17px",
    fontWeight: 700,
  },

  exploreButton: {
    border: `1px solid ${COLORS.royal}`,
    background: COLORS.royal,
    color: "#fff",
    borderRadius: "8px",
    padding: "8px 13px",
    fontSize: "16px",
    fontWeight: 800,
    cursor: "pointer",
    whiteSpace: "nowrap",
  },

  smallViewButton: {
    border: `1px solid ${COLORS.border}`,
    background: "#fff",
    color: COLORS.royal,
    borderRadius: "7px",
    padding: "6px 10px",
    fontSize: "14px",
    fontWeight: 800,
    cursor: "pointer",
    whiteSpace: "nowrap",
  },

  contributionCard: {
    margin: "0 16px 16px",
    border: `1px solid ${COLORS.border}`,
    borderRadius: "10px",
    overflow: "hidden",
    background: COLORS.surfaceSoft,
  },

  contributionDetail: {
    margin: "12px 0 0",
    padding: "14px",
    border: `1px solid ${COLORS.border}`,
    borderRadius: "10px",
    background: "#fff",
  },

  chartBox: {
    padding: "15px",
    overflowX: "auto",
    background:
      "linear-gradient(180deg,#fbfcff,#f3f5fd)",
  },

  innerChart: {
    background: "#fff",
    border:
      `1px solid ${COLORS.border}`,
    borderRadius: "12px",
    minWidth: "850px",
  },

  detailGrid: {
    display: "grid",
    gridTemplateColumns:
      "repeat(auto-fit,minmax(155px,1fr))",
    gap: "1px",
    background: COLORS.border,
  },

  detail: {
    padding: "15px",
    background: "#fff",
  },

  detailLabel: {
    display: "block",
    color: COLORS.muted,
    fontSize: "16px",
    fontWeight: 700,
    marginBottom: "6px",
  },

  detailValue: {
    fontSize: "21px",
    fontWeight: 850,
    color: COLORS.royalDark,
  },

  reason: {
    margin: "15px",
    padding: "14px 16px",
    borderLeft:
      `4px solid ${COLORS.gold}`,
    borderRadius: "8px",
    background: COLORS.goldSoft,
    fontSize: "18px",
    lineHeight: 1.55,
  },

  empty: {
    padding: "24px",
    textAlign: "center",
    color: COLORS.muted,
    fontSize: "18px",
  },
};

function MultivariateAnalysis({
  datasetId,
  result,
  loading = false,
  error = "",
  onBack,
}) {
  const [
    recordFilter,
    setRecordFilter,
  ] = useState("all");

  const [
    selectedRecord,
    setSelectedRecord,
  ] = useState(null);

  const [
    visualizationMode,
    setVisualizationMode,
  ] = useState("mahalanobis");

  const [
    contributionExpanded,
    setContributionExpanded,
  ] = useState(false);

  const [
    contributionDetails,
    setContributionDetails,
  ] = useState(null);

  const [
    contributionLoading,
    setContributionLoading,
  ] = useState(false);

  const [
    contributionError,
    setContributionError,
  ] = useState("");

  const [
    selectedContributionFeature,
    setSelectedContributionFeature,
  ] = useState(null);

  const selectedRecordDetailsRef =
    useRef(null);

  const records =
    result?.records || [];

  const columns =
    result?.columns_involved || [];

  const summary =
    result || {};

  // --------------------------------------------------------------
  // Threshold
  // --------------------------------------------------------------

  const threshold =
    summary.threshold ??
    summary.mahalanobis_threshold;

  // --------------------------------------------------------------
  // Accuracy / evaluation information
  //
  // Accuracy is generated by the backend using a separate
  // controlled evaluation dataset with known injected anomalies.
  // --------------------------------------------------------------

  const accuracy =
    result?.accuracy !== null &&
    result?.accuracy !== undefined &&
    result?.accuracy !== ""
      ? Number(result.accuracy)
      : null;

  const evaluation =
    result?.evaluation || null;

  const evaluationTotal =
    evaluation?.total_records ??
    null;

  const evaluationTP =
    evaluation?.true_positive ??
    evaluation?.tp ??
    null;

  const evaluationTN =
    evaluation?.true_negative ??
    evaluation?.tn ??
    null;

  const evaluationFP =
    evaluation?.false_positive ??
    evaluation?.fp ??
    null;

  const evaluationFN =
    evaluation?.false_negative ??
    evaluation?.fn ??
    null;

  const injectedAnomalies =
    evaluation?.injected_anomalies ??
    evaluation?.number_of_injected_anomalies ??
    evaluation?.injected_anomaly_count ??
    null;

  const injectionPercentage =
    evaluation?.injection_percentage ??
    evaluation?.injected_percentage ??
    null;

  // --------------------------------------------------------------
  // Filtered records
  // --------------------------------------------------------------

  const filteredRecords =
    useMemo(() => {
      if (recordFilter === "anomaly") {
        return records.filter(
          (record) =>
            record.is_anomaly
        );
      }

      if (recordFilter === "normal") {
        return records.filter(
          (record) =>
            !record.is_anomaly
        );
      }

      return records;
    }, [
      records,
      recordFilter,
    ]);

  // --------------------------------------------------------------
  // Selected record
  // --------------------------------------------------------------

  const selectedRecordData =
    useMemo(() => {
      if (
        selectedRecord === null ||
        selectedRecord === undefined
      ) {
        return null;
      }

      return (
        records.find(
          (record) =>
            record.record_number ===
            selectedRecord
        ) || null
      );
    }, [
      records,
      selectedRecord,
    ]);

  useEffect(() => {
    if (
      !selectedRecordData ||
      !selectedRecordDetailsRef.current
    ) {
      return;
    }

    selectedRecordDetailsRef.current.scrollIntoView(
      {
        behavior: "smooth",
        block: "start",
      }
    );
  }, [selectedRecordData]);

  useEffect(() => {
    setContributionExpanded(false);
    setContributionDetails(null);
    setSelectedContributionFeature(null);
    setContributionError("");
  }, [selectedRecord]);

  // --------------------------------------------------------------
  // PDF
  // --------------------------------------------------------------

  const downloadGeneratedPdf = () => {
    const encoded =
      result?.pdf_base64;

    if (!encoded) {
      window.alert(
        "PDF report is not available. Please run the analysis again."
      );
      return;
    }

    try {
      const cleanBase64 =
        String(encoded).includes(",")
          ? String(encoded).split(",")[1]
          : String(encoded);

      const binary =
        window.atob(cleanBase64);

      const bytes =
        new Uint8Array(
          binary.length
        );

      for (
        let i = 0;
        i < binary.length;
        i += 1
      ) {
        bytes[i] =
          binary.charCodeAt(i);
      }

      const blob = new Blob(
        [bytes],
        {
          type: "application/pdf",
        }
      );

      const url =
        window.URL.createObjectURL(
          blob
        );

      const anchor =
        document.createElement("a");

      anchor.href = url;

      anchor.download =
        result?.pdf_filename ||
        "ANOMALY_Multivariate_Anomaly_Report.pdf";

      document.body.appendChild(
        anchor
      );

      anchor.click();

      anchor.remove();

      window.URL.revokeObjectURL(
        url
      );
    } catch (downloadError) {
      console.error(
        "PDF download failed:",
        downloadError
      );

      window.alert(
        "Unable to download the PDF report."
      );
    }
  };

  // --------------------------------------------------------------
  // Formatting
  // --------------------------------------------------------------

  const formatNumber = (
    value
  ) => {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "—";
    }

    if (
      typeof value === "number" &&
      Number.isFinite(value)
    ) {
      return value.toLocaleString(
        undefined,
        {
          maximumFractionDigits: 6,
        }
      );
    }

    return String(value);
  };

  const formatAccuracy = (
    value
  ) => {
    if (
      value === null ||
      value === undefined ||
      !Number.isFinite(
        Number(value)
      )
    ) {
      return "—";
    }

    return `${Number(value).toFixed(2)}%`;
  };

  // --------------------------------------------------------------
  // Mahalanobis score
  // --------------------------------------------------------------

  const getMahalanobisScore = (
    record
  ) => {
    if (!record) return null;

    if (
      record.mahalanobis_score !==
        undefined &&
      record.mahalanobis_score !== null
    ) {
      return record.mahalanobis_score;
    }

    if (
      record.mah_distance !==
        undefined &&
      record.mah_distance !== null
    ) {
      return record.mah_distance;
    }

    const explanation =
      record.explanation;

    if (
      explanation &&
      explanation.mahalanobis_score !==
        undefined &&
      explanation.mahalanobis_score !==
        null
    ) {
      return explanation.mahalanobis_score;
    }

    if (
      explanation &&
      explanation.score !==
        undefined &&
      explanation.score !== null
    ) {
      return explanation.score;
    }

    if (
      explanation &&
      explanation.distance !==
        undefined &&
      explanation.distance !== null
    ) {
      return explanation.distance;
    }

    if (
      record.score !==
        undefined &&
      record.score !== null
    ) {
      return record.score;
    }

    return null;
  };

  const getFeatureValue = (
    record,
    column
  ) => {
    if (!record) return "—";

    if (
      record.feature_values &&
      Object.prototype.hasOwnProperty.call(
        record.feature_values,
        column
      )
    ) {
      return record.feature_values[
        column
      ];
    }

    if (
      Object.prototype.hasOwnProperty.call(
        record,
        column
      )
    ) {
      return record[column];
    }

    return "—";
  };

  // --------------------------------------------------------------
  // Contribution helpers
  // --------------------------------------------------------------

  const getContributionList = (
    record
  ) => {
    if (!record) return [];

    if (
      Array.isArray(
        record.top_contributors
      )
    ) {
      return record.top_contributors;
    }

    if (
      Array.isArray(
        record.feature_contributions
      )
    ) {
      return record.feature_contributions.slice(
        0,
        3
      );
    }

    if (
      contributionDetails?.record_number ===
      record.record_number
    ) {
      return (
        contributionDetails.top_contributors ||
        contributionDetails.feature_contributions ||
        []
      );
    }

    return [];
  };

  const getAllContributionList =
    () => {
      if (!contributionDetails) {
        return [];
      }

      return (
        contributionDetails.all_feature_contributions ||
        contributionDetails.feature_contributions ||
        contributionDetails.target_feature_evidence ||
        []
      );
    };

  const handleExploreContributions =
    async () => {
      if (
        !datasetId ||
        !selectedRecordData?.is_anomaly
      ) {
        return;
      }

      setContributionExpanded(
        true
      );

      setContributionLoading(
        true
      );

      setContributionError("");

      setSelectedContributionFeature(
        null
      );

      try {
        const response =
          await fetch(
            `${(import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "")}/api/statistical/${encodeURIComponent(
              datasetId
            )}/multivariate/explain`,
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json",
              },
              body: JSON.stringify(
                {
                  record_number:
                    selectedRecordData.record_number,
                  top_n: 3,
                }
              ),
            }
          );

        let data = null;

        try {
          data =
            await response.json();
        } catch {
          data = null;
        }

        if (!response.ok) {
          throw new Error(
            data?.detail ||
              data?.message ||
              `Feature contribution request failed with status ${response.status}.`
          );
        }

        setContributionDetails(
          data
        );
      } catch (err) {
        setContributionError(
          err?.message ||
            "Unable to load feature contribution details."
        );
      } finally {
        setContributionLoading(
          false
        );
      }
    };

  const handleCloseContributionDetails =
    () => {
      setContributionExpanded(
        false
      );

      setContributionDetails(
        null
      );

      setSelectedContributionFeature(
        null
      );

      setContributionError("");
    };

  // --------------------------------------------------------------
  // Dynamic explanation
  // --------------------------------------------------------------

  const getDynamicExplanation = (
    record
  ) => {
    if (!record) return "";

    if (
      record.explanation?.interpretation
    ) {
      return record.explanation
        .interpretation;
    }

    if (record.interpretation) {
      return record.interpretation;
    }

    if (record.reason) {
      return record.reason;
    }

    const score = Number(
      getMahalanobisScore(record)
    );

    const recordThreshold =
      Number(
        record.threshold ??
          summary.threshold
      );

    if (
      Number.isFinite(score) &&
      Number.isFinite(
        recordThreshold
      )
    ) {
      if (
        score > recordThreshold
      ) {
        return `The Mahalanobis score of ${formatNumber(
          score
        )} is above the calculated threshold of ${formatNumber(
          recordThreshold
        )}.`;
      }

      return `The Mahalanobis score of ${formatNumber(
        score
      )} is within the calculated threshold of ${formatNumber(
        recordThreshold
      )}.`;
    }

    return record.is_anomaly
      ? "The Mahalanobis score exceeds the calculated threshold."
      : "The Mahalanobis score is within the calculated threshold.";
  };

  // --------------------------------------------------------------
  // Parallel coordinates chart
  // --------------------------------------------------------------

  const parallelChart =
    useMemo(() => {
      if (
        columns.length === 0 ||
        records.length === 0
      ) {
        return null;
      }

      const width = 1100;
      const height = 520;

      const margin = {
        top: 60,
        right: 45,
        bottom: 60,
        left: 45,
      };

      const innerWidth =
        width -
        margin.left -
        margin.right;

      const innerHeight =
        height -
        margin.top -
        margin.bottom;

      const axisStep =
        columns.length === 1
          ? 0
          : innerWidth /
            (columns.length - 1);

      const featureStats = {};

      columns.forEach(
        (column) => {
          const values =
            records
              .map(
                (record) =>
                  Number(
                    getFeatureValue(
                      record,
                      column
                    )
                  )
              )
              .filter(
                Number.isFinite
              );

          let min =
            values.length
              ? Math.min(...values)
              : 0;

          let max =
            values.length
              ? Math.max(...values)
              : 1;

          if (min === max) {
            min -= 1;
            max += 1;
          }

          featureStats[column] = {
            min,
            max,
          };
        }
      );

      const getAxisX = (
        index
      ) =>
        columns.length === 1
          ? margin.left +
            innerWidth / 2
          : margin.left +
            axisStep * index;

      const getNormalizedY = (
        column,
        value
      ) => {
        const stats =
          featureStats[column];

        const numericValue =
          Number(value);

        if (
          !Number.isFinite(
            numericValue
          )
        ) {
          return (
            margin.top +
            innerHeight / 2
          );
        }

        const ratio =
          (numericValue -
            stats.min) /
          (stats.max -
            stats.min);

        return (
          margin.top +
          (1 - ratio) *
            innerHeight
        );
      };

      const buildPoints = (
        record
      ) =>
        columns.map(
          (
            column,
            index
          ) => ({
            x: getAxisX(index),
            y: getNormalizedY(
              column,
              getFeatureValue(
                record,
                column
              )
            ),
          })
        );

      return {
        width,
        height,
        margin,
        featureStats,
        getAxisX,
        getNormalizedY,
        buildPoints,
      };
    }, [
      columns,
      records,
    ]);

  // --------------------------------------------------------------
  // Mahalanobis chart
  // --------------------------------------------------------------

  const mahalanobisChart =
    useMemo(() => {
      if (!records.length) {
        return null;
      }

      const width = 1100;
      const height = 500;

      const margin = {
        top: 55,
        right: 55,
        bottom: 65,
        left: 75,
      };

      const innerWidth =
        width -
        margin.left -
        margin.right;

      const innerHeight =
        height -
        margin.top -
        margin.bottom;

      const scoredRecords =
        filteredRecords
          .map((record) => ({
            record,
            score: Number(
              getMahalanobisScore(
                record
              )
            ),
          }))
          .filter(
            (item) =>
              Number.isFinite(
                item.score
              )
          );

      if (
        !scoredRecords.length
      ) {
        return null;
      }

      const thresholdValue =
        Number(threshold);

      const scoreValues =
        scoredRecords.map(
          (item) =>
            item.score
        );

      const maxScore =
        Math.max(
          ...scoreValues,
          Number.isFinite(
            thresholdValue
          )
            ? thresholdValue
            : 0
        );

      const minScore =
        Math.min(
          0,
          ...scoreValues
        );

      const range =
        maxScore - minScore > 0
          ? maxScore - minScore
          : 1;

      const xStep =
        scoredRecords.length === 1
          ? 0
          : innerWidth /
            (scoredRecords.length -
              1);

      const getX = (
        index
      ) =>
        scoredRecords.length === 1
          ? margin.left +
            innerWidth / 2
          : margin.left +
            xStep * index;

      const getY = (
        score
      ) =>
        margin.top +
        (1 -
          (score - minScore) /
            range) *
          innerHeight;

      const thresholdY =
        Number.isFinite(
          thresholdValue
        )
          ? getY(thresholdValue)
          : null;

      return {
        width,
        height,
        margin,
        scoredRecords,
        minScore,
        maxScore,
        getX,
        getY,
        thresholdY,
      };
    }, [
      records,
      filteredRecords,
      threshold,
    ]);

  const buildPath = (
    points
  ) => {
    if (!points?.length) {
      return "";
    }

    return points
      .map(
        (
          point,
          index
        ) =>
          `${
            index === 0
              ? "M"
              : "L"
          } ${point.x} ${point.y}`
      )
      .join(" ");
  };

  // --------------------------------------------------------------
  // Loading state
  // --------------------------------------------------------------

  if (loading) {
    return (
      <div style={styles.page}>
        <div
          style={{
            ...styles.section,
            padding: "45px",
            textAlign: "center",
          }}
        >
          <h2
            style={
              styles.sectionTitle
            }
          >
            Running Mahalanobis
            Analysis
          </h2>

          <p
            style={
              styles.sectionText
            }
          >
            Calculating multivariate
            anomaly scores and
            controlled evaluation
            accuracy.
          </p>
        </div>
      </div>
    );
  }

  // --------------------------------------------------------------
  // Error state
  // --------------------------------------------------------------

  if (error) {
    return (
      <div style={styles.page}>
        <div
          style={{
            ...styles.section,
            padding: "25px",
          }}
        >
          <h2
            style={{
              ...styles.sectionTitle,
              color: COLORS.red,
            }}
          >
            Unable to complete
            analysis
          </h2>

          <p
            style={
              styles.sectionText
            }
          >
            {error}
          </p>

          {onBack && (
            <button
              type="button"
              onClick={onBack}
              style={{
                ...styles.backButton,
                marginTop: "10px",
                background:
                  COLORS.royal,
              }}
            >
              ← Back
            </button>
          )}
        </div>
      </div>
    );
  }

  // --------------------------------------------------------------
  // Detection summary
  // --------------------------------------------------------------

  const anomalyCount =
    summary.anomaly_records ??
    records.filter(
      (record) =>
        record.is_anomaly
    ).length;

  const totalCount =
    summary.total_records ??
    records.length;

  const normalCount =
    summary.normal_records ??
    Math.max(
      0,
      totalCount -
        anomalyCount
    );

  const anomalyRate =
    summary.anomaly_percentage ??
    (totalCount
      ? (anomalyCount /
          totalCount) *
        100
      : 0);

  return (
    <div
      style={styles.page}
      className="multivariate-analysis-page"
    >
      <style>
        {`
          .royal-section:hover {
            transform: translateY(-1px);
            box-shadow: 0 13px 30px rgba(32,48,110,.12) !important;
          }

          .royal-row:hover td {
            background: #e9efff !important;
          }

          .royal-detail:hover {
            background: #f2f5ff !important;
          }

          .royal-line {
            transition: opacity .15s ease, stroke-width .15s ease;
          }

          .royal-line:hover {
            opacity: 1 !important;
            stroke-width: 4 !important;
          }

          .royal-banner-item:hover {
            background: #e9efff !important;
          }

          @media (max-width: 760px) {
            .multivariate-analysis-page {
              padding: 12px !important;
            }
          }
        `}
      </style>

      {/* ============================================================
          HEADER
          ============================================================ */}

      <header
        style={styles.header}
        className="royal-section"
      >
        <div>
          <h1
            style={
              styles.headerTitle
            }
          >
            Multivariate Analysis
          </h1>

          <p
            style={
              styles.headerText
            }
          >
            Mahalanobis Distance
            identifies records that
            are unusual when the
            selected features are
            considered together.
          </p>
        </div>

        {onBack && (
          <button
            type="button"
            onClick={onBack}
            style={
              styles.backButton
            }
          >
            ← Back
          </button>
        )}
      </header>

      {/* ============================================================
          METHOD / SUMMARY BANNER
          ============================================================ */}

      <div
        style={styles.banner}
      >
        <div
          style={styles.bannerItem}
          className="royal-banner-item"
        >
          <span
            style={styles.label}
          >
            Variability
          </span>

          <strong
            style={styles.value}
          >
            Multivariate
          </strong>
        </div>

        <div
          style={styles.bannerItem}
          className="royal-banner-item"
        >
          <span
            style={styles.label}
          >
            Method
          </span>

          <strong
            style={styles.value}
          >
            Mahalanobis Distance
          </strong>
        </div>

        <div
          style={styles.bannerItem}
          className="royal-banner-item"
        >
          <span
            style={styles.label}
          >
            Columns Involved
          </span>

          <strong
            style={styles.value}
          >
            {columns.length}
          </strong>
        </div>

        {datasetId && (
          <div
            style={styles.bannerItem}
            className="royal-banner-item"
          >
            <span
              style={styles.label}
            >
              Dataset
            </span>

            <strong
              style={styles.value}
            >
              {datasetId}
            </strong>
          </div>
        )}

        {/* ==========================================================
            ACCURACY
            ========================================================== */}

        <div
          style={{
            ...styles.bannerItem,
            background:
              accuracy !== null
                ? "#edf8f3"
                : "#f1f5ff",
          }}
          className="royal-banner-item"
        >
          <span
            style={styles.label}
          >
            Accuracy
          </span>

          <strong
            style={{
              ...styles.value,
              color:
                accuracy !== null
                  ? COLORS.green
                  : COLORS.royalDark,
            }}
          >
            {formatAccuracy(
              accuracy
            )}
          </strong>
        </div>
      </div>

      {/* ============================================================
          CONTROLLED EVALUATION DETAILS
          ============================================================ */}

      {evaluation && (
        <section
          style={{
            ...styles.section,
            borderTop:
              `4px solid ${COLORS.green}`,
          }}
          className="royal-section"
        >
          <div
            style={styles.sectionHeader}
          >
            <div>
              <h2
                style={
                  styles.sectionTitle
                }
              >
                Accuracy Evaluation
              </h2>

              <p
                style={
                  styles.sectionText
                }
              >
                Accuracy is calculated by
                comparing the Mahalanobis
                detector predictions with
                controlled, statistically
                injected anomaly labels.
              </p>
            </div>

            <span
              style={{
                ...styles.normal,
                fontSize: "18px",
                padding:
                  "7px 13px",
              }}
            >
              {formatAccuracy(
                accuracy
              )}
            </span>
          </div>

          <div
            style={
              styles.detailGrid
            }
          >
            <div
              style={styles.detail}
              className="royal-detail"
            >
              <span
                style={
                  styles.detailLabel
                }
              >
                Evaluation Records
              </span>

              <strong
                style={
                  styles.detailValue
                }
              >
                {formatNumber(
                  evaluationTotal
                )}
              </strong>
            </div>

            <div
              style={styles.detail}
              className="royal-detail"
            >
              <span
                style={
                  styles.detailLabel
                }
              >
                Injected Anomalies
              </span>

              <strong
                style={{
                  ...styles.detailValue,
                  color:
                    COLORS.red,
                }}
              >
                {formatNumber(
                  injectedAnomalies
                )}
              </strong>
            </div>

            {injectionPercentage !==
              null &&
              injectionPercentage !==
                undefined && (
                <div
                  style={
                    styles.detail
                  }
                  className="royal-detail"
                >
                  <span
                    style={
                      styles.detailLabel
                    }
                  >
                    Injection Rate
                  </span>

                  <strong
                    style={
                      styles.detailValue
                    }
                  >
                    {formatNumber(
                      injectionPercentage
                    )}
                    %
                  </strong>
                </div>
              )}

            <div
              style={styles.detail}
              className="royal-detail"
            >
              <span
                style={
                  styles.detailLabel
                }
              >
                True Positive
              </span>

              <strong
                style={{
                  ...styles.detailValue,
                  color:
                    COLORS.green,
                }}
              >
                {formatNumber(
                  evaluationTP
                )}
              </strong>
            </div>

            <div
              style={styles.detail}
              className="royal-detail"
            >
              <span
                style={
                  styles.detailLabel
                }
              >
                True Negative
              </span>

              <strong
                style={{
                  ...styles.detailValue,
                  color:
                    COLORS.green,
                }}
              >
                {formatNumber(
                  evaluationTN
                )}
              </strong>
            </div>

            <div
              style={styles.detail}
              className="royal-detail"
            >
              <span
                style={
                  styles.detailLabel
                }
              >
                False Positive
              </span>

              <strong
                style={{
                  ...styles.detailValue,
                  color:
                    COLORS.red,
                }}
              >
                {formatNumber(
                  evaluationFP
                )}
              </strong>
            </div>

            <div
              style={styles.detail}
              className="royal-detail"
            >
              <span
                style={
                  styles.detailLabel
                }
              >
                False Negative
              </span>

              <strong
                style={{
                  ...styles.detailValue,
                  color:
                    COLORS.red,
                }}
              >
                {formatNumber(
                  evaluationFN
                )}
              </strong>
            </div>
          </div>

          <div
            style={{
              ...styles.reason,
              borderLeft:
                `4px solid ${COLORS.green}`,
              background:
                COLORS.greenSoft,
            }}
          >
            <strong>
              Evaluation Method
            </strong>

            <div
              style={{
                marginTop: "6px",
              }}
            >
              The original dataset is not
              assumed to contain ground-truth
              anomaly labels. A separate
              evaluation copy is created and
              approximately 5% of observations
              are statistically perturbed using
              robust feature scales. The
              standard Mahalanobis detector is
              then applied independently to that
              evaluation copy, and its predictions
              are compared with the known injected
              labels.
            </div>
          </div>
        </section>
      )}

      {/* ============================================================
          REPORT
          ============================================================ */}

      <section
        style={styles.section}
        className="royal-section"
      >
        <div
          style={
            styles.sectionHeader
          }
        >
          <div>
            <h2
              style={
                styles.sectionTitle
              }
            >
              Multivariate Anomaly
              Detection Report
            </h2>

            <p
              style={
                styles.sectionText
              }
            >
              Download the A4 report
              containing anomaly records,
              all feature values, threshold,
              Mahalanobis score, and a
              data-driven Top 3 Feature
              Contributions table.
              Normal records are not included.
            </p>
          </div>

          <button
            type="button"
            style={{
              ...styles.exploreButton,
              opacity:
                result?.pdf_base64
                  ? 1
                  : 0.6,
            }}
            onClick={
              downloadGeneratedPdf
            }
            disabled={
              !result?.pdf_base64
            }
          >
            {result?.pdf_base64
              ? "Download PDF Report"
              : "PDF Preparing..."}
          </button>
        </div>
      </section>

      {/* ============================================================
          DETECTION SUMMARY
          ============================================================ */}

      <section
        style={styles.section}
        className="royal-section"
      >
        <div
          style={
            styles.sectionHeader
          }
        >
          <div>
            <h2
              style={
                styles.sectionTitle
              }
            >
              Detection Summary
            </h2>

            <p
              style={
                styles.sectionText
              }
            >
              All selected features are
              evaluated together using
              Mahalanobis Distance.
            </p>
          </div>
        </div>

        <div
          style={styles.tableWrap}
        >
          <table
            style={styles.table}
          >
            <tbody>
              <tr className="royal-row">
                <th
                  style={styles.th}
                >
                  Total Records
                </th>

                <td
                  style={{
                    ...styles.td,
                    background:
                      "#eef3ff",
                  }}
                >
                  <strong>
                    {totalCount}
                  </strong>
                </td>

                <th
                  style={styles.th}
                >
                  Anomaly Records
                </th>

                <td
                  style={{
                    ...styles.td,
                    background:
                      "#eef3ff",
                  }}
                >
                  <strong
                    style={{
                      color:
                        COLORS.red,
                    }}
                  >
                    {anomalyCount}
                  </strong>
                </td>

                <th
                  style={styles.th}
                >
                  Normal Records
                </th>

                <td
                  style={{
                    ...styles.td,
                    background:
                      "#eef3ff",
                  }}
                >
                  <strong
                    style={{
                      color:
                        COLORS.green,
                    }}
                  >
                    {normalCount}
                  </strong>
                </td>
              </tr>

              <tr className="royal-row">
                <th
                  style={styles.th}
                >
                  Anomaly Rate
                </th>

                <td
                  style={{
                    ...styles.td,
                    background:
                      "#eef3ff",
                  }}
                >
                  <strong>
                    {formatNumber(
                      anomalyRate
                    )}
                    %
                  </strong>
                </td>

                <th
                  style={styles.th}
                >
                  Accuracy
                </th>

                <td
                  style={{
                    ...styles.td,
                    background:
                      "#edf8f3",
                  }}
                >
                  <strong
                    style={{
                      color:
                        COLORS.green,
                    }}
                  >
                    {formatAccuracy(
                      accuracy
                    )}
                  </strong>
                </td>

                <th
                  style={styles.th}
                >
                  Threshold
                </th>

                <td
                  style={{
                    ...styles.td,
                    background:
                      "#eef3ff",
                  }}
                >
                  <strong
                    style={{
                      color:
                        COLORS.gold,
                    }}
                  >
                    {formatNumber(
                      threshold
                    )}
                  </strong>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* ============================================================
          RECORD EXPLORATION
          ============================================================ */}

      <section
        style={styles.section}
        className="royal-section"
      >
        <div
          style={
            styles.sectionHeader
          }
        >
          <div>
            <h2
              style={
                styles.sectionTitle
              }
            >
              Explore Records
            </h2>

            <p
              style={
                styles.sectionText
              }
            >
              Each record receives one
              Mahalanobis score.
            </p>
          </div>

          <select
            value={recordFilter}
            onChange={(event) => {
              setRecordFilter(
                event.target.value
              );

              setSelectedRecord(
                null
              );
            }}
            style={styles.filter}
          >
            <option value="all">
              View all records
            </option>

            <option value="anomaly">
              View only anomaly
            </option>

            <option value="normal">
              View only normal
            </option>
          </select>
        </div>

        <div
          style={
            styles.recordsTableWrap
          }
        >
          <table
            style={styles.table}
          >
            <thead>
              <tr>
                <th
                  style={styles.th}
                >
                  Record
                </th>

                {columns.map(
                  (column) => (
                    <th
                      key={column}
                      style={styles.th}
                    >
                      {column}
                    </th>
                  )
                )}

                <th
                  style={styles.th}
                >
                  Mahalanobis Score
                </th>

                <th
                  style={styles.th}
                >
                  Threshold
                </th>

                <th
                  style={styles.th}
                >
                  Status
                </th>

                <th
                  style={styles.th}
                >
                  Explore
                </th>
              </tr>
            </thead>

            <tbody>
              {filteredRecords.map(
                (record) => {
                  const selected =
                    selectedRecord ===
                    record.record_number;

                  const mahalanobisScore =
                    getMahalanobisScore(
                      record
                    );

                  return (
                    <tr
                      key={
                        record.record_number
                      }
                      className="royal-row"
                      style={{
                        background:
                          selected
                            ? "#eef1ff"
                            : "#f1f5ff",
                      }}
                    >
                      <td
                        style={
                          styles.td
                        }
                      >
                        <button
                          type="button"
                          onClick={() =>
                            setSelectedRecord(
                              record.record_number
                            )
                          }
                          style={{
                            border:
                              "none",
                            background:
                              "transparent",
                            color:
                              COLORS.royal,
                            fontWeight:
                              850,
                            fontSize:
                              "18px",
                            cursor:
                              "pointer",
                          }}
                        >
                          #
                          {
                            record.record_number
                          }
                        </button>
                      </td>

                      {columns.map(
                        (column) => (
                          <td
                            key={column}
                            style={
                              styles.td
                            }
                          >
                            {formatNumber(
                              getFeatureValue(
                                record,
                                column
                              )
                            )}
                          </td>
                        )
                      )}

                      <td
                        style={
                          styles.td
                        }
                      >
                        <span
                          style={
                            styles.score
                          }
                        >
                          {formatNumber(
                            mahalanobisScore
                          )}
                        </span>
                      </td>

                      <td
                        style={
                          styles.td
                        }
                      >
                        {formatNumber(
                          record.threshold ??
                            threshold
                        )}
                      </td>

                      <td
                        style={
                          styles.td
                        }
                      >
                        <span
                          style={
                            record.is_anomaly
                              ? styles.anomaly
                              : styles.normal
                          }
                        >
                          {record.status ||
                            (record.is_anomaly
                              ? "Anomaly"
                              : "Normal")}
                        </span>
                      </td>

                      <td
                        style={
                          styles.td
                        }
                      >
                        <button
                          type="button"
                          onClick={() =>
                            setSelectedRecord(
                              record.record_number
                            )
                          }
                          style={
                            styles.exploreButton
                          }
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  );
                }
              )}
            </tbody>
          </table>
        </div>

        {!filteredRecords.length && (
          <div
            style={styles.empty}
          >
            No records match the
            selected filter.
          </div>
        )}
      </section>

      {/* ============================================================
          MULTIVARIATE VISUALIZATION
          ============================================================ */}

      <section
        style={styles.section}
        className="royal-section"
      >
        <div
          style={
            styles.sectionHeader
          }
        >
          <div>
            <h2
              style={
                styles.sectionTitle
              }
            >
              Multivariate
              Visualization
            </h2>

            <p
              style={
                styles.sectionText
              }
            >
              {visualizationMode ===
              "mahalanobis"
                ? "Mahalanobis Plot displays the actual distance of each record against the calculated statistical threshold. Click a point to inspect that record."
                : "Parallel coordinates show all selected features together. Click a record line to inspect the same record."}
            </p>
          </div>

          <select
            value={
              visualizationMode
            }
            onChange={(event) => {
              setVisualizationMode(
                event.target.value
              );
            }}
            style={styles.filter}
            aria-label="Select multivariate visualization"
          >
            <option value="mahalanobis">
              Mahalanobis Plot
            </option>

            <option value="parallel">
              Parallel Coordinates
            </option>
          </select>
        </div>

        {visualizationMode ===
        "mahalanobis" ? (
          mahalanobisChart ? (
            <div
              style={
                styles.chartBox
              }
            >
              <div
                style={
                  styles.innerChart
                }
              >
                <svg
                  viewBox={`0 0 ${mahalanobisChart.width} ${mahalanobisChart.height}`}
                  width="100%"
                  role="img"
                  aria-label="Mahalanobis distance plot"
                >
                  <line
                    x1={
                      mahalanobisChart
                        .margin
                        .left
                    }
                    x2={
                      mahalanobisChart.width -
                      mahalanobisChart
                        .margin
                        .right
                    }
                    y1={
                      mahalanobisChart.height -
                      mahalanobisChart
                        .margin
                        .bottom
                    }
                    y2={
                      mahalanobisChart.height -
                      mahalanobisChart
                        .margin
                        .bottom
                    }
                    stroke="#8b96b5"
                    strokeWidth="1.5"
                  />

                  <line
                    x1={
                      mahalanobisChart
                        .margin
                        .left
                    }
                    x2={
                      mahalanobisChart
                        .margin
                        .left
                    }
                    y1={
                      mahalanobisChart
                        .margin
                        .top
                    }
                    y2={
                      mahalanobisChart.height -
                      mahalanobisChart
                        .margin
                        .bottom
                    }
                    stroke="#8b96b5"
                    strokeWidth="1.5"
                  />

                  <text
                    x={
                      mahalanobisChart
                        .margin
                        .left
                    }
                    y="28"
                    textAnchor="start"
                    fontSize="18"
                    fontWeight="800"
                    fill={
                      COLORS.royalDark
                    }
                  >
                    Mahalanobis Plot
                  </text>

                  <text
                    x={
                      mahalanobisChart
                        .margin
                        .left +
                      (mahalanobisChart.width -
                        mahalanobisChart
                          .margin
                          .left -
                        mahalanobisChart
                          .margin
                          .right) /
                        2
                    }
                    y={
                      mahalanobisChart.height -
                      12
                    }
                    textAnchor="middle"
                    fontSize="14"
                    fontWeight="700"
                    fill="#6b7691"
                  >
                    Record Number
                  </text>

                  <text
                    x="20"
                    y={
                      mahalanobisChart
                        .margin
                        .top +
                      (mahalanobisChart.height -
                        mahalanobisChart
                          .margin
                          .top -
                        mahalanobisChart
                          .margin
                          .bottom) /
                        2
                    }
                    textAnchor="middle"
                    fontSize="14"
                    fontWeight="700"
                    fill="#6b7691"
                    transform={`rotate(-90 20 ${
                      mahalanobisChart
                        .margin
                        .top +
                      (mahalanobisChart.height -
                        mahalanobisChart
                          .margin
                          .top -
                        mahalanobisChart
                          .margin
                          .bottom) /
                        2
                    })`}
                  >
                    Mahalanobis Score
                  </text>

                  {mahalanobisChart.thresholdY !==
                    null && (
                    <>
                      <line
                        x1={
                          mahalanobisChart
                            .margin
                            .left
                        }
                        x2={
                          mahalanobisChart.width -
                          mahalanobisChart
                            .margin
                            .right
                        }
                        y1={
                          mahalanobisChart
                            .thresholdY
                        }
                        y2={
                          mahalanobisChart
                            .thresholdY
                        }
                        stroke={
                          COLORS.gold
                        }
                        strokeWidth="2.5"
                        strokeDasharray="8 6"
                      />

                      <text
                        x={
                          mahalanobisChart.width -
                          mahalanobisChart
                            .margin
                            .right
                        }
                        y={
                          mahalanobisChart
                            .thresholdY -
                          8
                        }
                        textAnchor="end"
                        fontSize="14"
                        fontWeight="800"
                        fill={
                          COLORS.gold
                        }
                      >
                        Threshold:{" "}
                        {formatNumber(
                          threshold
                        )}
                      </text>
                    </>
                  )}

                  {mahalanobisChart.scoredRecords.map(
                    ({
                      record,
                      score,
                    }) => {
                      const selected =
                        selectedRecord ===
                        record.record_number;

                      const x =
                        mahalanobisChart.getX(
                          mahalanobisChart.scoredRecords.findIndex(
                            (item) =>
                              item.record.record_number ===
                              record.record_number
                          )
                        );

                      const y =
                        mahalanobisChart.getY(
                          score
                        );

                      return (
                        <g
                          key={`mah-point-${record.record_number}`}
                          style={{
                            cursor:
                              "pointer",
                          }}
                          onClick={() =>
                            setSelectedRecord(
                              record.record_number
                            )
                          }
                        >
                          <circle
                            cx={x}
                            cy={y}
                            r={
                              selected
                                ? 8
                                : 5
                            }
                            fill={
                              record.is_anomaly
                                ? COLORS.red
                                : COLORS.blue
                            }
                            stroke={
                              selected
                                ? "#17255f"
                                : "#fff"
                            }
                            strokeWidth={
                              selected
                                ? 3
                                : 1.5
                            }
                          />

                          <title>
                            {`Record ${record.record_number} | ${record.status} | Mahalanobis Score: ${formatNumber(
                              score
                            )}${
                              Number.isFinite(
                                Number(
                                  threshold
                                )
                              )
                                ? ` | Threshold: ${formatNumber(
                                    threshold
                                  )}`
                                : ""
                            }`}
                          </title>
                        </g>
                      );
                    }
                  )}
                </svg>
              </div>

              <div
                style={{
                  display:
                    "flex",
                  gap: "22px",
                  flexWrap:
                    "wrap",
                  marginTop:
                    "11px",
                  fontSize:
                    "17px",
                  fontWeight: 700,
                }}
              >
                <span>
                  <span
                    style={{
                      color:
                        COLORS.blue,
                    }}
                  >
                    ●
                  </span>{" "}
                  Normal
                </span>

                <span>
                  <span
                    style={{
                      color:
                        COLORS.red,
                    }}
                  >
                    ●
                  </span>{" "}
                  Anomaly
                </span>

                <span
                  style={{
                    color:
                      COLORS.gold,
                  }}
                >
                  ┄ Threshold
                </span>

                <span
                  style={{
                    color:
                      COLORS.royal,
                  }}
                >
                  Click a point
                  to inspect
                </span>
              </div>
            </div>
          ) : (
            <div
              style={
                styles.empty
              }
            >
              No Mahalanobis
              scores are
              available for
              visualization.
            </div>
          )
        ) : parallelChart ? (
          <div
            style={
              styles.chartBox
            }
          >
            <div
              style={
                styles.innerChart
              }
            >
              <svg
                viewBox={`0 0 ${parallelChart.width} ${parallelChart.height}`}
                width="100%"
                role="img"
                aria-label="Mahalanobis parallel coordinates visualization"
              >
                {columns.map(
                  (
                    column,
                    index
                  ) => {
                    const x =
                      parallelChart.getAxisX(
                        index
                      );

                    const stats =
                      parallelChart
                        .featureStats[
                        column
                      ];

                    return (
                      <g
                        key={
                          column
                        }
                      >
                        <line
                          x1={x}
                          x2={x}
                          y1={
                            parallelChart
                              .margin
                              .top
                          }
                          y2={
                            parallelChart.height -
                            parallelChart
                              .margin
                              .bottom
                          }
                          stroke="#8b96b5"
                          strokeWidth="1.5"
                        />

                        <text
                          x={x}
                          y="27"
                          textAnchor="middle"
                          fontSize="16"
                          fontWeight="800"
                          fill={
                            COLORS.royalDark
                          }
                        >
                          {column}
                        </text>

                        <text
                          x={x}
                          y={
                            parallelChart
                              .margin
                              .top -
                            5
                          }
                          textAnchor="middle"
                          fontSize="14"
                          fill="#6b7691"
                        >
                          {formatNumber(
                            stats.max
                          )}
                        </text>

                        <text
                          x={x}
                          y={
                            parallelChart.height -
                            parallelChart
                              .margin
                              .bottom +
                            18
                          }
                          textAnchor="middle"
                          fontSize="14"
                          fill="#6b7691"
                        >
                          {formatNumber(
                            stats.min
                          )}
                        </text>
                      </g>
                    );
                  }
                )}

                {records.map(
                  (record) => {
                    const points =
                      parallelChart.buildPoints(
                        record
                      );

                    const selected =
                      selectedRecord ===
                      record.record_number;

                    const mahalanobisScore =
                      getMahalanobisScore(
                        record
                      );

                    return (
                      <path
                        key={`record-${record.record_number}`}
                        className="royal-line"
                        d={buildPath(
                          points
                        )}
                        fill="none"
                        stroke={
                          record.is_anomaly
                            ? COLORS.red
                            : COLORS.blue
                        }
                        strokeWidth={
                          selected
                            ? 4
                            : record.is_anomaly
                              ? 2.5
                              : 1.1
                        }
                        opacity={
                          selected
                            ? 1
                            : record.is_anomaly
                              ? 0.82
                              : 0.24
                        }
                        style={{
                          cursor:
                            "pointer",
                        }}
                        onClick={() =>
                          setSelectedRecord(
                            record.record_number
                          )
                        }
                      >
                        <title>
                          {`Record ${record.record_number} | ${record.status} | Mahalanobis Score: ${formatNumber(
                            mahalanobisScore
                          )}`}
                        </title>
                      </path>
                    );
                  }
                )}
              </svg>
            </div>

            <div
              style={{
                display:
                  "flex",
                gap: "22px",
                flexWrap:
                  "wrap",
                marginTop:
                  "11px",
                fontSize:
                  "17px",
                fontWeight: 700,
              }}
            >
              <span>
                <span
                  style={{
                    color:
                      COLORS.blue,
                  }}
                >
                  ●
                </span>{" "}
                Normal
              </span>

              <span>
                <span
                  style={{
                    color:
                      COLORS.red,
                  }}
                >
                  ●
                </span>{" "}
                Anomaly
              </span>

              <span
                style={{
                  color:
                    COLORS.gold,
                }}
              >
                Click a line
                to inspect
              </span>
            </div>
          </div>
        ) : (
          <div
            style={
              styles.empty
            }
          >
            No records or
            features are available
            for visualization.
          </div>
        )}
      </section>

      {/* ============================================================
          SELECTED RECORD
          ============================================================ */}

      {selectedRecordData && (
        <section
          ref={
            selectedRecordDetailsRef
          }
          style={{
            ...styles.section,
            borderTop:
              `4px solid ${
                selectedRecordData.is_anomaly
                  ? COLORS.red
                  : COLORS.gold
              }`,
          }}
          className="royal-section"
        >
          <div
            style={
              styles.sectionHeader
            }
          >
            <div>
              <h2
                style={
                  styles.sectionTitle
                }
              >
                Record Details
              </h2>

              <p
                style={
                  styles.sectionText
                }
              >
                Record #
                {
                  selectedRecordData.record_number
                }
              </p>
            </div>

            <span
              style={
                selectedRecordData.is_anomaly
                  ? styles.anomaly
                  : styles.normal
              }
            >
              {selectedRecordData.status ||
                (selectedRecordData.is_anomaly
                  ? "Anomaly"
                  : "Normal")}
            </span>
          </div>

          <div
            style={{
              ...styles.detailGrid,
              margin: "0",
            }}
          >
            <div
              style={styles.detail}
              className="royal-detail"
            >
              <span
                style={
                  styles.detailLabel
                }
              >
                Record Number
              </span>

              <strong
                style={
                  styles.detailValue
                }
              >
                {
                  selectedRecordData.record_number
                }
              </strong>
            </div>

            <div
              style={styles.detail}
              className="royal-detail"
            >
              <span
                style={
                  styles.detailLabel
                }
              >
                Mahalanobis Score
              </span>

              <strong
                style={{
                  ...styles.detailValue,
                  color:
                    COLORS.royal,
                }}
              >
                {formatNumber(
                  getMahalanobisScore(
                    selectedRecordData
                  )
                )}
              </strong>
            </div>

            <div
              style={styles.detail}
              className="royal-detail"
            >
              <span
                style={
                  styles.detailLabel
                }
              >
                Threshold
              </span>

              <strong
                style={{
                  ...styles.detailValue,
                  color:
                    COLORS.gold,
                }}
              >
                {formatNumber(
                  selectedRecordData.threshold ??
                    threshold
                )}
              </strong>
            </div>

            <div
              style={styles.detail}
              className="royal-detail"
            >
              <span
                style={
                  styles.detailLabel
                }
              >
                Status
              </span>

              <strong
                style={
                  styles.detailValue
                }
              >
                {selectedRecordData.status ||
                  "—"}
              </strong>
            </div>
          </div>

          {/* ========================================================
              ACTUAL FEATURE VALUES
              ======================================================== */}

          <div
            style={{
              padding: "16px",
              borderTop:
                `1px solid ${COLORS.border}`,
            }}
          >
            <h3
              style={{
                margin:
                  "0 0 11px",
                color:
                  COLORS.royalDark,
                fontSize:
                  "20px",
              }}
            >
              Actual Feature
              Values
            </h3>

            <div
              style={
                styles.tableWrap
              }
            >
              <table
                style={
                  styles.table
                }
              >
                <thead>
                  <tr>
                    <th
                      style={
                        styles.th
                      }
                    >
                      Feature
                    </th>

                    <th
                      style={
                        styles.th
                      }
                    >
                      Actual Value
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {columns.map(
                    (column) => (
                      <tr
                        key={column}
                        className="royal-row"
                      >
                        <td
                          style={
                            styles.td
                          }
                        >
                          <strong>
                            {column}
                          </strong>
                        </td>

                        <td
                          style={
                            styles.td
                          }
                        >
                          {formatNumber(
                            getFeatureValue(
                              selectedRecordData,
                              column
                            )
                          )}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* ========================================================
              INTERPRETATION
              ======================================================== */}

          <div
            style={
              styles.reason
            }
          >
            <strong>
              Interpretation
            </strong>

            <div
              style={{
                marginTop:
                  "5px",
              }}
            >
              {getDynamicExplanation(
                selectedRecordData
              )}
            </div>
          </div>

          {/* ========================================================
              TOP CONTRIBUTING ATTRIBUTES
              ======================================================== */}

          {selectedRecordData.is_anomaly && (
            <div
              style={{
                padding:
                  "0 16px 16px",
              }}
            >
              <div
                style={{
                  display:
                    "flex",
                  alignItems:
                    "center",
                  justifyContent:
                    "space-between",
                  gap: "12px",
                  margin:
                    "8px 0 10px",
                }}
              >
                <div>
                  <h3
                    style={{
                      margin: 0,
                      color:
                        COLORS.royalDark,
                      fontSize:
                        "20px",
                    }}
                  >
                    Top 3
                    Contributing
                    Attributes
                  </h3>

                  <p
                    style={{
                      margin:
                        "4px 0 0",
                      color:
                        COLORS.muted,
                      fontSize:
                        "15px",
                    }}
                  >
                    Highest
                    covariance-adjusted
                    contributions
                    to this
                    record's
                    Mahalanobis
                    score.
                  </p>
                </div>

                <button
                  type="button"
                  style={
                    styles.exploreButton
                  }
                  onClick={
                    contributionExpanded
                      ? handleCloseContributionDetails
                      : handleExploreContributions
                  }
                  disabled={
                    contributionLoading
                  }
                >
                  {contributionLoading
                    ? "Loading..."
                    : contributionExpanded
                      ? "Close"
                      : "Explore"}
                </button>
              </div>

              {getContributionList(
                selectedRecordData
              ).length === 0 ? (
                <div
                  style={
                    styles.empty
                  }
                />
              ) : (
                <div
                  style={
                    styles.tableWrap
                  }
                >
                  <table
                    style={
                      styles.table
                    }
                  >
                    <tbody>
                      {getContributionList(
                        selectedRecordData
                      )
                        .slice(
                          0,
                          3
                        )
                        .map(
                          (
                            contribution,
                            index
                          ) => (
                            <tr
                              key={
                                contribution.feature_name ||
                                contribution.feature ||
                                index
                              }
                              className="royal-row"
                            >
                              <td
                                style={{
                                  ...styles.td,
                                  width:
                                    "55px",
                                }}
                              >
                                <strong>
                                  {String(
                                    contribution.rank ??
                                      index +
                                        1
                                  ).padStart(
                                    2,
                                    "0"
                                  )}
                                </strong>
                              </td>

                              <td
                                style={
                                  styles.td
                                }
                              >
                                <strong>
                                  {contribution.feature_name ||
                                    contribution.feature}
                                </strong>
                              </td>

                              <td
                                style={{
                                  ...styles.td,
                                  textAlign:
                                    "right",
                                  fontWeight:
                                    850,
                                  color:
                                    COLORS.royal,
                                }}
                              >
                                {formatNumber(
                                  contribution.contribution_percentage ??
                                    contribution.percentage
                                )}
                                %
                              </td>
                            </tr>
                          )
                        )}
                    </tbody>
                  </table>
                </div>
              )}

              {contributionExpanded && (
                <div
                  style={{
                    marginTop:
                      "12px",
                  }}
                >
                  {contributionError && (
                    <div
                      style={{
                        ...styles.reason,
                        margin:
                          "0 0 12px",
                        borderLeft:
                          `4px solid ${COLORS.red}`,
                        background:
                          COLORS.redSoft,
                      }}
                    >
                      {
                        contributionError
                      }
                    </div>
                  )}

                  {contributionLoading && (
                    <div
                      style={
                        styles.empty
                      }
                    >
                      Calculating the
                      complete
                      covariance-adjusted
                      feature
                      contribution
                      breakdown...
                    </div>
                  )}

                  {!contributionLoading &&
                    !contributionError &&
                    contributionDetails && (
                      <div
                        style={
                          styles.contributionCard
                        }
                      >
                        <div
                          style={{
                            padding:
                              "12px 14px",
                            borderBottom:
                              `1px solid ${COLORS.border}`,
                            background:
                              "#f1f5ff",
                          }}
                        >
                          <strong
                            style={{
                              color:
                                COLORS.royalDark,
                              fontSize:
                                "17px",
                            }}
                          >
                            All Feature
                            Contributions
                          </strong>

                          <div
                            style={{
                              marginTop:
                                "4px",
                              color:
                                COLORS.muted,
                              fontSize:
                                "14px",
                            }}
                          >
                            Percentages
                            are based
                            on absolute
                            feature
                            contribution
                            magnitude.
                            Signed terms
                            can be
                            negative
                            because of
                            covariance
                            relationships.
                          </div>
                        </div>

                        <div
                          style={
                            styles.tableWrap
                          }
                        >
                          <table
                            style={
                              styles.table
                            }
                          >
                            <thead>
                              <tr>
                                <th
                                  style={
                                    styles.th
                                  }
                                >
                                  Rank
                                </th>

                                <th
                                  style={
                                    styles.th
                                  }
                                >
                                  Feature
                                </th>

                                <th
                                  style={
                                    styles.th
                                  }
                                >
                                  Contribution %
                                </th>

                                <th
                                  style={
                                    styles.th
                                  }
                                >
                                  Action
                                </th>
                              </tr>
                            </thead>

                            <tbody>
                              {getAllContributionList().map(
                                (
                                  item,
                                  index
                                ) => (
                                  <tr
                                    key={
                                      item.feature_name ||
                                      item.feature ||
                                      index
                                    }
                                    className="royal-row"
                                  >
                                    <td
                                      style={
                                        styles.td
                                      }
                                    >
                                      {String(
                                        item.rank ??
                                          index +
                                            1
                                      ).padStart(
                                        2,
                                        "0"
                                      )}
                                    </td>

                                    <td
                                      style={
                                        styles.td
                                      }
                                    >
                                      <strong>
                                        {item.feature_name ||
                                          item.feature ||
                                          item.label}
                                      </strong>
                                    </td>

                                    <td
                                      style={{
                                        ...styles.td,
                                        fontWeight:
                                          850,
                                        color:
                                          COLORS.royal,
                                      }}
                                    >
                                      {formatNumber(
                                        item.contribution_percentage ??
                                          item.contribution_percent ??
                                          item.percentage
                                      )}
                                      %
                                    </td>

                                    <td
                                      style={
                                        styles.td
                                      }
                                    >
                                      <button
                                        type="button"
                                        style={
                                          styles.smallViewButton
                                        }
                                        onClick={() =>
                                          setSelectedContributionFeature(
                                            item
                                          )
                                        }
                                      >
                                        View
                                      </button>
                                    </td>
                                  </tr>
                                )
                              )}
                            </tbody>
                          </table>
                        </div>

                        {selectedContributionFeature && (
                          <div
                            style={
                              styles.contributionDetail
                            }
                          >
                            <div
                              style={{
                                display:
                                  "flex",
                                justifyContent:
                                  "space-between",
                                alignItems:
                                  "center",
                                gap: "10px",
                                marginBottom:
                                  "10px",
                              }}
                            >
                              <div>
                                <strong
                                  style={{
                                    color:
                                      COLORS.royalDark,
                                    fontSize:
                                      "18px",
                                  }}
                                >
                                  {selectedContributionFeature.feature_name ||
                                    selectedContributionFeature.feature ||
                                    selectedContributionFeature.label}
                                </strong>

                                <div
                                  style={{
                                    marginTop:
                                      "3px",
                                    color:
                                      COLORS.muted,
                                    fontSize:
                                      "14px",
                                  }}
                                >
                                  Detailed
                                  Mahalanobis
                                  contribution
                                  calculation
                                </div>
                              </div>

                              <span
                                style={{
                                  color:
                                    COLORS.royal,
                                  fontWeight:
                                    850,
                                  fontSize:
                                    "17px",
                                }}
                              >
                                {formatNumber(
                                  selectedContributionFeature.contribution_percentage ??
                                    selectedContributionFeature.contribution_percent
                                )}
                                %
                              </span>
                            </div>

                            <div
                              style={{
                                display:
                                  "grid",
                                gridTemplateColumns:
                                  "repeat(auto-fit,minmax(180px,1fr))",
                                gap: "8px",
                                marginBottom:
                                  "12px",
                              }}
                            >
                              {[
                                [
                                  "Actual Value",
                                  selectedContributionFeature.actual_value,
                                ],
                                [
                                  "Mean (μ)",
                                  selectedContributionFeature.mean_value,
                                ],
                                [
                                  "Deviation (x − μ)",
                                  selectedContributionFeature.deviation,
                                ],
                                [
                                  "Covariance-adjusted term",
                                  selectedContributionFeature.covariance_adjusted_deviation,
                                ],
                                [
                                  "Raw Contribution",
                                  selectedContributionFeature.contribution,
                                ],
                                [
                                  "Absolute Contribution",
                                  selectedContributionFeature.absolute_contribution,
                                ],
                              ].map(
                                ([
                                  label,
                                  value,
                                ]) => (
                                  <div
                                    key={
                                      label
                                    }
                                    style={{
                                      padding:
                                        "9px 10px",
                                      border:
                                        `1px solid ${COLORS.border}`,
                                      borderRadius:
                                        "8px",
                                      background:
                                        COLORS.surfaceSoft,
                                    }}
                                  >
                                    <div
                                      style={{
                                        color:
                                          COLORS.muted,
                                        fontSize:
                                          "13px",
                                        fontWeight:
                                          700,
                                        marginBottom:
                                          "3px",
                                      }}
                                    >
                                      {label}
                                    </div>

                                    <strong
                                      style={{
                                        color:
                                          COLORS.ink,
                                        fontSize:
                                          "15px",
                                      }}
                                    >
                                      {formatNumber(
                                        value
                                      )}
                                    </strong>
                                  </div>
                                )
                              )}
                            </div>

                            <div
                              style={{
                                padding:
                                  "11px 12px",
                                borderLeft:
                                  `4px solid ${COLORS.royal}`,
                                borderRadius:
                                  "7px",
                                background:
                                  COLORS.royalLight,
                                fontSize:
                                  "14px",
                                lineHeight:
                                  1.6,
                              }}
                            >
                              <strong>
                                Step 1 —
                                Feature
                                deviation
                              </strong>

                              <div>
                                x
                                <sub>
                                  j
                                </sub>{" "}
                                − μ
                                <sub>
                                  j
                                </sub>{" "}
                                ={" "}
                                {formatNumber(
                                  selectedContributionFeature.actual_value
                                )}{" "}
                                −{" "}
                                {formatNumber(
                                  selectedContributionFeature.mean_value
                                )}{" "}
                                ={" "}
                                {formatNumber(
                                  selectedContributionFeature.deviation
                                )}
                              </div>

                              <br />

                              <strong>
                                Step 2 —
                                Covariance
                                adjustment
                              </strong>

                              <div>
                                [Σ
                                <sup>
                                  −1
                                </sup>
                                (x − μ)]
                                <sub>
                                  j
                                </sub>{" "}
                                ={" "}
                                {formatNumber(
                                  selectedContributionFeature.covariance_adjusted_deviation
                                )}
                              </div>

                              <br />

                              <strong>
                                Step 3 —
                                Feature
                                contribution
                              </strong>

                              <div>
                                C
                                <sub>
                                  j
                                </sub>{" "}
                                = (x
                                <sub>
                                  j
                                </sub>{" "}
                                − μ
                                <sub>
                                  j
                                </sub>
                                ) × [Σ
                                <sup>
                                  −1
                                </sup>
                                (x − μ)]
                                <sub>
                                  j
                                </sub>{" "}
                                ={" "}
                                {formatNumber(
                                  selectedContributionFeature.contribution
                                )}
                              </div>

                              <br />

                              <strong>
                                Step 4 —
                                Relative
                                contribution
                              </strong>

                              <div>
                                |C
                                <sub>
                                  j
                                </sub>
                                | ÷ Σ|C
                                <sub>
                                  k
                                </sub>
                                | × 100 ={" "}
                                {formatNumber(
                                  selectedContributionFeature.contribution_percentage ??
                                    selectedContributionFeature.contribution_percent
                                )}
                                %
                              </div>

                              <br />

                              <strong>
                                Step 5 —
                                Relationship
                                to
                                Mahalanobis
                                score
                              </strong>

                              <div>
                                The signed
                                feature
                                contributions
                                sum to D²,
                                where D is
                                the
                                Mahalanobis
                                distance.
                                The displayed
                                percentage
                                ranks
                                contribution
                                magnitude and
                                therefore
                                uses absolute
                                contribution
                                values.
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                </div>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default MultivariateAnalysis;
