import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:4100";

function App() {
  const [scenarios, setScenarios] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/scenarios`);
        const data = await response.json();
        setScenarios(data.scenarios || []);
        if (data.scenarios?.length > 0) {
          setSelectedId(data.scenarios[0].scenario_id);
        }
      } catch (e) {
        setError("Failed to connect to the backend API.");
      }
    }
    load();
  }, []);

  async function runScenario() {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/scenarios/${selectedId}/run`, {
        method: "POST"
      });
      const data = await response.json();
      if (!response.ok || data.error) {
        setError(data.error || "Execution failed");
      } else {
        setResult(data);
      }
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  }

  const selectedScenarioInfo = scenarios.find(s => s.scenario_id === selectedId);

  return (
    <div className="container">
      <header>
        <h1>AGRUS Attack Simulator</h1>
        <p>Inject live telemetry scenarios directly into the AI Security Engine.</p>
      </header>

      <main className="glass-panel">
        <div className="scenario-selector">
          <label>Select Attack Vector:</label>
          <select 
            className="custom-select" 
            value={selectedId} 
            onChange={(e) => setSelectedId(e.target.value)}
            disabled={loading}
          >
            {scenarios.map((s) => (
              <option key={s.scenario_id} value={s.scenario_id}>
                {s.title}
              </option>
            ))}
          </select>
          {selectedScenarioInfo && (
            <p style={{color: 'var(--text-secondary)', marginTop: '-10px', marginBottom: '10px', fontSize: '0.95rem'}}>
              {selectedScenarioInfo.description}
            </p>
          )}
        </div>

        <button 
          className="launch-btn" 
          onClick={runScenario} 
          disabled={loading || !selectedId}
          style={{ width: '100%' }}
        >
          {loading ? "Injecting Payload..." : "Simulate Attack"}
        </button>

        {(result || error) && (
          <div className="results-area">
            <h3>{error ? "⚠ Execution Error" : "✓ AI Engine Response"}</h3>
            <pre className={`json-block ${error ? 'error' : ''}`}>
              {error ? error : JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
