import {
  type PredictionResponse,
  type SessionFeatures,
  predictionResponseSchema,
} from "./schemas";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function predictPurchase(
  features: SessionFeatures,
): Promise<PredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(features),
    signal: AbortSignal.timeout(15_000),
  });
  if (!response.ok) {
    throw new Error(`Prediction API returned ${response.status}`);
  }
  return predictionResponseSchema.parse(await response.json());
}
