import cors from "cors";
import dotenv from "dotenv";
import express from "express";
import mongoose from "mongoose";
import path from "path";
import { fileURLToPath } from "url";
import { connect, StringCodec } from "nats";

import { connectMongo } from "./db.js";
import { IncidentReport } from "./models/IncidentReport.js";

dotenv.config();

const app = express();
const port = Number(process.env.PORT || 4200);
const securityAiBaseUrl = process.env.SECURITY_AI_BASE_URL || "http://127.0.0.1:8000";
const agrusInternalToken = process.env.AGRUS_INTERNAL_TOKEN;
const corsOrigin = process.env.CORS_ORIGIN || "*";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.resolve(__dirname, "../dist");

app.use(cors({ origin: corsOrigin }));
app.use(express.json({ limit: "2mb" }));

await connectMongo(process.env.MONGO_URI);

async function securityAiFetch(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (agrusInternalToken && !headers.Authorization) {
    headers.Authorization = `Bearer ${agrusInternalToken}`;
  }

  const response = await fetch(`${securityAiBaseUrl}${path}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Security AI request failed ${response.status}: ${text}`);
  }

  return response.json();
}

app.get("/api/health", (_req, res) => {
  res.json({
    service: "agrus-report-website",
    mongoConnected: mongoose.connection.readyState === 1,
    securityAiBaseUrl
  });
});

 

app.get("/api/reports", async (_req, res, next) => {
  try {
    if (mongoose.connection.readyState !== 1) {
      res.json({ reports: [] });
      return;
    }

    const reports = await IncidentReport.find()
      .sort({ createdAt: -1 })
      .limit(25)
      .select("incidentId scenarioId classification action confidence autoExecute requiresHumanApproval createdAt")
      .lean();
    res.json({ reports });
  } catch (error) {
    next(error);
  }
});

app.get("/api/reports/:id", async (req, res, next) => {
  try {
    if (mongoose.connection.readyState !== 1) {
      res.status(503).json({ error: "MongoDB is not connected." });
      return;
    }

    const report = await IncidentReport.findById(req.params.id).lean();
    if (!report) {
      res.status(404).json({ error: "Report not found." });
      return;
    }
    res.json({ report });
  } catch (error) {
    next(error);
  }
});

app.get("/api/correlations", async (req, res, next) => {
  try {
    const data = await securityAiFetch("/correlations");
    res.json(data);
  } catch (error) { next(error); }
});

app.get("/api/baselines", async (req, res, next) => {
  try {
    const data = await securityAiFetch("/baselines");
    res.json(data);
  } catch (error) { next(error); }
});

app.get("/api/baselines/:entity_id", async (req, res, next) => {
  try {
    const data = await securityAiFetch("/baselines/" + req.params.entity_id);
    res.json(data);
  } catch (error) { next(error); }
});

app.post("/api/baselines/deviation", async (req, res, next) => {
  try {
    const data = await securityAiFetch("/baselines/deviation", { method: "POST", body: JSON.stringify(req.body) });
    res.json(data);
  } catch (error) { next(error); }
});

app.get("/api/timeline/:entity", async (req, res, next) => {
  try {
    const data = await securityAiFetch("/timeline/" + req.params.entity);
    res.json(data);
  } catch (error) { next(error); }
});

app.get("/api/containers", async (req, res, next) => {
  try {
    const data = await securityAiFetch("/containers");
    res.json(data);
  } catch (error) { next(error); }
});

app.post("/api/containers/quarantine", async (req, res, next) => {
  try {
    const data = await securityAiFetch("/containers/quarantine", { method: "POST", body: JSON.stringify(req.body) });
    res.json(data);
  } catch (error) { next(error); }
});

app.post("/api/containers/kill", async (req, res, next) => {
  try {
    const data = await securityAiFetch("/containers/kill", { method: "POST", body: JSON.stringify(req.body) });
    res.json(data);
  } catch (error) { next(error); }
});

app.use(express.static(distDir));
app.use((req, res, next) => {
  if (req.method === "GET" && req.accepts("html")) {
    res.sendFile(path.join(distDir, "index.html"));
    return;
  }
  next();
});

app.use((error, _req, res, _next) => {
  console.error(error);
  res.status(502).json({ error: error.message });
});

app.listen(port, () => {
  console.log(`AGRUS report website API running on http: 
});

 
const natsUrl = process.env.NATS_URL || "nats://127.0.0.1:4222";
connect({ servers: natsUrl }).then(nc => {
  console.log(`Connected to live NATS telemetry at ${natsUrl}`);
  const sc = StringCodec();
  nc.subscribe("incidents.scored", {
    callback: async (err, msg) => {
      if (err) return;
      try {
        const rawTelemetry = JSON.parse(sc.decode(msg.data));
        const riskScoreMap = { "PROCESS_START": 7.0, "FILE_ACCESS": 5.0, "NETWORK_CONNECT": 8.0 };
        const riskScore = riskScoreMap[rawTelemetry.event_type] || 6.0;
        const payloadStr = Object.entries(rawTelemetry.payload || {})
          .map(([k, v]) => `${k}:${v}`)
          .join(" ");
        const incidentInput = {
          incident_id: "inc-" + rawTelemetry.event_id,
          summary: `Suspicious activity from ${rawTelemetry.source}: ${rawTelemetry.event_type} on host ${rawTelemetry.host}. Payload: ${payloadStr}`,
          risk_score: riskScore,  
          asset_id: rawTelemetry.host,
          host: rawTelemetry.host,
          hour_of_day: new Date().getUTCHours(),
          labels: [rawTelemetry.source, rawTelemetry.event_type, ...Object.values(rawTelemetry.payload || {}).map(String)],
          company: "AGRUS-Customer"
        };
        
        const analysis = await securityAiFetch("/analyze", {
          method: "POST",
          body: JSON.stringify(incidentInput)
        });

        if (mongoose.connection.readyState === 1) {
          await IncidentReport.create({
            incidentId: analysis.decision.incident_id,
            scenarioId: "live-event",
            classification: analysis.ai_result.classification,
            action: analysis.decision.action,
            confidence: analysis.decision.confidence,
            autoExecute: analysis.decision.auto_execute,
            requiresHumanApproval: analysis.decision.requires_human_approval,
            payload: {
              ...analysis,
              scenario: { incident: rawTelemetry }
            }
          });
          console.log(`Ingested live threat analysis: ${analysis.decision.incident_id}`);
        }
      } catch(e) {
        console.error("Live telemetry ingest error:", e);
      }
    }
  });
}).catch(err => console.error("NATS connection failed:", err));
