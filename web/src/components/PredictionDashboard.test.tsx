import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach } from "vitest";
import { SWRConfig } from "swr";

import { PredictionDashboard } from "./PredictionDashboard";

function renderIsolated(component: React.ReactNode) {
  return render(
    <SWRConfig value={{ provider: () => new Map() }}>
      {component}
    </SWRConfig>,
  );
}

const metadata = {
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
};

beforeEach(() => {
  const values = new Map<string, string>();
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: {
      clear: () => values.clear(),
      getItem: (key: string) => values.get(key) ?? null,
      key: (index: number) => [...values.keys()][index] ?? null,
      get length() { return values.size; },
      removeItem: (key: string) => values.delete(key),
      setItem: (key: string, value: string) => values.set(key, value),
    } satisfies Storage,
  });
  window.localStorage.clear();
});

it("loads and displays champion metadata from the API", async () => {
  renderIsolated(
    <PredictionDashboard
      loadMetadata={async () => metadata}
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

it("navigates to the real experiment leaderboard", async () => {
  const user = userEvent.setup();
  renderIsolated(<PredictionDashboard loadMetadata={async () => metadata} />);

  await user.click(screen.getByRole("button", { name: "Experimentación" }));

  expect(screen.getByRole("heading", { name: "Experimentación del modelo" })).toBeInTheDocument();
  expect(within(screen.getByText("Corridas evaluadas").parentElement!).getByText("66")).toBeInTheDocument();
  expect(await screen.findByText("run-ec2-123")).toBeInTheDocument();
  expect(screen.getByRole("table")).toHaveTextContent("XGBoost");
});

it("stores successful predictions in the local history", async () => {
  const user = userEvent.setup();
  renderIsolated(
    <PredictionDashboard
      loadMetadata={async () => metadata}
      predict={async () => ({
        will_purchase: true,
        purchase_probability: 0.73,
        threshold: 0.61,
        model_version: "champion-v2",
      })}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Predecir compra" }));
  expect(await screen.findByText("Compra probable")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Historial" }));

  expect(screen.getByRole("heading", { name: "Historial de predicciones" })).toBeInTheDocument();
  expect(screen.getByText("73,0%")).toBeInTheDocument();
  expect(window.localStorage.getItem("online-shoppers-prediction-history-v1")).toContain("champion-v2");
});
