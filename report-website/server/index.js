import cors from "cors";
import dotenv from "dotenv";
import express from "express";
import mongoose from "mongoose";
import path from "path";
import { fileURLToPath } from "url";

import { connectMongo } from "./db.js";
import { IncidentReport } from "./models/IncidentReport.js";

dotenv.config();

const app = express();
const port = Number(process.env.PORT || 4200);
const securityAiBaseUrl = process.env.SECURITY_AI_BASE_URL || "http://127.0.0.1:8000";
const corsOrigin = process.env.CORS_ORIGIN || "*";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.resolve(__dirname, "../dist");

app.use(cors({ origin: corsOrigin }));
app.use(express.json({ limit: "2mb" }));

await connectMongo(process.env.MONGO_URI);

async function securityAiFetch(path, options = {}) {
  const response = await fetch(`${securityAiBaseUrl}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
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

app.get("/api/scenarios", async (_req, res, next) => {
  try {
    res.json(await securityAiFetch("/scenarios"));
  } catch (error) {
    next(error);
  }
});

app.post("/api/reports/from-scenario/:scenarioId", async (req, res, next) => {
  try {
    const payload = await securityAiFetch(`/scenarios/${encodeURIComponent(req.params.scenarioId)}/run`, {
      method: "POST"
    });

    if (payload.error) {
      res.status(404).json(payload);
      return;
    }

    let report = null;
    if (mongoose.connection.readyState === 1) {
      report = await IncidentReport.create({
        incidentId: payload.decision.incident_id,
        scenarioId: payload.scenario.scenario_id,
        classification: payload.ai_result.classification,
        action: payload.decision.action,
        confidence: payload.decision.confidence,
        autoExecute: payload.decision.auto_execute,
        requiresHumanApproval: payload.decision.requires_human_approval,
        payload
      });
    }

    res.json({ reportId: report?._id || null, payload });
  } catch (error) {
    next(error);
  }
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
  console.log(`AGRUS report website API running on http://127.0.0.1:${port}`);
});
