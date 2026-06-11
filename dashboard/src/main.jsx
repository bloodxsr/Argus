import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:4200";
const aiBaseUrl = import.meta.env.VITE_AI_BASE_URL || "http://127.0.0.1:9000";

function App() {
  const [reports, setReports] = useState([]);
  const [correlations, setCorrelations] = useState([]);
  const [baselines, setBaselines] = useState([]);
  const [containers, setContainers] = useState([]);
  
  const [tab, setTab] = useState("active"); // 'active', 'solved', 'correlations', 'baselines', 'containers'
  const [selectedReport, setSelectedReport] = useState(null);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 3000); // Live SOC polling
    return () => clearInterval(interval);
  }, []);

  async function fetchAllData() {
    try {
      const res = await fetch(`${apiBaseUrl}/api/reports`);
      const data = await res.json();
      setReports(data.reports || []);
    } catch (e) {
      console.error("Failed to load reports", e);
    }

    try {
      const res = await fetch(`${aiBaseUrl}/correlations`);
      const data = await res.json();
      setCorrelations(data.correlations || []);
    } catch (e) {
      console.error("Failed to load correlations", e);
    }

    try {
      const res = await fetch(`${aiBaseUrl}/baselines`);
      const data = await res.json();
      setBaselines(data.entities || []);
    } catch (e) {
      console.error("Failed to load baselines", e);
    }

    try {
      const res = await fetch(`${aiBaseUrl}/containers`);
      const data = await res.json();
      setContainers(data.containers || []);
    } catch (e) {
      console.error("Failed to load containers", e);
    }
  }

  async function viewReportDetails(id) {
    try {
      const res = await fetch(`${apiBaseUrl}/api/reports/${id}`);
      const data = await res.json();
      setSelectedReport(data.report);
    } catch (e) {
      console.error(e);
    }
  }

  const activeProblems = reports.filter((r) => r.requiresHumanApproval || !r.autoExecute);
  const solvedProblems = reports.filter((r) => r.autoExecute && !r.requiresHumanApproval);

  return (
    <div className="container">
      <header>
        <div>
          <h1>AGRUS Security Dashboard</h1>
          <p>Real-time autonomous incident response and SOC escalation.</p>
        </div>
        <div className="live-feed">
          <div className="dot"></div>
          <span>LIVE FEED</span>
        </div>
      </header>

      <div className="tabs">
        <button 
          className={`tab ${tab === 'active' ? 'active' : ''}`} 
          onClick={() => setTab('active')}
        >
          Active Incidents ({activeProblems.length})
        </button>
        <button 
          className={`tab ${tab === 'solved' ? 'active' : ''}`} 
          onClick={() => setTab('solved')}
        >
          Resolved ({solvedProblems.length})
        </button>
        <button 
          className={`tab ${tab === 'correlations' ? 'active' : ''}`} 
          onClick={() => setTab('correlations')}
        >
          APT Correlations ({correlations.length})
        </button>
        <button 
          className={`tab ${tab === 'baselines' ? 'active' : ''}`} 
          onClick={() => setTab('baselines')}
        >
          UEBA Baselines ({baselines.length})
        </button>
        <button 
          className={`tab ${tab === 'containers' ? 'active' : ''}`} 
          onClick={() => setTab('containers')}
        >
          Containers ({containers.length})
        </button>
      </div>

      <div className="grid">
        {tab === 'active' && activeProblems.length === 0 && (
          <p style={{color: 'var(--text-secondary)'}}>No active incidents at the moment.</p>
        )}
        {tab === 'active' && activeProblems.map((report) => (
          <div key={report._id} className="card" onClick={() => viewReportDetails(report._id)}>
            <div className="card-header">
              <h3>{report.incidentId}</h3>
              <span className="badge active-badge">Requires Review</span>
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

        {tab === 'solved' && solvedProblems.length === 0 && (
          <p style={{color: 'var(--text-secondary)'}}>No solved incidents at the moment.</p>
        )}
        {tab === 'solved' && solvedProblems.map((report) => (
          <div key={report._id} className="card" onClick={() => viewReportDetails(report._id)}>
            <div className="card-header">
              <h3>{report.incidentId}</h3>
              <span className="badge solved-badge">Auto-Resolved</span>
            </div>
            <div className="card-body">
              <p><strong>Threat:</strong> {report.classification}</p>
              <p><strong>Action Taken:</strong> {report.action}</p>
            </div>
            <div className="card-footer">
              <span>Confidence: {Math.round(report.confidence * 100)}%</span>
              <span>{new Date(report.createdAt).toLocaleTimeString()}</span>
            </div>
          </div>
        ))}

        {tab === 'correlations' && correlations.length === 0 && (
          <p style={{color: 'var(--text-secondary)'}}>No active correlations detected.</p>
        )}
        {tab === 'correlations' && correlations.map((corr) => (
          <div key={corr.correlation_id} className="card">
            <div className="card-header">
              <h3>Entity: {corr.entity}</h3>
              <span className={`badge ${corr.severity === 'CRITICAL' ? 'active-badge' : 'neutral-badge'}`}>{corr.severity}</span>
            </div>
            <div className="card-body">
              <p><strong>Kill Chain Coverage:</strong> {Math.round(corr.kill_chain_coverage * 100)}%</p>
              <p><strong>Stages:</strong> {corr.kill_chain_stages.join(' → ')}</p>
              <p><strong>Summary:</strong> {corr.summary}</p>
            </div>
            <div className="card-footer">
              <span>{corr.event_count} associated events</span>
              <span>Span: {corr.time_span_hours} hours</span>
            </div>
          </div>
        ))}

        {tab === 'baselines' && baselines.length === 0 && (
          <p style={{color: 'var(--text-secondary)'}}>No baselines established yet.</p>
        )}
        {tab === 'baselines' && baselines.map((baseline) => (
          <div key={baseline.entity_id} className="card">
            <div className="card-header">
              <h3>{baseline.entity_id}</h3>
              <span className="badge neutral-badge">Monitored</span>
            </div>
            <div className="card-body">
              <p><strong>Total Events:</strong> {baseline.event_count}</p>
              <p>Collecting behavioral telemetry for UEBA deviation analysis.</p>
            </div>
          </div>
        ))}

        {tab === 'containers' && containers.length === 0 && (
          <p style={{color: 'var(--text-secondary)'}}>No running containers detected.</p>
        )}
        {tab === 'containers' && containers.map((container) => (
          <div key={container.id} className="card">
            <div className="card-header">
              <h3>{container.name}</h3>
              <span className="badge neutral-badge">{container.status}</span>
            </div>
            <div className="card-body">
              <p><strong>Image:</strong> {container.image}</p>
              <p><strong>PID:</strong> {container.pid}</p>
              <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
                <button className="action-btn" onClick={() => fetch(`${aiBaseUrl}/containers/quarantine`, { method: 'POST', body: JSON.stringify({container_id: container.id}), headers: {'Content-Type': 'application/json'} })}>Quarantine</button>
                <button className="action-btn" style={{color: 'var(--accent-active)', borderColor: 'var(--accent-active)'}} onClick={() => fetch(`${aiBaseUrl}/containers/kill`, { method: 'POST', body: JSON.stringify({container_id: container.id}), headers: {'Content-Type': 'application/json'} })}>Kill</button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {selectedReport && (
        <div className="modal-overlay" onClick={() => setSelectedReport(null)}>
          <div className="report-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>{selectedReport.incidentId}</h2>
                <span className={`badge ${selectedReport.autoExecute ? 'solved-badge' : 'active-badge'}`}>
                  {selectedReport.autoExecute ? 'Resolved Autonomously' : 'Human Escalation Required'}
                </span>
              </div>
              <button className="close-btn" onClick={() => setSelectedReport(null)}>✕</button>
            </div>

            <div className="modal-body">
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
                    <span className="data-label">Proposed Action</span>
                    <span className="data-val">{selectedReport.action}</span>
                  </div>
                  <div className="data-item" style={{ gridColumn: 'span 2' }}>
                    <span className="data-label">Reasoning Engine</span>
                    <span className="data-val" style={{color: 'var(--text-secondary)'}}>
                      {selectedReport.payload?.decision?.reasoning || "Analyzing network telemetry against MITRE ATT&CK models..."}
                    </span>
                  </div>
                </div>
              </div>

              <div className="report-section">
                <h4>Raw Telemetry Payload</h4>
                <pre className="json-view">
                  {JSON.stringify(selectedReport.payload?.scenario?.incident || selectedReport, null, 2)}
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
