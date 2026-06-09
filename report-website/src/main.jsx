import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:4200";

function App() {
  const [scenarios, setScenarios] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [report, setReport] = useState(null);
  const [reports, setReports] = useState([]);
  const [status, setStatus] = useState("Loading");
  const [mongoConnected, setMongoConnected] = useState(false);

  async function loadHealth() {
    const response = await fetch(`${apiBaseUrl}/api/health`);
    const data = await response.json();
    setMongoConnected(Boolean(data.mongoConnected));
  }

  async function loadScenarios() {
    const response = await fetch(`${apiBaseUrl}/api/scenarios`);
    const data = await response.json();
    setScenarios(data.scenarios || []);
    setSelectedId(data.scenarios?.[0]?.scenario_id || "");
  }

  async function loadReports() {
    const response = await fetch(`${apiBaseUrl}/api/reports`);
    const data = await response.json();
    setReports(data.reports || []);
  }

  async function generateReport() {
    if (!selectedId) return;
    setStatus("Generating");
    const response = await fetch(`${apiBaseUrl}/api/reports/from-scenario/${selectedId}`, { method: "POST" });
    const data = await response.json();
    setReport(data.payload);
    setStatus(data.payload.decision.auto_execute ? "Auto response" : data.payload.decision.requires_human_approval ? "Review required" : "Observed");
    loadReports();
  }

  useEffect(() => {
    Promise.all([loadHealth(), loadScenarios(), loadReports()])
      .then(() => setStatus("Ready"))
      .catch((error) => setStatus(error.message));
  }, []);

  return (
    <>
      <header>
        <div>
          <h1>Argus Incident Reports</h1>
          <p>Audit view for decisions, response actions, and human review state.</p>
        </div>
        <span>{status} · {mongoConnected ? "Mongo on" : "Mongo reports off"}</span>
      </header>

      <main>
        <section className="toolbar">
          <div>
            <h2>Generate Report</h2>
            <p>Reports are created from the same replay endpoint used by the test website.</p>
          </div>
          <div className="controls">
            <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
              {scenarios.map((scenario) => (
                <option key={scenario.scenario_id} value={scenario.scenario_id}>{scenario.title}</option>
              ))}
            </select>
            <button onClick={generateReport}>Generate</button>
          </div>
        </section>

        <section className="metrics">
          <Metric label="Incident" value={report?.decision?.incident_id || "-"} />
          <Metric label="Classification" value={report?.ai_result?.classification || "-"} />
          <Metric label="Action" value={report?.decision?.action || "-"} />
          <Metric label="Confidence" value={report ? `${Math.round(report.decision.confidence * 100)}%` : "-"} />
        </section>

        <section>
          <div className="panelHead">
            <h2>Timeline</h2>
          </div>
          <div className="timeline">
            <TimelineRow label="Telemetry" value={report ? `${report.event_count} event(s) from ${report.scenario.incident.host}` : "Waiting"} />
            <TimelineRow label="AI Result" value={report?.ai_result?.classification || "Waiting"} />
            <TimelineRow label="Decision" value={report?.decision?.reasoning || "Waiting"} />
            <TimelineRow label="Action" value={report ? `${report.action_record.action_type}: ${report.action_record.result}` : "Waiting"} />
            <TimelineRow label="Human Audit" value={report?.review_decision?.notes || "Audit available after autonomous action."} />
          </div>
        </section>

        <section>
          <div className="panelHead">
            <h2>Recent Reports</h2>
          </div>
          <div className="reportList">
            {!mongoConnected && <p>MongoDB is offline, so generated reports are not being stored.</p>}
            {reports.map((item) => (
              <div className="reportRow" key={item._id}>
                <strong>{item.incidentId}</strong>
                <span>{item.classification}</span>
                <span>{item.action}</span>
              </div>
            ))}
          </div>
        </section>

        <pre>{JSON.stringify(report || {}, null, 2)}</pre>
      </main>
    </>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TimelineRow({ label, value }) {
  return (
    <div className="timelineRow">
      <strong>{label}</strong>
      <span>{value}</span>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
