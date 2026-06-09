import mongoose from "mongoose";

const IncidentReportSchema = new mongoose.Schema(
  {
    incidentId: { type: String, required: true, index: true },
    scenarioId: { type: String, required: true, index: true },
    classification: { type: String, required: true },
    action: { type: String, required: true },
    confidence: { type: Number, required: true },
    autoExecute: { type: Boolean, required: true },
    requiresHumanApproval: { type: Boolean, required: true },
    payload: { type: Object, required: true }
  },
  { timestamps: true }
);

export const IncidentReport = mongoose.models.IncidentReport || mongoose.model("IncidentReport", IncidentReportSchema);
