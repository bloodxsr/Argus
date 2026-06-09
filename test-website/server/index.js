import cors from "cors";
import dotenv from "dotenv";
import express from "express";
import mongoose from "mongoose";
import path from "path";
import { fileURLToPath } from "url";

import { connectMongo } from "./db.js";
import { ReplaySession } from "./models/ReplaySession.js";
import { ReviewDecision } from "./models/ReviewDecision.js";

dotenv.config();

const app = express();
const port = Number(process.env.PORT || 4100);
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
    service: "aisos-test-website",
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

app.post("/api/scenarios/:scenarioId/run", async (req, res, next) => {
  try {
    const payload = await securityAiFetch(`/scenarios/${encodeURIComponent(req.params.scenarioId)}/run`, {
      method: "POST"
    });

    if (mongoose.connection.readyState === 1 && !payload.error) {
      await ReplaySession.create({
        scenarioId: payload.scenario.scenario_id,
        title: payload.scenario.title,
        decisionAction: payload.decision.action,
        autoExecute: payload.decision.auto_execute,
        requiresHumanApproval: payload.decision.requires_human_approval,
        payload
      });
    }

    res.json(payload);
  } catch (error) {
    next(error);
  }
});

app.get("/api/replay-sessions", async (_req, res, next) => {
  try {
    if (mongoose.connection.readyState !== 1) {
      res.json({ sessions: [] });
      return;
    }

    const sessions = await ReplaySession.find()
      .sort({ createdAt: -1 })
      .limit(25)
      .select("scenarioId title decisionAction autoExecute requiresHumanApproval createdAt")
      .lean();
    res.json({ sessions });
  } catch (error) {
    next(error);
  }
});

app.post("/api/reviews", async (req, res, next) => {
  try {
    const { incidentId, scenarioId, decision, analyst = "demo-analyst", notes = "", payload = {} } = req.body || {};
    if (!incidentId || !scenarioId || !["approved", "rejected"].includes(decision)) {
      res.status(400).json({ error: "incidentId, scenarioId, and decision approved/rejected are required." });
      return;
    }

    if (mongoose.connection.readyState !== 1) {
      res.json({
        persisted: false,
        review: { incidentId, scenarioId, analyst, decision, notes, payload }
      });
      return;
    }

    const review = await ReviewDecision.create({ incidentId, scenarioId, analyst, decision, notes, payload });
    res.json({ persisted: true, review });
  } catch (error) {
    next(error);
  }
});

app.get("/api/reviews", async (_req, res, next) => {
  try {
    if (mongoose.connection.readyState !== 1) {
      res.json({ reviews: [] });
      return;
    }
    const reviews = await ReviewDecision.find()
      .sort({ createdAt: -1 })
      .limit(25)
      .select("incidentId scenarioId analyst decision notes createdAt")
      .lean();
    res.json({ reviews });
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
  console.log(`AISOS test website API running on http://127.0.0.1:${port}`);
});
