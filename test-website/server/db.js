import mongoose from "mongoose";

export async function connectMongo(uri) {
  if (!uri) {
    console.warn("MONGO_URI is not set; replay sessions will not be persisted.");
    return false;
  }

  try {
    await mongoose.connect(uri);
    console.log("MongoDB connected");
    return true;
  } catch (error) {
    console.warn(`MongoDB unavailable: ${error.message}`);
    return false;
  }
}
