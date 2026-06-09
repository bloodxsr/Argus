import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:4100";
const stages = ["Telemetry", "Investigate", "Risk", "AI Decide", "Respond"];

function App() {
  const [scenarios, setScenarios] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("Loading");
  const [history, setHistory] = useState([]);
  const [mongoConnected, setMongoConnected] = useState(false);
  const [reviewStatus, setReviewStatus] = useState("");

  const selected = useMemo(
    () => scenarios.find((scenario) => scenario.scenario_id === selectedId),
    [scenarios, selectedId]
  );

  async function loadScenarios() {
    setStatus("Loading");
    const response = await fetch(`${apiBaseUrl}/api/scenarios`);
    const data = await response.json();
    setScenarios(data.scenarios || []);
    setSelectedId(data.scenarios?.[0]?.scenario_id || "");
    setStatus("Ready");
  }

  async function loadHistory() {
    const response = await fetch(`${apiBaseUrl}/api/replay-sessions`);
    const data = await response.json();
    setHistory(data.sessions || []);
  }

  async function loadHealth() {
    const response = await fetch(`${apiBaseUrl}/api/health`);
    const data = await response.json();
    setMongoConnected(Boolean(data.mongoConnected));
  }

  async function runScenario() {
    if (!selectedId) return;
    setStatus("Running");
    const response = await fetch(`${apiBaseUrl}/api/scenarios/${selectedId}/run`, { method: "POST" });
    const data = await response.json();
    setResult(data);
    setReviewStatus("");
    setStatus(data.decision.auto_execute ? "Auto response" : data.decision.requires_human_approval ? "Review required" : "Observed");
    loadHistory();
  }

  async function submitReview(decision) {
    if (!result) return;
    const response = await fetch(`${apiBaseUrl}/api/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        incidentId: result.decision.incident_id,
        scenarioId: result.scenario.scenario_id,
        decision,
        analyst: "demo-analyst",
        notes: decision === "approved" ? "Approved from test website." : "Rejected from test website.",
        payload: result
      })
    });
    const data = await response.json();
    setReviewStatus(data.persisted ? `Review ${decision} and saved` : `Review ${decision}; Mongo history disabled`);
  }

  useEffect(() => {
    Promise.all([loadHealth(), loadScenarios(), loadHistory()]).catch((error) => setStatus(error.message));
  }, []);

  return (
    <>
      <header>
        <div>
          <h1>Argus Scenario Launcher</h1>
          <p>Synthetic attack replay for the AI-native SOAR pipeline.</p>
        </div>
        <span>{status} · {mongoConnected ? "Mongo on" : "Mongo history off"}</span>
      </header>

      <main>
        <aside>
          <div className="panelHead">
            <h2>Scenarios</h2>
            <button onClick={loadScenarios}>Reload</button>
          </div>
          <div className="list">
            {scenarios.map((scenario) => (
              <button
                className={scenario.scenario_id === selectedId ? "scenario active" : "scenario"}
                key={scenario.scenario_id}
                onClick={() => {
                  setSelectedId(scenario.scenario_id);
                  setResult(null);
                }}
              >
                <strong>{scenario.title}</strong>
                <small>{scenario.description}</small>
              </button>
            ))}
          </div>
        </aside>

        <section className="workspace">
          <div className="panel">
            <div className="panelHead">
              <div>
                <h2>{selected?.title || "Select a scenario"}</h2>
                <p>{selected?.incident?.summary || "Start the Python Security AI API first."}</p>
              </div>
              <button disabled={!selectedId} onClick={runScenario}>Run</button>
            </div>
            <div className="pipeline">
              {stages.map((stage, index) => (
                <div className={result ? "stage done" : index === 0 ? "stage done" : "stage"} key={stage}>
                  <strong>{stage}</strong>
                  <small>{result ? "Complete" : index === 0 ? "Ready" : "Queued"}</small>
                </div>
              ))}
            </div>
          </div>

          <div className="metrics">
            <Metric label="Classification" value={result?.ai_result?.classification || "-"} />
            <Metric label="Confidence" value={result ? `${Math.round(result.ai_result.confidence * 100)}%` : "-"} />
            <Metric label="Action" value={result?.decision?.action || "-"} />
            <Metric label="Approval" value={result ? result.decision.requires_human_approval ? "Required" : "Not required" : "-"} />
          </div>

          {result?.decision?.requires_human_approval && (
            <div className="panel reviewPanel">
              <div>
                <h2>Human Review</h2>
                <p>{reviewStatus || "Approve or reject the recommended response."}</p>
              </div>
              <div className="reviewActions">
                <button onClick={() => submitReview("approved")}>Approve</button>
                <button className="danger" onClick={() => submitReview("rejected")}>Reject</button>
              </div>
            </div>
          )}

          <div className="panel">
            <div className="panelHead">
              <h2>Recent Replays</h2>
            </div>
            <div className="history">
              {!mongoConnected && <p>MongoDB is offline, so replay history is not being stored.</p>}
              {history.map((item) => (
                <div className="historyRow" key={item._id}>
                  <strong>{item.title}</strong>
                  <span>{item.decisionAction}</span>
                  <span>{item.autoExecute ? "auto" : item.requiresHumanApproval ? "review" : "observe"}</span>
                </div>
              ))}
            </div>
          </div>

          <pre>{JSON.stringify(result || selected || {}, null, 2)}</pre>
        </section>
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

createRoot(document.getElementById("root")).render(<App />);
