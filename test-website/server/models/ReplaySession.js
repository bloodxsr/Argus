import mongoose from "mongoose";

const ReplaySessionSchema = new mongoose.Schema(
  {
    scenarioId: { type: String, required: true, index: true },
    title: { type: String, required: true },
    decisionAction: { type: String, required: true },
    autoExecute: { type: Boolean, required: true },
    requiresHumanApproval: { type: Boolean, required: true },
    payload: { type: Object, required: true }
  },
  { timestamps: true }
);

export const ReplaySession = mongoose.models.ReplaySession || mongoose.model("ReplaySession", ReplaySessionSchema);
