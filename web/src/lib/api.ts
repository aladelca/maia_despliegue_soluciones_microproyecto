import {
  type ModelMetadata,
  type PredictionResponse,
  type SessionFeatures,
  modelMetadataSchema,
  predictionResponseSchema,
} from "./schemas";

const PRODUCTION_API_BASE_URL = "https://nzm0y8hoja.execute-api.us-east-1.amazonaws.com";
export const API_REQUEST_TIMEOUT_MS = 29_000;
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  (process.env.NODE_ENV === "production" ? PRODUCTION_API_BASE_URL : "http://localhost:8000");

export async function getModelMetadata(): Promise<ModelMetadata> {
  const response = await fetch(`${API_BASE_URL}/v1/model/metadata`, {
    signal: AbortSignal.timeout(API_REQUEST_TIMEOUT_MS),
  });
  if (!response.ok) {
    throw new Error(`Metadata API returned ${response.status}`);
  }
  return modelMetadataSchema.parse(await response.json());
}

export async function predictPurchase(
  features: SessionFeatures,
): Promise<PredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(features),
    signal: AbortSignal.timeout(API_REQUEST_TIMEOUT_MS),
  });
  if (!response.ok) {
    throw new Error(`Prediction API returned ${response.status}`);
  }
  return predictionResponseSchema.parse(await response.json());
}
