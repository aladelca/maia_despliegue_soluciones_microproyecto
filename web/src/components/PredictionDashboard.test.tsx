import { render, screen } from "@testing-library/react";
import { SWRConfig } from "swr";

import { PredictionDashboard } from "./PredictionDashboard";

function renderIsolated(component: React.ReactNode) {
  return render(
    <SWRConfig value={{ provider: () => new Map() }}>
      {component}
    </SWRConfig>,
  );
}

it("loads and displays champion metadata from the API", async () => {
  renderIsolated(
    <PredictionDashboard
      loadMetadata={async () => ({
        model_version: "champion-v2",
        feature_names: ["Administrative", "PageValues"],
        threshold: 0.61,
        champion: "catboost__engineered_with_page_values",
        mlflow_run_id: "run-ec2-123",
        mlflow_experiment: "online-shoppers-ec2-large-experiment",
        feature_set: "engineered_with_page_values",
        include_page_values: true,
        baseline_rate: 0.22,
        data_version: "md5:dataset",
        validation_metrics: { cv_pr_auc_mean: 0.76, cv_pr_auc_std: 0.01 },
        test_metrics: { pr_auc: 0.75, f1: 0.7 },
      })}
    />,
  );

  expect(await screen.findByText("catboost__engineered_with_page_values")).toBeInTheDocument();
  expect(screen.getByText(/PR-AUC CV/)).toHaveTextContent("76,0%");
  expect(screen.getByText(/run-ec2-123/)).toBeInTheDocument();
  expect(screen.getByText(/usa PageValues/i)).toBeInTheDocument();
});

it("keeps prediction available when metadata cannot be loaded", async () => {
  renderIsolated(
    <PredictionDashboard loadMetadata={async () => Promise.reject(new Error("offline"))} />,
  );

  expect(await screen.findByText(/metadata del modelo no está disponible/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Predecir compra" })).toBeEnabled();
});
