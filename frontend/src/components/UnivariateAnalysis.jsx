import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

/* ================================================================
   ROYAL BLUE DESIGN SYSTEM
================================================================ */

const COLORS = {
  ink: "#101a2e",

  royal: "#173f8a",
  royalDark: "#102f68",
  royalDeep: "#0d2858",
  royalLight: "#2f63b5",
  royalBright: "#3d74c9",

  gold: "#b89445",
  goldSoft: "#f7f1e4",

  background: "#eef3fa",
  surface: "#ffffff",
  surfaceSoft: "#f7f9fd",

  border: "#d9e1ef",
  borderStrong: "#c4d1e6",

  muted: "#68758a",

  blue: "#315f9d",
  blueSoft: "#edf4ff",

  red: "#b4233d",
  redSoft: "#fff0f3",

  green: "#14745a",
  greenSoft: "#edf8f3",

  hover: "#f2f6fc",
  selected: "#edf4ff",
};

function downloadGeneratedPdf(result) {
  const encoded = result?.pdf_base64;

  if (!encoded) {
    window.alert(
      "PDF report is not available in the backend response. Please run the analysis again."
    );
    return;
  }

  try {
    const cleanBase64 = String(encoded).includes(",")
      ? String(encoded).split(",")[1]
      : String(encoded);

    const binary = window.atob(cleanBase64);
    const bytes = new Uint8Array(binary.length);

    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }

    const blob = new Blob([bytes], {
      type: "application/pdf",
    });

    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");

    anchor.href = url;
    anchor.download =
      result?.pdf_filename ||
      "ANOMALY_Univariate_Anomaly_Report.pdf";

    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  } catch (downloadError) {
    console.error(
      "Unable to download the univariate PDF report:",
      downloadError
    );
    window.alert(
      "The PDF report could not be downloaded. Please run the analysis again."
    );
  }
}

/* ================================================================
   MAIN COMPONENT
================================================================ */

function UnivariateAnalysis({
  datasetId,
  result,
  loading = false,
  error = "",
  onBack,
}) {
  const [selectedColumn, setSelectedColumn] = useState(null);
  const [recordFilter, setRecordFilter] = useState("all");
  const [selectedRecord, setSelectedRecord] = useState(null);

  const columnAnalysisRef = useRef(null);
  const recordDetailRef = useRef(null);

  const [
    pendingColumnScroll,
    setPendingColumnScroll,
  ] = useState(false);

  const [
    pendingRecordScroll,
    setPendingRecordScroll,
  ] = useState(false);

  /*
   * IMPORTANT:
   * Defensive fallbacks prevent .map() crashes if the backend
   * temporarily returns an incomplete response.
   */

  const columnResults = Array.isArray(result?.results)
    ? result.results
    : [];

  const summary = Array.isArray(result?.summary)
    ? result.summary
    : [];

  /*
   * ACCURACY
   *
   * The backend supplies the evaluated accuracy.
   * No accuracy is calculated on the frontend.
   */
  const accuracy = result?.accuracy;

  const activeColumn = useMemo(() => {
    if (!selectedColumn) return null;

    return (
      columnResults.find(
        (item) => item.column_name === selectedColumn
      ) || null
    );
  }, [columnResults, selectedColumn]);

  const records = Array.isArray(activeColumn?.records)
    ? activeColumn.records
    : [];

  const filteredRecords = useMemo(() => {
    if (recordFilter === "anomaly") {
      return records.filter((record) => record.is_anomaly);
    }

    if (recordFilter === "normal") {
      return records.filter((record) => !record.is_anomaly);
    }

    return records;
  }, [records, recordFilter]);

  const totalRecords =
    Number(activeColumn?.total_records) || 0;

  const anomalyRecords =
    Number(activeColumn?.anomaly_records) || 0;

  const normalRecords =
    Number(activeColumn?.normal_records) || 0;

  const anomalyPercentage =
    Number(activeColumn?.anomaly_percentage) || 0;

  /* ==============================================================
     NUMBER FORMATTER
  ============================================================== */

  const formatNumber = (value) => {
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
      return value.toLocaleString(undefined, {
        maximumFractionDigits: 6,
      });
    }

    return String(value);
  };

  /* ==============================================================
     ACCURACY FORMATTER
  ============================================================== */

  const formatAccuracy = (value) => {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "—";
    }

    const numericAccuracy = Number(value);

    if (!Number.isFinite(numericAccuracy)) {
      return "—";
    }

    return `${numericAccuracy.toFixed(2)}%`;
  };

  /* ==============================================================
     SELECTION
  ============================================================== */

  const selectColumn = (columnName) => {
    setSelectedColumn(columnName);
    setRecordFilter("all");
    setSelectedRecord(null);
  };

  const selectRecord = (record) => {
    setSelectedRecord(record);
  };

  const exploreColumn = (columnName) => {
    selectColumn(columnName);
    setPendingColumnScroll(true);
  };

  const viewRecord = (record) => {
    selectRecord(record);
    setPendingRecordScroll(true);
  };

  /* ================================================================
     AUTOMATIC SECTION NAVIGATION
  ================================================================ */

  useEffect(() => {
    if (
      !pendingColumnScroll ||
      !activeColumn ||
      !columnAnalysisRef.current
    ) {
      return;
    }

    columnAnalysisRef.current.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });

    setPendingColumnScroll(false);
  }, [pendingColumnScroll, activeColumn]);

  useEffect(() => {
    if (
      !pendingRecordScroll ||
      !selectedRecord ||
      !recordDetailRef.current
    ) {
      return;
    }

    recordDetailRef.current.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });

    setPendingRecordScroll(false);
  }, [pendingRecordScroll, selectedRecord]);

  /* ================================================================
     IQR CHART
  ================================================================ */

  const chart = useMemo(() => {
    if (!activeColumn || records.length === 0) {
      return null;
    }

    const width = 1000;
    const height = 400;

    const margin = {
      top: 32,
      right: 38,
      bottom: 55,
      left: 78,
    };

    const innerWidth =
      width - margin.left - margin.right;

    const innerHeight =
      height - margin.top - margin.bottom;

    const numericValues = records
      .map((record) => Number(record.column_value))
      .filter(Number.isFinite);

    const lowerBoundary = Number(
      activeColumn.lower_boundary
    );

    const upperBoundary = Number(
      activeColumn.upper_boundary
    );

    const allValues = [
      ...numericValues,
      lowerBoundary,
      upperBoundary,
    ].filter(Number.isFinite);

    if (allValues.length === 0) {
      return null;
    }

    let minValue = Math.min(...allValues);
    let maxValue = Math.max(...allValues);

    if (minValue === maxValue) {
      minValue -= 1;
      maxValue += 1;
    }

    const padding =
      (maxValue - minValue) * 0.08 || 1;

    minValue -= padding;
    maxValue += padding;

    const maxRecord = Math.max(
      ...records.map(
        (record) =>
          Number(record.record_number) || 1
      )
    );

    const xScale = (recordNumber) => {
      if (maxRecord <= 1) {
        return margin.left + innerWidth / 2;
      }

      return (
        margin.left +
        ((Number(recordNumber) - 1) /
          (maxRecord - 1)) *
          innerWidth
      );
    };

    const yScale = (value) => {
      return (
        margin.top +
        (1 -
          (Number(value) - minValue) /
            (maxValue - minValue)) *
          innerHeight
      );
    };

    const yTicks = Array.from(
      { length: 5 },
      (_, index) =>
        minValue +
        ((maxValue - minValue) / 4) *
          index
    );

    /*
     * IMPORTANT FIX:
     * records is explicitly returned here.
     *
     * Previously the SVG used:
     * chart.records.map(...)
     *
     * but chart.records did not exist.
     */

    return {
      width,
      height,
      margin,
      innerWidth,
      innerHeight,
      lowerBoundary,
      upperBoundary,
      xScale,
      yScale,
      yTicks,
      records,
    };
  }, [activeColumn, records]);

  /* ================================================================
     LOADING
  ================================================================ */

  if (loading) {
    return (
      <div style={styles.page}>
        <StateBlock
          eyebrow="STATISTICAL ANALYSIS"
          title="Running IQR analysis"
          text="Evaluating eligible numerical columns."
        />
      </div>
    );
  }

  /* ================================================================
     ERROR
  ================================================================ */

  if (error) {
    return (
      <div style={styles.page}>
        <StateBlock
          eyebrow="ANALYSIS ERROR"
          title="Unable to complete analysis"
          text={error}
          error
          onBack={onBack}
        />
      </div>
    );
  }

  /* ================================================================
     MAIN UI
  ================================================================ */

  return (
    <div style={styles.page}>

      {/* ============================================================
          HEADER
      ============================================================ */}

      <header style={styles.header}>
        <div>
          <div style={styles.eyebrow}>
            STATISTICAL APPROACH · IQR
          </div>

          <h1 style={styles.title}>
            Univariate Analysis
          </h1>

          <p style={styles.subtitle}>
            Independent IQR-based anomaly detection
            across eligible numerical columns.
          </p>
        </div>

        <div style={styles.headerActions}>
          <div style={styles.methodBadge}>
            <span style={styles.badgeDot} />
            IQR METHOD
          </div>

          {onBack && (
            <button
              type="button"
              onClick={onBack}
              style={styles.backButton}
            >
              ← Back
            </button>
          )}
        </div>
      </header>

      {/* ============================================================
          DATASET STRIP
      ============================================================ */}

      <div style={styles.contextStrip}>
        <ContextItem
          label="Variability"
          value="Univariate"
        />

        <ContextDivider />

        <ContextItem
          label="Detection Method"
          value="Interquartile Range"
        />

        <ContextDivider />

        <ContextItem
          label="Dataset"
          value={datasetId || "—"}
          truncate
        />

        <ContextDivider />

        <ContextItem
          label="Accuracy"
          value={formatAccuracy(accuracy)}
        />
      </div>

      {/* ============================================================
          DETECTION SUMMARY
      ============================================================ */}

      <section style={styles.section}>
        <SectionHeader
          title="Detection Summary"
          subtitle="Numerical columns evaluated independently."
          right={
            <span style={styles.sectionTag}>
              {summary.length} columns
            </span>
          }
        />

        {summary.length === 0 ? (
          <EmptyState
            text="No eligible numerical columns were found."
          />
        ) : (
          <TableScroll>
            <table style={styles.table}>
              <thead>
                <tr>
                  <Th>#</Th>
                  <Th>Column</Th>
                  <Th>Anomaly Records</Th>
                  <Th>Anomaly Rate</Th>
                  <Th>Status</Th>
                  <Th align="right">Action</Th>
                </tr>
              </thead>

              <tbody>
                {summary.map((item, index) => {
                  const anomalyCount =
                    Number(
                      item.total_anomaly_records
                    ) || 0;

                  const percentage =
                    Number(
                      item.anomaly_percentage
                    ) || 0;

                  const active =
                    selectedColumn ===
                    item.column_name;

                  return (
                    <tr
                      key={item.column_name}
                      style={
                        active
                          ? styles.activeRow
                          : undefined
                      }
                      className="uv-table-row"
                    >
                      <Td>
                        <span
                          style={
                            styles.rowNumber
                          }
                        >
                          {String(
                            item.s_no ||
                              index + 1
                          ).padStart(2, "0")}
                        </span>
                      </Td>

                      <Td>
                        <button
                          type="button"
                          onClick={() =>
                            selectColumn(
                              item.column_name
                            )
                          }
                          style={
                            styles.columnButton
                          }
                        >
                          {item.column_name}
                        </button>
                      </Td>

                      <Td>
                        <strong>
                          {anomalyCount}
                        </strong>
                      </Td>

                      <Td>
                        <div
                          style={
                            styles.rateWrapper
                          }
                        >
                          <div
                            style={
                              styles.progressTrack
                            }
                          >
                            <span
                              style={{
                                ...styles.progressFill,
                                width: `${Math.min(
                                  percentage,
                                  100
                                )}%`,
                              }}
                            />
                          </div>

                          <strong>
                            {formatNumber(
                              percentage
                            )}
                            %
                          </strong>
                        </div>
                      </Td>

                      <Td>
                        <StatusPill
                          anomaly={
                            anomalyCount > 0
                          }
                        >
                          {anomalyCount > 0
                            ? "Anomalies detected"
                            : "No anomalies"}
                        </StatusPill>
                      </Td>

                      <Td align="right">
                        <button
                          type="button"
                          onClick={() =>
                            exploreColumn(
                              item.column_name
                            )
                          }
                          style={{
                            ...styles.actionButton,
                            ...(active
                              ? styles.actionButtonActive
                              : {}),
                          }}
                        >
                          Explore →
                        </button>
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </TableScroll>
        )}
      </section>

      {/* ============================================================
          ACTIVE COLUMN
      ============================================================ */}

      {activeColumn && (
        <>
          {/* ========================================================
              COLUMN PROFILE
          ======================================================== */}

          <section
            ref={columnAnalysisRef}
            style={styles.section}
          >
            <SectionHeader
              title="Column Analysis"
              subtitle={`Statistical profile for ${activeColumn.column_name}.`}
              right={
                <span style={styles.selectedTag}>
                  {activeColumn.column_name}
                </span>
              }
            />

            <TableScroll>
              <table style={styles.detailTable}>
                <tbody>
                  <tr>
                    <LabelCell>
                      Column
                    </LabelCell>

                    <ValueCell>
                      {activeColumn.column_name}
                    </ValueCell>

                    <LabelCell>
                      Data Type
                    </LabelCell>

                    <ValueCell>
                      {activeColumn.column_dtype}
                    </ValueCell>

                    <LabelCell>
                      Total Records
                    </LabelCell>

                    <ValueCell>
                      {formatNumber(
                        totalRecords
                      )}
                    </ValueCell>
                  </tr>

                  <tr>
                    <LabelCell>
                      Anomaly Records
                    </LabelCell>

                    <ValueCell danger>
                      {formatNumber(
                        anomalyRecords
                      )}
                    </ValueCell>

                    <LabelCell>
                      Normal Records
                    </LabelCell>

                    <ValueCell success>
                      {formatNumber(
                        normalRecords
                      )}
                    </ValueCell>

                    <LabelCell>
                      Anomaly Rate
                    </LabelCell>

                    <ValueCell danger>
                      {formatNumber(
                        anomalyPercentage
                      )}
                      %
                    </ValueCell>
                  </tr>
                </tbody>
              </table>
            </TableScroll>

            <div style={styles.subSectionTitle}>
              IQR STATISTICS
            </div>

            <TableScroll>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <Th>Q1</Th>
                    <Th>Q3</Th>
                    <Th>IQR</Th>
                    <Th>Lower Boundary</Th>
                    <Th>Upper Boundary</Th>
                    <Th>Method</Th>
                  </tr>
                </thead>

                <tbody>
                  <tr className="uv-table-row">
                    <Td>
                      {formatNumber(
                        activeColumn.q1
                      )}
                    </Td>

                    <Td>
                      {formatNumber(
                        activeColumn.q3
                      )}
                    </Td>

                    <Td>
                      <strong
                        style={{
                          color: COLORS.royal,
                        }}
                      >
                        {formatNumber(
                          activeColumn.iqr
                        )}
                      </strong>
                    </Td>

                    <Td>
                      {formatNumber(
                        activeColumn.lower_boundary
                      )}
                    </Td>

                    <Td>
                      {formatNumber(
                        activeColumn.upper_boundary
                      )}
                    </Td>

                    <Td>
                      <span
                        style={
                          styles.methodChip
                        }
                      >
                        IQR
                      </span>
                    </Td>
                  </tr>
                </tbody>
              </table>
            </TableScroll>
          </section>

          {/* ========================================================
              RECORDS
          ======================================================== */}

          <section style={styles.section}>
            <SectionHeader
              title="Records"
              subtitle="Inspect individual observations."
              right={
                <div style={styles.filterGroup}>
                  <FilterButton
                    active={
                      recordFilter === "all"
                    }
                    onClick={() => {
                      setRecordFilter("all");
                      setSelectedRecord(null);
                    }}
                    label="All"
                    count={totalRecords}
                  />

                  <FilterButton
                    active={
                      recordFilter ===
                      "anomaly"
                    }
                    onClick={() => {
                      setRecordFilter(
                        "anomaly"
                      );
                      setSelectedRecord(null);
                    }}
                    label="Anomalies"
                    count={anomalyRecords}
                    anomaly
                  />

                  <FilterButton
                    active={
                      recordFilter ===
                      "normal"
                    }
                    onClick={() => {
                      setRecordFilter(
                        "normal"
                      );
                      setSelectedRecord(null);
                    }}
                    label="Normal"
                    count={normalRecords}
                  />
                </div>
              }
            />

            <div style={{ maxHeight: "520px", overflowY: "auto", overflowX: "auto" }}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <Th>Record</Th>
                    <Th>Value</Th>
                    <Th>Boundary Comparison</Th>
                    <Th>Status</Th>
                    <Th align="right">
                      Action
                    </Th>
                  </tr>
                </thead>

                <tbody>
                  {filteredRecords.map(
                    (record) => {
                      const active =
                        selectedRecord?.record_number ===
                        record.record_number;

                      return (
                        <tr
                          key={
                            record.record_number
                          }
                          style={
                            active
                              ? styles.activeRow
                              : undefined
                          }
                          className="uv-table-row"
                        >
                          <Td>
                            <span
                              style={
                                styles.recordBadge
                              }
                            >
                              #
                              {
                                record.record_number
                              }
                            </span>
                          </Td>

                          <Td>
                            <strong>
                              {formatNumber(
                                record.column_value
                              )}
                            </strong>
                          </Td>

                          <Td>
                            <span
                              style={
                                styles.boundaryText
                              }
                            >
                              {record.boundary_comparison ||
                                "—"}
                            </span>
                          </Td>

                          <Td>
                            <StatusPill
                              anomaly={
                                record.is_anomaly
                              }
                            >
                              {record.status}
                            </StatusPill>
                          </Td>

                          <Td align="right">
                            <button
                              type="button"
                              onClick={() =>
                                viewRecord(
                                  record
                                )
                              }
                              style={{
                                ...styles.actionButton,
                                ...(active
                                  ? styles.actionButtonActive
                                  : {}),
                              }}
                            >
                              View →
                            </button>
                          </Td>
                        </tr>
                      );
                    }
                  )}
                </tbody>
              </table>
            </div>

            {filteredRecords.length ===
              0 && (
              <EmptyState
                text="No records match the selected filter."
              />
            )}
          </section>

          {/* ========================================================
              RECORD DETAIL
          ======================================================== */}

          {selectedRecord && (
            <section
              ref={recordDetailRef}
              style={styles.detailSection}
            >
              <div style={styles.detailHeader}>
                <div>
                  <div style={styles.eyebrow}>
                    RECORD DETAIL
                  </div>

                  <h2
                    style={{
                      margin: "5px 0 0",
                      fontSize: 23,
                    }}
                  >
                    Record #
                    {
                      selectedRecord.record_number
                    }
                  </h2>
                </div>

                <StatusPill
                  anomaly={
                    selectedRecord.is_anomaly
                  }
                >
                  {selectedRecord.status}
                </StatusPill>
              </div>

              <TableScroll>
                <table
                  style={styles.detailTable}
                >
                  <tbody>
                    <tr>
                      <LabelCell>
                        Column
                      </LabelCell>

                      <ValueCell>
                        {
                          selectedRecord.column_name
                        }
                      </ValueCell>

                      <LabelCell>
                        Actual Value
                      </LabelCell>

                      <ValueCell>
                        {formatNumber(
                          selectedRecord.column_value
                        )}
                      </ValueCell>

                      <LabelCell>
                        Lower Boundary
                      </LabelCell>

                      <ValueCell>
                        {formatNumber(
                          selectedRecord.lower_boundary
                        )}
                      </ValueCell>

                      <LabelCell>
                        Upper Boundary
                      </LabelCell>

                      <ValueCell>
                        {formatNumber(
                          selectedRecord.upper_boundary
                        )}
                      </ValueCell>
                    </tr>
                  </tbody>
                </table>
              </TableScroll>

              <div
                style={
                  styles.reasonContainer
                }
              >
                <span
                  style={
                    styles.reasonLabel
                  }
                >
                  DYNAMIC REASON
                </span>

                <p
                  style={
                    styles.reasonText
                  }
                >
                  {selectedRecord.reason ||
                    "No additional interpretation was returned."}
                </p>
              </div>
            </section>
          )}

          {/* ========================================================
              VISUALIZATION
          ======================================================== */}

          <section style={styles.section}>
            <SectionHeader
              title="IQR Visualization"
              subtitle="Actual Phase 3 preprocessed values."
              right={
                <span style={styles.sectionTag}>
                  Click a point to inspect
                </span>
              }
            />

            {chart ? (
              <div style={styles.chartArea}>
                <div style={styles.chartLegend}>
                  <LegendDot
                    color={COLORS.blue}
                    label="Normal"
                  />

                  <LegendDot
                    color={COLORS.red}
                    label="Anomaly"
                  />

                  <LegendLine
                    color={COLORS.gold}
                    label="Lower boundary"
                  />

                  <LegendLine
                    color={COLORS.royalLight}
                    label="Upper boundary"
                  />
                </div>

                <div
                  style={{
                    overflowX: "auto",
                  }}
                >
                  <svg
                    viewBox={`0 0 ${chart.width} ${chart.height}`}
                    width="100%"
                    role="img"
                    aria-label={`IQR scatter plot for ${activeColumn.column_name}`}
                    style={{
                      minWidth: 700,
                    }}
                  >
                    {/* Grid */}

                    {chart.yTicks.map(
                      (tick, index) => {
                        const y =
                          chart.yScale(tick);

                        return (
                          <g
                            key={`tick-${index}`}
                          >
                            <line
                              x1={
                                chart.margin
                                  .left
                              }
                              x2={
                                chart.width -
                                chart.margin
                                  .right
                              }
                              y1={y}
                              y2={y}
                              stroke={
                                COLORS.border
                              }
                              strokeDasharray="4 5"
                            />

                            <text
                              x={
                                chart.margin
                                  .left - 10
                              }
                              y={y + 4}
                              textAnchor="end"
                              fontSize="14"
                              fill={
                                COLORS.muted
                              }
                            >
                              {formatNumber(
                                tick
                              )}
                            </text>
                          </g>
                        );
                      }
                    )}

                    {/* Axes */}

                    <line
                      x1={
                        chart.margin.left
                      }
                      x2={
                        chart.margin.left
                      }
                      y1={
                        chart.margin.top
                      }
                      y2={
                        chart.height -
                        chart.margin.bottom
                      }
                      stroke="#9ba9bd"
                    />

                    <line
                      x1={
                        chart.margin.left
                      }
                      x2={
                        chart.width -
                        chart.margin.right
                      }
                      y1={
                        chart.height -
                        chart.margin.bottom
                      }
                      y2={
                        chart.height -
                        chart.margin.bottom
                      }
                      stroke="#9ba9bd"
                    />

                    {/* Lower boundary */}

                    {Number.isFinite(
                      chart.lowerBoundary
                    ) && (
                      <>
                        <line
                          x1={
                            chart.margin.left
                          }
                          x2={
                            chart.width -
                            chart.margin.right
                          }
                          y1={chart.yScale(
                            chart.lowerBoundary
                          )}
                          y2={chart.yScale(
                            chart.lowerBoundary
                          )}
                          stroke={
                            COLORS.gold
                          }
                          strokeWidth="2"
                          strokeDasharray="8 5"
                        />

                        <text
                          x={
                            chart.width -
                            chart.margin.right -
                            4
                          }
                          y={
                            chart.yScale(
                              chart.lowerBoundary
                            ) - 7
                          }
                          textAnchor="end"
                          fontSize="14"
                          fill={
                            COLORS.gold
                          }
                        >
                          Lower
                        </text>
                      </>
                    )}

                    {/* Upper boundary */}

                    {Number.isFinite(
                      chart.upperBoundary
                    ) && (
                      <>
                        <line
                          x1={
                            chart.margin.left
                          }
                          x2={
                            chart.width -
                            chart.margin.right
                          }
                          y1={chart.yScale(
                            chart.upperBoundary
                          )}
                          y2={chart.yScale(
                            chart.upperBoundary
                          )}
                          stroke={
                            COLORS.royalLight
                          }
                          strokeWidth="2"
                          strokeDasharray="8 5"
                        />

                        <text
                          x={
                            chart.width -
                            chart.margin.right -
                            4
                          }
                          y={
                            chart.yScale(
                              chart.upperBoundary
                            ) - 7
                          }
                          textAnchor="end"
                          fontSize="14"
                          fill={
                            COLORS.royalLight
                          }
                        >
                          Upper
                        </text>
                      </>
                    )}

                    {/* Records */}

                    {Array.isArray(
                      chart.records
                    ) &&
                      chart.records.map(
                        (record) => {
                          const value =
                            Number(
                              record.column_value
                            );

                          if (
                            !Number.isFinite(
                              value
                            )
                          ) {
                            return null;
                          }

                          const x =
                            chart.xScale(
                              record.record_number
                            );

                          const y =
                            chart.yScale(
                              value
                            );

                          const selected =
                            selectedRecord?.record_number ===
                            record.record_number;

                          return (
                            <g
                              key={
                                record.record_number
                              }
                            >
                              {selected && (
                                <circle
                                  cx={x}
                                  cy={y}
                                  r="10"
                                  fill="none"
                                  stroke={
                                    COLORS.royalDark
                                  }
                                  strokeWidth="2"
                                />
                              )}

                              <circle
                                cx={x}
                                cy={y}
                                r={
                                  selected
                                    ? 6
                                    : 4.5
                                }
                                fill={
                                  record.is_anomaly
                                    ? COLORS.red
                                    : COLORS.blue
                                }
                                stroke="#fff"
                                strokeWidth="1.5"
                                style={{
                                  cursor:
                                    "pointer",
                                }}
                                onClick={() =>
                                  viewRecord(
                                    record
                                  )
                                }
                              >
                                <title>
                                  {`Record ${record.record_number} | Value: ${formatNumber(
                                    record.column_value
                                  )} | ${record.status}`}
                                </title>
                              </circle>
                            </g>
                          );
                        }
                      )}

                    <text
                      x={
                        chart.width / 2
                      }
                      y={
                        chart.height - 14
                      }
                      textAnchor="middle"
                      fontSize="15"
                      fill={COLORS.muted}
                    >
                      Record Number
                    </text>

                    <text
                      x="18"
                      y={
                        chart.height / 2
                      }
                      textAnchor="middle"
                      fontSize="15"
                      fill={COLORS.muted}
                      transform={`rotate(-90 18 ${
                        chart.height / 2
                      })`}
                    >
                      {
                        activeColumn.column_name
                      }
                    </text>
                  </svg>
                </div>
              </div>
            ) : (
              <EmptyState
                text="No numeric records are available for visualization."
              />
            )}
          </section>
        </>
      )}

      {/* ============================================================
          PDF REPORT
      ============================================================ */}

      <section style={styles.reportSection}>
        <div style={styles.reportHeader}>
          <div>
            <div style={styles.eyebrow}>DOWNLOADABLE REPORT</div>
            <h2 style={styles.sectionTitle}>
              Univariate Anomaly Detection Report
            </h2>
            <p style={styles.sectionSubtitle}>
              A4 PDF containing the anomaly summary and, for each numerical
              column, one IQR statistics table followed by the record values,
              boundary comparison, reason, and status. No visualizations are
              included.
            </p>
          </div>

          <button
            type="button"
            onClick={() => downloadGeneratedPdf(result)}
            disabled={!result?.pdf_base64}
            style={{
              ...styles.reportButton,
              ...(!result?.pdf_base64
                ? styles.reportButtonDisabled
                : {}),
            }}
          >
            {result?.pdf_base64
              ? "Download PDF Report"
              : "PDF Preparing..."}
          </button>
        </div>
      </section>
    </div>
  );
}

/* ================================================================
   SMALL COMPONENTS
================================================================ */

function ContextItem({
  label,
  value,
  truncate = false,
}) {
  return (
    <div style={styles.contextItem}>
      <span style={styles.contextLabel}>
        {label}
      </span>

      <strong
        title={value}
        style={
          truncate
            ? {
                overflow: "hidden",
                textOverflow:
                  "ellipsis",
                whiteSpace:
                  "nowrap",
              }
            : undefined
        }
      >
        {value}
      </strong>
    </div>
  );
}

function ContextDivider() {
  return (
    <div
      style={
        styles.contextDivider
      }
    />
  );
}

function SectionHeader({
  title,
  subtitle,
  right,
}) {
  return (
    <div style={styles.sectionHeader}>
      <div>
        <h2 style={styles.sectionTitle}>
          {title}
        </h2>

        <p
          style={
            styles.sectionSubtitle
          }
        >
          {subtitle}
        </p>
      </div>

      {right}
    </div>
  );
}

function TableScroll({ children }) {
  return (
    <div
      style={{
        overflowX: "auto",
      }}
    >
      {children}
    </div>
  );
}

function Th({ children, align }) {
  return (
    <th
      style={{
        ...styles.th,
        textAlign: align || "left",
      }}
    >
      {children}
    </th>
  );
}

function Td({ children, align }) {
  return (
    <td
      style={{
        ...styles.td,
        textAlign: align || "left",
      }}
    >
      {children}
    </td>
  );
}

function LabelCell({ children }) {
  return (
    <td
      style={{
        ...styles.td,
        color: COLORS.muted,
        fontWeight: 800,
        fontSize: 13,
        textTransform:
          "uppercase",
        letterSpacing: ".6px",
      }}
    >
      {children}
    </td>
  );
}

function ValueCell({
  children,
  danger = false,
  success = false,
}) {
  return (
    <td
      style={{
        ...styles.td,
        color: danger
          ? COLORS.red
          : success
          ? COLORS.green
          : COLORS.ink,
        fontWeight: 800,
      }}
    >
      {children}
    </td>
  );
}

function StatusPill({
  anomaly,
  children,
}) {
  return (
    <span
      style={{
        ...styles.statusPill,
        color: anomaly
          ? COLORS.red
          : COLORS.green,
        background: anomaly
          ? COLORS.redSoft
          : COLORS.greenSoft,
        border: `1px solid ${
          anomaly
            ? "#f2ccd5"
            : "#c9e8db"
        }`,
      }}
    >
      <span
        style={{
          ...styles.statusDot,
          background: anomaly
            ? COLORS.red
            : COLORS.green,
        }}
      />

      {children}
    </span>
  );
}

function FilterButton({
  active,
  onClick,
  label,
  count,
  anomaly = false,
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        ...styles.filterButton,
        ...(active
          ? styles.filterButtonActive
          : {}),
        ...(active && anomaly
          ? {
              color: COLORS.red,
            }
          : {}),
      }}
    >
      {label}

      <b>{count}</b>
    </button>
  );
}

function LegendDot({
  color,
  label,
}) {
  return (
    <span style={styles.legendItem}>
      <i
        style={{
          ...styles.legendDot,
          background: color,
        }}
      />

      {label}
    </span>
  );
}

function LegendLine({
  color,
  label,
}) {
  return (
    <span style={styles.legendItem}>
      <i
        style={{
          ...styles.legendLine,
          borderTopColor: color,
        }}
      />

      {label}
    </span>
  );
}

function EmptyState({ text }) {
  return (
    <div style={styles.emptyState}>
      <span>—</span>
      {text}
    </div>
  );
}

function StateBlock({
  eyebrow,
  title,
  text,
  error = false,
  onBack,
}) {
  return (
    <div style={styles.stateWrapper}>
      <div
        style={{
          ...styles.stateBlock,
          ...(error
            ? {
                borderTopColor:
                  COLORS.red,
              }
            : {}),
        }}
      >
        <div style={styles.eyebrow}>
          {eyebrow}
        </div>

        <h2>{title}</h2>

        <p>{text}</p>

        {onBack && (
          <button
            type="button"
            onClick={onBack}
            style={styles.backButton}
          >
            ← Back
          </button>
        )}
      </div>
    </div>
  );
}

/* ================================================================
   STYLES
================================================================ */

const styles = {
  page: {
    minHeight: "100%",
    background:
      "linear-gradient(180deg, #edf3fb 0%, #f5f7fb 45%, #eef3fa 100%)",
    color: COLORS.ink,
    padding:
      "28px clamp(16px, 4vw, 56px) 60px",
    fontFamily:
      "Inter, Segoe UI, Roboto, Arial, sans-serif",
  },

  header: {
    maxWidth: 1240,
    margin: "0 auto 18px",
    padding: "20px 18px",
    borderRadius: 16,
    display: "flex",
    justifyContent:
      "space-between",
    alignItems: "flex-start",
    gap: 24,
    color: "#fff",
    background:
      `linear-gradient(135deg, ${COLORS.royalDeep}, ${COLORS.royal} 58%, ${COLORS.royalLight})`,
    boxShadow:
      "0 14px 34px rgba(23,63,138,.22)",
  },

  headerActions: {
    display: "flex",
    alignItems: "center",
    justifyContent: "flex-end",
    gap: 12,
    flexWrap: "wrap",
  },

  backButton: {
    border: "1px solid rgba(255,255,255,.35)",
    background: "rgba(255,255,255,.10)",
    color: "#fff",
    borderRadius: 9,
    padding: "10px 15px",
    fontSize: 16,
    fontWeight: 700,
    cursor: "pointer",
    whiteSpace: "nowrap",
  },

  eyebrow: {
    color: COLORS.gold,
    fontSize: 13,
    fontWeight: 900,
    letterSpacing: "1.8px",
  },

  title: {
    margin: "6px 0 5px",
    fontSize:
      "clamp(29px, 3vw, 39px)",
    lineHeight: 1.1,
    fontWeight: 850,
    letterSpacing: "-.7px",
    color: "#fff",
  },

  subtitle: {
    margin: 0,
    color: "rgba(255,255,255,.78)",
    fontSize: 16,
    lineHeight: 1.5,
  },

  methodBadge: {
    background:
      `linear-gradient(135deg, ${COLORS.royalDeep}, ${COLORS.royal})`,
    color: "#fff",
    padding: "10px 14px",
    borderRadius: 4,
    fontSize: 13,
    fontWeight: 900,
    letterSpacing: "1.2px",
    whiteSpace: "nowrap",
    boxShadow:
      "0 6px 16px rgba(23,63,138,.22)",
    border:
      "1px solid rgba(255,255,255,.12)",
  },

  badgeDot: {
    display: "inline-block",
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: COLORS.gold,
    marginRight: 7,
    boxShadow:
      "0 0 0 3px rgba(184,148,69,.15)",
  },

  contextStrip: {
    maxWidth: 1240,
    margin: "0 auto 18px",
    display: "grid",
    gridTemplateColumns:
      "1fr 1px 1fr 1px 1.4fr 1px 1fr",
    alignItems: "stretch",
    background:
      "rgba(255,255,255,.96)",
    border:
      `1px solid ${COLORS.borderStrong}`,
    borderTop:
      `3px solid ${COLORS.royal}`,
    boxShadow:
      "0 8px 25px rgba(20,48,94,.08)",
  },

  contextItem: {
    minWidth: 0,
    padding: "11px 16px",
    background: "#f1f5ff",
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },

  contextLabel: {
    color: COLORS.muted,
    fontSize: 12,
    fontWeight: 800,
    textTransform:
      "uppercase",
    letterSpacing: ".7px",
  },

  contextDivider: {
    background:
      COLORS.border,
  },

  section: {
    maxWidth: 1240,
    margin: "0 auto 18px",
    background:
      "rgba(255,255,255,.98)",
    border:
      `1px solid ${COLORS.borderStrong}`,
    borderTop:
      `3px solid ${COLORS.royal}`,
    boxShadow:
      "0 7px 24px rgba(20,48,94,.065)",
    transition:
      "box-shadow .2s ease, border-color .2s ease, transform .2s ease",
  },

  sectionHeader: {
    padding:
      "14px 18px",
    display: "flex",
    justifyContent:
      "space-between",
    alignItems: "center",
    gap: 20,
    borderBottom:
      `1px solid ${COLORS.border}`,
    background:
      "linear-gradient(90deg, #f9fbff 0%, #ffffff 60%)",
  },

  sectionTitle: {
    margin: 0,
    fontSize: 19,
    fontWeight: 850,
    letterSpacing: "-.2px",
    color: COLORS.royalDeep,
  },

  sectionSubtitle: {
    margin: "3px 0 0",
    color: COLORS.muted,
    fontSize: 14,
  },

  sectionTag: {
    padding: "6px 9px",
    background:
      COLORS.blueSoft,
    color: COLORS.royal,
    border:
      "1px solid #d4e1f4",
    fontSize: 13,
    fontWeight: 850,
    borderRadius: 3,
    whiteSpace: "nowrap",
  },

  selectedTag: {
    padding: "6px 10px",
    background:
      COLORS.goldSoft,
    color: "#76571f",
    border:
      "1px solid #eadabd",
    fontSize: 14,
    fontWeight: 850,
    borderRadius: 3,
    boxShadow:
      "0 2px 6px rgba(184,148,69,.08)",
  },

  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: 15,
  },

  detailTable: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: 15,
  },

  th: {
    padding:
      "10px 13px",
    background:
      COLORS.royalDark,
    borderBottom:
      `1px solid ${COLORS.border}`,
    borderRight:
      "1px solid rgba(255,255,255,.12)",
    color: "#fff",
    fontSize: 12,
    fontWeight: 900,
    letterSpacing: ".9px",
    textTransform:
      "uppercase",
    whiteSpace: "nowrap",
  },

  td: {
    padding:
      "10px 13px",
    borderBottom:
      `1px solid ${COLORS.border}`,
    verticalAlign:
      "middle",
    background: "#f1f5ff",
    color: COLORS.ink,
  },

  activeRow: {
    background:
      COLORS.selected,
    boxShadow:
      `inset 3px 0 0 ${COLORS.royal}`,
  },

  rowNumber: {
    color: COLORS.muted,
    fontSize: 13,
    fontWeight: 800,
  },

  columnButton: {
    border: 0,
    background: "transparent",
    color: COLORS.royal,
    padding: 0,
    fontSize: 15,
    fontWeight: 850,
    cursor: "pointer",
  },

  rateWrapper: {
    display: "flex",
    alignItems: "center",
    gap: 9,
    minWidth: 130,
  },

  progressTrack: {
    width: 65,
    height: 4,
    background:
      "#e3e9f2",
    borderRadius: 10,
    overflow: "hidden",
  },

  progressFill: {
    display: "block",
    height: "100%",
    background:
      `linear-gradient(90deg, ${COLORS.royal}, ${COLORS.royalLight})`,
    borderRadius: 10,
  },

  statusPill: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding:
      "5px 8px",
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 900,
    whiteSpace: "nowrap",
  },

  statusDot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
  },

  actionButton: {
    border:
      "1px solid #c8d5e8",
    background: "#fff",
    color: COLORS.royal,
    padding:
      "6px 9px",
    borderRadius: 3,
    fontSize: 13,
    fontWeight: 850,
    cursor: "pointer",
    transition:
      "all .18s ease",
  },

  actionButtonActive: {
    background:
      `linear-gradient(135deg, ${COLORS.royalDark}, ${COLORS.royal})`,
    color: "#fff",
    borderColor:
      COLORS.royal,
    boxShadow:
      "0 4px 10px rgba(23,63,138,.2)",
  },

  subSectionTitle: {
    padding:
      "14px 13px 7px",
    color: COLORS.gold,
    fontSize: 12,
    fontWeight: 900,
    letterSpacing:
      "1.4px",
  },

  methodChip: {
    display:
      "inline-block",
    padding:
      "4px 8px",
    background:
      COLORS.blueSoft,
    color: COLORS.royal,
    border:
      "1px solid #d4e1f4",
    borderRadius: 3,
    fontSize: 12,
    fontWeight: 900,
  },

  chartArea: {
    padding:
      "12px 18px 16px",
  },

  chartLegend: {
    display: "flex",
    alignItems: "center",
    gap: 17,
    flexWrap: "wrap",
    padding:
      "0 2px 10px",
    color: COLORS.muted,
    fontSize: 13,
  },

  legendItem: {
    display:
      "inline-flex",
    alignItems:
      "center",
    gap: 6,
  },

  legendDot: {
    width: 7,
    height: 7,
    borderRadius: "50%",
  },

  legendLine: {
    width: 18,
    borderTop:
      "2px dashed",
  },

  filterGroup: {
    display: "flex",
    gap: 3,
    background:
      "#edf2f9",
    padding: 3,
    borderRadius: 4,
    border:
      "1px solid #dce4f0",
  },

  filterButton: {
    border: 0,
    background:
      "transparent",
    color: COLORS.muted,
    padding:
      "5px 9px",
    fontSize: 12,
    fontWeight: 700,
    cursor: "pointer",
    borderRadius: 3,
    transition:
      "all .18s ease",
  },

  filterButtonActive: {
    background: "#fff",
    color: COLORS.royal,
    fontWeight: 900,
    boxShadow:
      "0 2px 7px rgba(20,48,94,.12)",
  },

  recordBadge: {
    display:
      "inline-block",
    minWidth: 27,
    textAlign:
      "center",
    padding:
      "4px 6px",
    background:
      COLORS.blueSoft,
    color: COLORS.royal,
    border:
      "1px solid #d7e2f2",
    fontSize: 12,
    fontWeight: 850,
    borderRadius: 3,
  },

  boundaryText: {
    color: COLORS.muted,
    fontSize: 14,
  },

  detailSection: {
    maxWidth: 1240,
    margin:
      "0 auto 18px",
    background:
      "rgba(255,255,255,.98)",
    border:
      `1px solid ${COLORS.borderStrong}`,
    borderTop:
      `3px solid ${COLORS.royal}`,
    boxShadow:
      "0 8px 25px rgba(20,48,94,.08)",
  },

  detailHeader: {
    padding:
      "14px 18px",
    display: "flex",
    justifyContent:
      "space-between",
    alignItems: "center",
    borderBottom:
      `1px solid ${COLORS.border}`,
    background:
      "linear-gradient(90deg, #f4f6ff, #ffffff)",
  },

  reasonContainer: {
    margin:
      "12px 18px 16px",
    padding:
      "10px 12px",
    background:
      "#f7f9fd",
    borderLeft:
      `3px solid ${COLORS.royal}`,
    borderTop:
      "1px solid #e4eaf3",
    borderRight:
      "1px solid #e4eaf3",
    borderBottom:
      "1px solid #e4eaf3",
  },

  reasonLabel: {
    display: "block",
    color: COLORS.gold,
    fontSize: 12,
    fontWeight: 900,
    letterSpacing:
      "1.2px",
    marginBottom: 4,
  },

  reasonText: {
    margin: 0,
    color: COLORS.ink,
    fontSize: 14,
    lineHeight: 1.5,
  },

  emptyState: {
    padding: 30,
    textAlign: "center",
    color: COLORS.muted,
    fontSize: 15,
  },

  reportSection: {
    marginTop: 18,
    padding: 22,
    background: COLORS.surface,
    border: `1px solid ${COLORS.borderStrong}`,
    borderTop: `3px solid ${COLORS.gold}`,
    boxShadow: "0 10px 28px rgba(20,48,94,.07)",
  },

  reportHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 20,
    flexWrap: "wrap",
  },

  reportButton: {
    border: "none",
    borderRadius: 7,
    padding: "11px 17px",
    background: COLORS.royal,
    color: "#fff",
    fontSize: 14,
    fontWeight: 800,
    cursor: "pointer",
    boxShadow: "0 6px 15px rgba(23,63,138,.20)",
  },

  reportButtonDisabled: {
    opacity: 0.55,
    cursor: "not-allowed",
    boxShadow: "none",
  },

  stateWrapper: {
    minHeight:
      "70vh",
    display: "flex",
    alignItems: "center",
    justifyContent:
      "center",
  },

  stateBlock: {
    width:
      "min(620px, 100%)",
    padding: 32,
    textAlign: "center",
    background:
      COLORS.surface,
    border:
      `1px solid ${COLORS.borderStrong}`,
    borderTop:
      `3px solid ${COLORS.royal}`,
    boxShadow:
      "0 12px 35px rgba(20,48,94,.10)",
  },
};

/* ================================================================
   GLOBAL HOVER ENHANCEMENT
   ================================================================ */

if (
  typeof document !== "undefined" &&
  !document.getElementById(
    "univariate-royal-enhancements"
  )
) {
  const style =
    document.createElement("style");

  style.id =
    "univariate-royal-enhancements";

  style.textContent = `
    .uv-table-row {
      transition:
        background-color .16s ease,
        box-shadow .16s ease;
    }

    .uv-table-row:hover {
      background: #f4f8ff !important;
      box-shadow:
        inset 3px 0 0 #3d74c9;
    }

    .uv-table-row:hover td {
      color: #172d52;
    }

    button:hover {
      filter: brightness(1.035);
    }

    button:active {
      transform: translateY(1px);
    }
  `;

  document.head.appendChild(style);
}

export default UnivariateAnalysis;