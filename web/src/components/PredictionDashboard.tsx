"use client";

import useSWR from "swr";

import { getModelMetadata } from "../lib/api";
import type { ModelMetadata } from "../lib/schemas";
import { ModelSummary } from "./ModelSummary";
import { PredictionForm } from "./PredictionForm";

type PredictionDashboardProps = {
  loadMetadata?: () => Promise<ModelMetadata>;
};

export function PredictionDashboard({
  loadMetadata = getModelMetadata,
}: PredictionDashboardProps) {
  const { data, error, isLoading } = useSWR("model-metadata", loadMetadata, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return (
    <>
      <ModelSummary metadata={data} isLoading={isLoading} hasError={error !== undefined} />
      <PredictionForm baselineRate={data?.baseline_rate ?? undefined} />
    </>
  );
}
