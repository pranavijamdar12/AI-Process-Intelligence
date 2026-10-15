
import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function formatValue(value) {
  if (value === null || value === undefined) return "N/A";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function getArray(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.tickets)) return data.tickets;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

function getTicketId(ticket) {
  return (
    ticket?.ticket_id ??
    ticket?.Ticket_ID ??
    ticket?.Case_ID ??
    ticket?.case_id ??
    ticket?.id ??
    null
  );
}

function combineTickets(oldTickets, databaseTickets) {
  const combined = [];
  const indexes = new Map();

  [...oldTickets, ...databaseTickets].forEach((ticket) => {
    if (!ticket || typeof ticket !== "object") return;

    const id = getTicketId(ticket);

    if (id === null || String(id).trim() === "") {
      combined.push(ticket);
      return;
    }

    const key = String(id).trim().toLowerCase();

    if (indexes.has(key)) {
      const index = indexes.get(key);
      combined[index] = { ...combined[index], ...ticket };
    } else {
      indexes.set(key, combined.length);
      combined.push(ticket);
    }
  });

  return combined;
}

function DataTable({ data }) {
  if (!Array.isArray(data) || data.length === 0) {
    return <p className="empty-message">No data available.</p>;
  }

  const columns = [
    ...new Set(
      data
        .filter((item) => item && typeof item === "object")
        .flatMap((item) => Object.keys(item))
    ),
  ];

  if (columns.length === 0) {
    return (
      <ul className="data-list">
        {data.map((item, index) => (
          <li key={index}>{formatValue(item)}</li>
        ))}
      </ul>
    );
  }

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>
                {column.replaceAll("_", " ")}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {data.map((item, index) => (
            <tr key={getTicketId(item) ?? index}>
              {columns.map((column) => (
                <td key={column}>
                  {formatValue(item?.[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function App() {
  const [analysis, setAnalysis] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [bottlenecks, setBottlenecks] = useState([]);
  const [recommendations, setRecommendations] = useState([]);

  // Anomaly Detection
  const [anomalies, setAnomalies] = useState([]);
  const [anomalySummary, setAnomalySummary] = useState(null);

  // Root Cause Analysis
  const [rootCauseSummary, setRootCauseSummary] = useState(null);
  const [rootCauseResults, setRootCauseResults] = useState([]);
  const [rootCauseError, setRootCauseError] = useState("");

  // Dashboard loading and errors
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Add New Ticket
  const [newTicket, setNewTicket] = useState({
    ticket_id: "",
    process_name: "IT Support",
    status: "Open",
    priority: "Medium",
    delay_hours: 0,
  });

  const [savingTicket, setSavingTicket] = useState(false);
  const [ticketMessage, setTicketMessage] = useState("");

  // AI Delay Prediction
  const [predictionForm, setPredictionForm] = useState({
    priority: "High",
    department: "Development",
    current_stage: "Developer Assigned",
    total_activities: 7,
    elapsed_hours: 20,
    assigned_workload: 8,
  });

  const [prediction, setPrediction] = useState(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState("");

  // Load old dataset tickets and MySQL tickets
  async function loadTickets() {
    const [oldResponse, databaseResponse] = await Promise.all([
      fetch(`${API_URL}/tickets`),
      fetch(`${API_URL}/database/tickets`),
    ]);

    if (!oldResponse.ok || !databaseResponse.ok) {
      throw new Error("Could not load all tickets from the backend.");
    }

    const oldData = getArray(await oldResponse.json());
    const databaseData = getArray(await databaseResponse.json());

    const combined = combineTickets(oldData, databaseData);
    setTickets(combined);

    return combined;
  }

  // Load all dashboard data
  async function loadDashboard() {
    setRefreshing(true);
    setError("");

    try {
      const endpoints = [
        ["analysis", `${API_URL}/process-analysis`],
        ["bottlenecks", `${API_URL}/bottlenecks`],
        ["recommendations", `${API_URL}/recommendations`],
        ["anomalies", `${API_URL}/anomalies`],
      ];

      const responses = await Promise.all(
        endpoints.map(async ([name, url]) => {
          const response = await fetch(url);

          if (!response.ok) {
            throw new Error(`${name} API failed: ${response.status}`);
          }

          return response.json();
        })
      );

      const [
        analysisData,
        bottleneckData,
        recommendationData,
        anomalyData,
      ] = responses;

      setAnalysis(analysisData);
      setBottlenecks(getArray(bottleneckData));
      setRecommendations(getArray(recommendationData));

      setAnomalySummary(anomalyData);
      setAnomalies(getArray(anomalyData?.anomalies));

      // Root Cause Analysis loads independently
      try {
        const rootResponse = await fetch(
          `${API_URL}/root-cause-analysis`
        );

        if (!rootResponse.ok) {
          throw new Error(
            `Root Cause API failed: ${rootResponse.status}`
          );
        }

        const rootData = await rootResponse.json();

        setRootCauseSummary(rootData);
        setRootCauseResults(getArray(rootData));
        setRootCauseError("");
      } catch (rootErr) {
        console.error("Root Cause Analysis Error:", rootErr);

        setRootCauseError(
          `${rootErr.message}. Check the backend endpoint.`
        );
      }

      await loadTickets();
    } catch (err) {
      console.error("Dashboard API Error:", err);

      setError(
        `${err.message}. Check that the backend is running and the API endpoints are correct.`
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  const scrollToSection = (sectionId) => {
    document.getElementById(sectionId)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };

  // Add a new ticket to MySQL
  const handleAddTicket = async (event) => {
    event.preventDefault();

    setSavingTicket(true);
    setTicketMessage("");

    try {
      const ticketId = newTicket.ticket_id.trim();

      if (!ticketId) {
        throw new Error("Please enter a Ticket ID.");
      }

      const response = await fetch(`${API_URL}/database/tickets`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          ...newTicket,
          ticket_id: ticketId,
          delay_hours: Number(newTicket.delay_hours),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Could not save ticket."
        );
      }

      // Refresh the dashboard after saving
      await loadDashboard();

      setTicketMessage("Ticket saved successfully!");

      setNewTicket({
        ticket_id: "",
        process_name: "IT Support",
        status: "Open",
        priority: "Medium",
        delay_hours: 0,
      });
    } catch (err) {
      setTicketMessage(`Error: ${err.message}`);
    } finally {
      setSavingTicket(false);
    }
  };

  // Predict ticket delay
  const handlePredictDelay = async (event) => {
    event.preventDefault();

    setPredictionLoading(true);
    setPredictionError("");
    setPrediction(null);

    try {
      const response = await fetch(`${API_URL}/predict-delay`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          ...predictionForm,
          total_activities: Number(
            predictionForm.total_activities
          ),
          elapsed_hours: Number(predictionForm.elapsed_hours),
          assigned_workload: Number(
            predictionForm.assigned_workload
          ),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Prediction request failed."
        );
      }

      setPrediction(data.result);
    } catch (err) {
      setPredictionError(
        `${err.message}. Please check that the backend is running.`
      );
    } finally {
      setPredictionLoading(false);
    }
  };

  const totalTickets = tickets.length;
  const totalActivities = analysis?.total_activities ?? "N/A";
  const averageHours =
    analysis?.average_processing_hours ?? "N/A";

  if (loading) {
    return (
      <main className="dashboard">
        <header className="dashboard-header">
          <div>
            <h1>AI Process Intelligence</h1>
            <p>Loading your process analytics...</p>
          </div>
        </header>

        <div className="status-message">
          Connecting to backend API...
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard">
      {/* Dashboard Header and Refresh Button */}
      <header
        className="dashboard-header"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "20px",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1>AI Process Intelligence</h1>
          <p>
            Monitor tickets, identify bottlenecks, and improve business
            processes.
          </p>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "14px",
            flexWrap: "wrap",
          }}
        >
          <span className="api-status">
            <span className="status-dot" />
            {refreshing ? "Updating dashboard..." : "Dashboard loaded"}
          </span>

          <button
            type="button"
            onClick={loadDashboard}
            disabled={refreshing}
            style={{
              padding: "12px 20px",
              border: "none",
              borderRadius: "9px",
              background: refreshing ? "#818cf8" : "#6366f1",
              color: "#fff",
              fontWeight: 700,
              cursor: refreshing ? "wait" : "pointer",
            }}
          >
            {refreshing ? "Refreshing..." : "↻ Refresh Data"}
          </button>
        </div>
      </header>

      {error && (
        <div className="status-message error-message" role="alert">
          {error}
        </div>
      )}

      {/* Dashboard Summary Cards */}
      <section
        className="dashboard-grid"
        aria-label="Dashboard summary"
      >
        <article
          className="dashboard-card summary-card"
          role="button"
          tabIndex={0}
          onClick={() => scrollToSection("tickets")}
        >
          <p>Total Tickets</p>
          <strong>{totalTickets}</strong>
          <span>View ticket overview →</span>
        </article>

        <article
          className="dashboard-card summary-card"
          role="button"
          tabIndex={0}
          onClick={() => scrollToSection("analysis")}
        >
          <p>Total Activities</p>
          <strong>{totalActivities}</strong>
          <span>Explore process metrics →</span>
        </article>

        <article
          className="dashboard-card summary-card"
          role="button"
          tabIndex={0}
          onClick={() => scrollToSection("bottlenecks")}
        >
          <p>Bottleneck Stages</p>
          <strong>{bottlenecks.length}</strong>
          <span>View process delays →</span>
        </article>

        <article
          className="dashboard-card summary-card"
          role="button"
          tabIndex={0}
          onClick={() => scrollToSection("anomalies")}
        >
          <p>Anomalies Detected</p>
          <strong>{anomalySummary?.anomaly_count ?? "N/A"}</strong>
          <span>View unusual tickets →</span>
        </article>

        <article
          className="dashboard-card summary-card"
          role="button"
          tabIndex={0}
          onClick={() => scrollToSection("root-cause-analysis")}
        >
          <p>Root Cause Analysis</p>
          <strong>
            {rootCauseSummary?.tickets_with_possible_causes ?? "N/A"}
          </strong>
          <span>Explore possible delay causes →</span>
        </article>

        <article
          className="dashboard-card summary-card"
          role="button"
          tabIndex={0}
          onClick={() => scrollToSection("recommendations")}
        >
          <p>Recommendations</p>
          <strong>{recommendations.length}</strong>
          <span>Explore improvements →</span>
        </article>

        <article className="dashboard-card summary-card">
          <p>Average Processing Time</p>
          <strong>{averageHours}</strong>
          <span>Hours per ticket</span>
        </article>

        <article className="dashboard-card summary-card">
          <p>Departments</p>
          <strong>{analysis?.total_departments ?? "N/A"}</strong>
          <span>Across the process</span>
        </article>

        <article
          className="dashboard-card summary-card"
          role="button"
          tabIndex={0}
          onClick={() => scrollToSection("delay-prediction")}
        >
          <p>AI Delay Prediction</p>
          <strong>AI</strong>
          <span>Estimate ticket delay risk →</span>
        </article>
      </section>

      {/* Process Analysis */}
      <section
        id="analysis"
        className="dashboard-card dashboard-section"
      >
        <h2>Process Analysis</h2>
        <p className="section-description">
          Key metrics from your process analysis API.
        </p>

        {analysis && typeof analysis === "object" ? (
          <div className="metrics-grid">
            {Object.entries(analysis).map(([key, value]) => (
              <div className="metric-item" key={key}>
                <span>{key.replaceAll("_", " ")}</span>
                <strong>{formatValue(value)}</strong>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-message">
            No analysis data available.
          </p>
        )}
      </section>

      {/* Add New Ticket */}
      <section
        id="add-ticket"
        className="dashboard-card dashboard-section"
      >
        <h2>Add New Ticket</h2>
        <p className="section-description">
          Add a ticket and save it in the MySQL database.
        </p>

        <form
          onSubmit={handleAddTicket}
          style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "18px",
          }}
        >
          <label style={{ display: "grid", gap: "8px", fontWeight: 600 }}>
            Ticket ID
            <input
              required
              maxLength={50}
              value={newTicket.ticket_id}
              placeholder="e.g. TKT-1002"
              onChange={(event) =>
                setNewTicket({
                  ...newTicket,
                  ticket_id: event.target.value,
                })
              }
              style={{
                padding: "12px",
                borderRadius: "8px",
                border: "1px solid #d9dce8",
              }}
            />
          </label>

          <label style={{ display: "grid", gap: "8px", fontWeight: 600 }}>
            Process Name
            <select
              value={newTicket.process_name}
              onChange={(event) =>
                setNewTicket({
                  ...newTicket,
                  process_name: event.target.value,
                })
              }
              style={{
                padding: "12px",
                borderRadius: "8px",
                border: "1px solid #d9dce8",
              }}
            >
              <option>IT Support</option>
              <option>Development</option>
              <option>Testing</option>
            </select>
          </label>

          <label style={{ display: "grid", gap: "8px", fontWeight: 600 }}>
            Status
            <select
              value={newTicket.status}
              onChange={(event) =>
                setNewTicket({
                  ...newTicket,
                  status: event.target.value,
                })
              }
              style={{
                padding: "12px",
                borderRadius: "8px",
                border: "1px solid #d9dce8",
              }}
            >
              <option>Open</option>
              <option>In Progress</option>
              <option>Completed</option>
            </select>
          </label>

          <label style={{ display: "grid", gap: "8px", fontWeight: 600 }}>
            Priority
            <select
              value={newTicket.priority}
              onChange={(event) =>
                setNewTicket({
                  ...newTicket,
                  priority: event.target.value,
                })
              }
              style={{
                padding: "12px",
                borderRadius: "8px",
                border: "1px solid #d9dce8",
              }}
            >
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
              <option>Critical</option>
            </select>
          </label>

          <label style={{ display: "grid", gap: "8px", fontWeight: 600 }}>
            Delay Hours
            <input
              type="number"
              min="0"
              step="any"
              required
              value={newTicket.delay_hours}
              onChange={(event) =>
                setNewTicket({
                  ...newTicket,
                  delay_hours: event.target.value,
                })
              }
              style={{
                padding: "12px",
                borderRadius: "8px",
                border: "1px solid #d9dce8",
              }}
            />
          </label>

          <div style={{ gridColumn: "1 / -1" }}>
            <button
              type="submit"
              disabled={savingTicket}
              style={{
                padding: "13px 24px",
                border: "none",
                borderRadius: "9px",
                background: "#6366f1",
                color: "#fff",
                fontWeight: 700,
                cursor: savingTicket ? "wait" : "pointer",
              }}
            >
              {savingTicket ? "Saving..." : "Save Ticket"}
            </button>
          </div>
        </form>

        {ticketMessage && (
          <p role="status" style={{ marginTop: "16px" }}>
            {ticketMessage}
          </p>
        )}
      </section>

      {/* Tickets Overview */}
      <section
        id="tickets"
        className="dashboard-card dashboard-section"
      >
        <h2>Tickets Overview</h2>
        <p className="section-description">
          Review tickets from the old dataset and MySQL database.
        </p>
        <DataTable data={tickets} />
      </section>

      {/* Bottleneck Detection */}
      <section
        id="bottlenecks"
        className="dashboard-card dashboard-section"
      >
        <h2>Bottleneck Detection</h2>
        <p className="section-description">
          Identify activities with the highest average duration.
        </p>

        {bottlenecks.length > 0 &&
        bottlenecks.some((item) =>
          Number.isFinite(Number(item.average_duration_hours))
        ) ? (
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={bottlenecks}
                margin={{
                  top: 10,
                  right: 20,
                  left: 0,
                  bottom: 55,
                }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                />
                <XAxis
                  dataKey="activity"
                  interval={0}
                  angle={-25}
                  textAnchor="end"
                  height={70}
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  label={{
                    value: "Hours",
                    angle: -90,
                    position: "insideLeft",
                  }}
                />
                <Tooltip />
                <Bar
                  dataKey="average_duration_hours"
                  name="Average duration (hours)"
                  fill="#6366f1"
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="empty-message">
            No chart data available.
          </p>
        )}

        <h3>Stage Details</h3>
        <DataTable data={bottlenecks} />
      </section>

      {/* Anomaly Detection */}
      <section
        id="anomalies"
        className="dashboard-card dashboard-section"
      >
        <h2>Anomaly Detection</h2>
        <p className="section-description">
          Identify tickets with unusually long processing times using
          statistical analysis.
        </p>

        {anomalySummary ? (
          <>
            <div className="metrics-grid">
              <div className="metric-item">
                <span>Tickets Analyzed</span>
                <strong>
                  {anomalySummary.total_tickets_analyzed ?? 0}
                </strong>
              </div>

              <div className="metric-item">
                <span>Anomalies Found</span>
                <strong>{anomalySummary.anomaly_count ?? 0}</strong>
              </div>

              <div className="metric-item">
                <span>Threshold (Hours)</span>
                <strong>
                  {anomalySummary.threshold_hours ?? "N/A"}
                </strong>
              </div>
            </div>

            <h3>Unusual Tickets</h3>

            {anomalies.length > 0 ? (
              <DataTable data={anomalies} />
            ) : (
              <p className="empty-message">
                No unusual tickets found in the current dataset.
              </p>
            )}

            <p className="section-description">
              Detection method: {anomalySummary.method ?? "IQR"}
            </p>

            {anomalySummary.message && (
              <p>{anomalySummary.message}</p>
            )}
          </>
        ) : (
          <p className="empty-message">
            Anomaly analysis data is not available.
          </p>
        )}
      </section>

      {/* Root Cause Analysis */}
      <section
        id="root-cause-analysis"
        className="dashboard-card dashboard-section"
      >
        <h2>Root Cause Analysis</h2>
        <p className="section-description">
          Investigate possible reasons for ticket delays using event-log
          statistics, processing times, and activity waiting times.
        </p>

        {rootCauseError && (
          <div className="status-message error-message" role="alert">
            {rootCauseError}
          </div>
        )}

        {rootCauseSummary && (
          <>
            <div className="metrics-grid">
              <div className="metric-item">
                <span>Tickets Analyzed</span>
                <strong>
                  {rootCauseSummary.total_tickets_analyzed ?? 0}
                </strong>
              </div>

              <div className="metric-item">
                <span>Tickets with Possible Causes</span>
                <strong>
                  {rootCauseSummary.tickets_with_possible_causes ?? 0}
                </strong>
              </div>
            </div>

            {rootCauseSummary.message && (
              <p className="section-description">
                {rootCauseSummary.message}
              </p>
            )}

            <p className="section-description">
              Method:{" "}
              {rootCauseSummary.method ??
                "Rule-based event-log analysis"}
            </p>
          </>
        )}

        {rootCauseResults.length > 0 ? (
          <div className="recommendation-list">
            {rootCauseResults.map((ticket, index) => (
              <article
                className="recommendation-item"
                key={ticket.ticket_id ?? index}
              >
                <span className="recommendation-number">
                  {String(index + 1).padStart(2, "0")}
                </span>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <h3>
                    Ticket: {formatValue(ticket.ticket_id)}
                  </h3>

                  <p>
                    <strong>Priority:</strong>{" "}
                    {formatValue(ticket.priority)}
                  </p>

                  <p>
                    <strong>Status:</strong>{" "}
                    {formatValue(ticket.status)}
                  </p>

                  <p>
                    <strong>Total Activities:</strong>{" "}
                    {formatValue(ticket.total_activities)}
                  </p>

                  <p>
                    <strong>Processing Time:</strong>{" "}
                    {formatValue(ticket.processing_hours)} hours
                  </p>

                  <h4>Possible Root Causes</h4>
                  {Array.isArray(ticket.possible_root_causes) &&
                  ticket.possible_root_causes.length > 0 ? (
                    <ul>
                      {ticket.possible_root_causes.map(
                        (cause, causeIndex) => (
                          <li key={causeIndex}>{cause}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p>No specific cause identified.</p>
                  )}

                  <h4>Evidence</h4>
                  {Array.isArray(ticket.evidence) &&
                  ticket.evidence.length > 0 ? (
                    <ul>
                      {ticket.evidence.map((item, evidenceIndex) => (
                        <li key={evidenceIndex}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>No evidence available.</p>
                  )}

                  <h4>Recommendations</h4>
                  {Array.isArray(ticket.recommendations) &&
                  ticket.recommendations.length > 0 ? (
                    <ul>
                      {ticket.recommendations.map(
                        (item, recommendationIndex) => (
                          <li key={recommendationIndex}>{item}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p>No recommendations available.</p>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          !rootCauseError &&
          rootCauseSummary && (
            <p className="empty-message">
              No possible root causes were identified in the current
              dataset. This does not necessarily mean that no delays
              occurred.
            </p>
          )
        )}

        <p className="section-description">
          Note: These are possible explanations based on recorded data,
          not confirmed causes.
        </p>
      </section>

      {/* AI Delay Prediction */}
      <section
        id="delay-prediction"
        className="dashboard-card dashboard-section"
      >
        <h2>AI Delay Prediction</h2>
        <p className="section-description">
          Enter ticket details to estimate its delay risk.
        </p>

        <form
          onSubmit={handlePredictDelay}
          style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "18px",
          }}
        >
          {[
            {
              key: "priority",
              label: "Priority",
              options: ["Low", "Medium", "High", "Critical"],
            },
            {
              key: "department",
              label: "Department",
              options: ["Development", "IT Support", "Testing"],
            },
            {
              key: "current_stage",
              label: "Current Stage",
              options: [
                "Ticket Created",
                "Ticket Assigned",
                "Investigation Started",
                "Developer Assigned",
                "Fix Completed",
                "Testing Completed",
              ],
            },
          ].map((field) => (
            <label
              key={field.key}
              style={{
                display: "grid",
                gap: "8px",
                fontWeight: 600,
              }}
            >
              {field.label}

              <select
                value={predictionForm[field.key]}
                onChange={(event) =>
                  setPredictionForm({
                    ...predictionForm,
                    [field.key]: event.target.value,
                  })
                }
                style={{
                  padding: "12px",
                  borderRadius: "8px",
                  border: "1px solid #d9dce8",
                  background: "#fff",
                  color: "#202747",
                }}
              >
                {field.options.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          ))}

          {[
            {
              key: "total_activities",
              label: "Total Activities",
              min: 1,
              max: 10000,
            },
            {
              key: "elapsed_hours",
              label: "Elapsed Hours",
              min: 0,
              max: 100000,
            },
            {
              key: "assigned_workload",
              label: "Assigned Workload",
              min: 1,
              max: 10000,
            },
          ].map((field) => (
            <label
              key={field.key}
              style={{
                display: "grid",
                gap: "8px",
                fontWeight: 600,
              }}
            >
              {field.label}

              <input
                type="number"
                min={field.min}
                max={field.max}
                step={
                  field.key === "elapsed_hours" ? "any" : "1"
                }
                required
                value={predictionForm[field.key]}
                onChange={(event) =>
                  setPredictionForm({
                    ...predictionForm,
                    [field.key]: event.target.value,
                  })
                }
                style={{
                  padding: "12px",
                  borderRadius: "8px",
                  border: "1px solid #d9dce8",
                }}
              />
            </label>
          ))}

          <div style={{ gridColumn: "1 / -1" }}>
            <button
              type="submit"
              disabled={predictionLoading}
              style={{
                padding: "13px 24px",
                border: "none",
                borderRadius: "9px",
                background: "#6366f1",
                color: "#fff",
                fontWeight: 700,
                cursor: predictionLoading ? "wait" : "pointer",
              }}
            >
              {predictionLoading
                ? "Predicting..."
                : "Predict Delay"}
            </button>
          </div>
        </form>

        {predictionError && (
          <p
            role="alert"
            style={{ color: "#dc2626", marginTop: "20px" }}
          >
            {predictionError}
          </p>
        )}

        {prediction && (
          <div
            style={{
              marginTop: "24px",
              padding: "24px",
              borderRadius: "12px",
              background: "#f5f3ff",
              border: "1px solid #ddd6fe",
            }}
          >
            <h3>Prediction Result</h3>

            <p>
              Delay Probability:{" "}
              <strong
                style={{ fontSize: "28px", color: "#6366f1" }}
              >
                {prediction.delay_probability}%
              </strong>
            </p>

            <p>
              Risk Assessment:{" "}
              <strong>{prediction.prediction}</strong>
            </p>

            <p>Model: {prediction.model_type}</p>

            <p style={{ fontSize: "13px", color: "#625b71" }}>
              {prediction.disclaimer}
            </p>
          </div>
        )}
      </section>

      {/* AI Recommendations */}
      <section
        id="recommendations"
        className="dashboard-card dashboard-section"
      >
        <h2>AI Recommendations</h2>
        <p className="section-description">
          Suggested improvements returned by your backend.
        </p>

        {recommendations.length > 0 ? (
          <div className="recommendation-list">
            {recommendations.map((item, index) => (
              <article
                className="recommendation-item"
                key={index}
              >
                <span className="recommendation-number">
                  {String(index + 1).padStart(2, "0")}
                </span>

                <div>
                  {typeof item === "object" && item !== null ? (
                    Object.entries(item).map(([key, value]) => (
                      <p key={key}>
                        <strong>
                          {key.replaceAll("_", " ")}:{" "}
                        </strong>
                        {formatValue(value)}
                      </p>
                    ))
                  ) : (
                    <p>{formatValue(item)}</p>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-message">
            No recommendations available.
          </p>
        )}
      </section>

      <footer className="dashboard-footer">
        AI Process Intelligence Dashboard
      </footer>
    </main>
  );
}

export default App;
