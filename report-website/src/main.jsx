import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:4200";

function App() {
  const [reports, setReports] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState("");
  const [tab, setTab] = useState("active"); // 'active' or 'solved'
  const [selectedReport, setSelectedReport] = useState(null);
  const [loadingModal, setLoadingModal] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    fetchReports();
    fetchScenarios();
  }, []);

  async function fetchReports() {
    try {
      const res = await fetch(`${apiBaseUrl}/api/reports`);
      const data = await res.json();
      setReports(data.reports || []);
    } catch (e) {
      console.error("Failed to load reports", e);
    }
  }

  async function fetchScenarios() {
    try {
      const res = await fetch(`${apiBaseUrl}/api/scenarios`);
      const data = await res.json();
      setScenarios(data.scenarios || []);
      if (data.scenarios?.length > 0) {
        setSelectedScenarioId(data.scenarios[0].scenario_id);
      }
    } catch (e) {
      console.error("Failed to load scenarios", e);
    }
  }

  async function generateReport() {
    if (!selectedScenarioId) return;
    setIsGenerating(true);
    try {
      await fetch(`${apiBaseUrl}/api/reports/from-scenario/${selectedScenarioId}`, { method: "POST" });
      await fetchReports();
    } catch (e) {
      console.error(e);
    }
    setIsGenerating(false);
  }

  async function viewReportDetails(id) {
    setLoadingModal(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/reports/${id}`);
      const data = await res.json();
      setSelectedReport(data.report);
    } catch (e) {
      console.error(e);
    }
    setLoadingModal(false);
  }

  const activeProblems = reports.filter((r) => r.requiresHumanApproval || !r.autoExecute);
  const solvedProblems = reports.filter((r) => r.autoExecute && !r.requiresHumanApproval);

  const displayedReports = tab === "active" ? activeProblems : solvedProblems;

  return (
    <div className="container">
      <header>
        <div>
          <h1>AGRUS Security Dashboard</h1>
          <p>Real-time incident reports, autonomous actions, and SOC escalations.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <select 
            style={{ padding: '10px', borderRadius: '8px', background: 'rgba(255,255,255,0.1)', color: 'white', border: '1px solid rgba(255,255,255,0.2)', fontFamily: 'var(--font-main)' }}
            value={selectedScenarioId} 
            onChange={(e) => setSelectedScenarioId(e.target.value)}
          >
            {scenarios.map(s => <option key={s.scenario_id} value={s.scenario_id} style={{color: 'black'}}>{s.title}</option>)}
          </select>
          <button className="generate-btn" onClick={generateReport} disabled={isGenerating}>
            {isGenerating ? "Simulating..." : "Trigger Incident"}
          </button>
        </div>
      </header>

      <div className="tabs">
        <button 
          className={`tab ${tab === 'active' ? 'active' : ''}`} 
          data-type="active"
          onClick={() => setTab('active')}
        >
          Active Problems ({activeProblems.length})
        </button>
        <button 
          className={`tab ${tab === 'solved' ? 'active' : ''}`} 
          data-type="solved"
          onClick={() => setTab('solved')}
        >
          Solved Problems ({solvedProblems.length})
        </button>
      </div>

      <div className="report-grid">
        {displayedReports.length === 0 && (
          <p style={{color: 'var(--text-secondary)'}}>No {tab} problems at the moment.</p>
        )}
        {displayedReports.map((report) => (
          <div 
            key={report._id} 
            className={`glass-card ${tab === 'active' ? 'active-card' : 'solved-card'}`}
            onClick={() => viewReportDetails(report._id)}
          >
            <div className="card-header">
              <h3>{report.incidentId}</h3>
              <span className={`badge ${tab === 'active' ? 'active-badge' : 'solved-badge'}`}>
                {tab === 'active' ? 'Requires Review' : 'Auto-Resolved'}
              </span>
            </div>
            <div className="card-body">
              <p><strong>Threat:</strong> {report.classification}</p>
              <p><strong>Proposed Action:</strong> {report.action}</p>
            </div>
            <div className="card-footer">
              <span>Confidence: {Math.round(report.confidence * 100)}%</span>
              <span>{new Date(report.createdAt).toLocaleTimeString()}</span>
            </div>
          </div>
        ))}
      </div>

      {selectedReport && (
        <div className="modal-overlay" onClick={() => setSelectedReport(null)}>
          <div className="report-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>Incident: {selectedReport.incidentId}</h2>
                <span className={`badge ${selectedReport.autoExecute ? 'solved-badge' : 'active-badge'}`}>
                  {selectedReport.autoExecute ? 'Resolved Autonomously' : 'Human Escalation Required'}
                </span>
              </div>
              <button className="close-btn" onClick={() => setSelectedReport(null)}>✕</button>
            </div>

            <div className="modal-body">
              {/* If Solved, show the Solution prominently */}
              {selectedReport.autoExecute && (
                <div className="report-section solution-box">
                  <h4>✓ Solution Applied</h4>
                  <div className="data-grid">
                    <div className="data-item">
                      <span className="data-label">Action Taken</span>
                      <span className="data-val">{selectedReport.payload?.action_record?.action_type || selectedReport.action}</span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">Result</span>
                      <span className="data-val">{selectedReport.payload?.action_record?.result || "Threat Neutralized successfully. No downtime."}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* If Active, show Warning prominently */}
              {!selectedReport.autoExecute && (
                <div className="report-section warning-box">
                  <h4>⚠ Human Review Required</h4>
                  <p style={{color: 'var(--text-secondary)', lineHeight: '1.5'}}>
                    The AI Engine detected a threat but was constrained by Blast Radius Logic. 
                    It is awaiting a human SOC analyst to approve the execution of: <strong>{selectedReport.action}</strong>
                  </p>
                </div>
              )}

              <div className="report-section">
                <h4>AI Analysis</h4>
                <div className="data-grid">
                  <div className="data-item">
                    <span className="data-label">Classification</span>
                    <span className="data-val">{selectedReport.classification}</span>
                  </div>
                  <div className="data-item">
                    <span className="data-label">AI Confidence</span>
                    <span className="data-val">{Math.round(selectedReport.confidence * 100)}%</span>
                  </div>
                  <div className="data-item" style={{ gridColumn: 'span 2' }}>
                    <span className="data-label">Reasoning Engine</span>
                    <span className="data-val" style={{fontSize: '1rem', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.5'}}>
                      {selectedReport.payload?.decision?.reasoning || "Analyzing network telemetry against MITRE ATT&CK models..."}
                    </span>
                  </div>
                </div>
              </div>

              <div className="report-section">
                <h4>Raw Telemetry Payload</h4>
                <pre className="json-view">
                  {JSON.stringify(selectedReport.payload?.scenario?.incident || {}, null, 2)}
                </pre>
              </div>

            </div>
          </div>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
