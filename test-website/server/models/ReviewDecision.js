import mongoose from "mongoose";

const ReviewDecisionSchema = new mongoose.Schema(
  {
    incidentId: { type: String, required: true, index: true },
    scenarioId: { type: String, required: true, index: true },
    analyst: { type: String, required: true },
    decision: { type: String, enum: ["approved", "rejected"], required: true },
    notes: { type: String, default: "" },
    payload: { type: Object, required: true }
  },
  { timestamps: true }
);

export const ReviewDecision = mongoose.models.ReviewDecision || mongoose.model("ReviewDecision", ReviewDecisionSchema);
