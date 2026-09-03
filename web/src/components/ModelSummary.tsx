import type { ModelMetadata } from "../lib/schemas";

const percentage = new Intl.NumberFormat("es-CO", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

function numericMetric(metrics: Record<string, unknown>, key: string): number | null {
  const value = metrics[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

type ModelSummaryProps = {
  metadata?: ModelMetadata;
  isLoading: boolean;
  hasError: boolean;
};

export function ModelSummary({ metadata, isLoading, hasError }: ModelSummaryProps) {
  if (isLoading) {
    return <section className="model-summary" aria-busy="true">Cargando modelo desplegado…</section>;
  }
  if (hasError || !metadata) {
    return (
      <section className="model-summary metadata-warning" role="status">
        La metadata del modelo no está disponible. La predicción continúa habilitada.
      </section>
    );
  }

  const cvPrAuc = numericMetric(metadata.validation_metrics, "cv_pr_auc_mean");
  const testPrAuc = numericMetric(metadata.test_metrics, "pr_auc");

  return (
    <section className="model-summary" aria-labelledby="model-summary-title">
      <div>
        <p className="eyebrow">Campeón desplegado</p>
        <h2 id="model-summary-title">{metadata.champion ?? metadata.model_version}</h2>
        <p className="model-trace">
          MLflow {metadata.mlflow_run_id ?? "sin run ID"} · Datos {metadata.data_version ?? "sin versión"}
        </p>
      </div>
      <div className="metric-grid">
        <p>PR-AUC CV <strong>{cvPrAuc === null ? "—" : percentage.format(cvPrAuc)}</strong></p>
        <p>PR-AUC audit <strong>{testPrAuc === null ? "—" : percentage.format(testPrAuc)}</strong></p>
        <p>Umbral <strong>{percentage.format(metadata.threshold)}</strong></p>
      </div>
      <p className="feature-note">
        Feature set: {metadata.feature_set ?? "no reportado"}; el modelo {metadata.include_page_values ? "usa PageValues" : "no usa PageValues"}.
      </p>
    </section>
  );
}
