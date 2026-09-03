import { experimentSummary, topCandidates } from "../data/dashboard";
import type { ModelMetadata } from "../lib/schemas";

const percentage = new Intl.NumberFormat("es-CO", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

function metric(metrics: Record<string, unknown>, key: string): number | null {
  const value = metrics[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

type ExperimentationPanelProps = {
  metadata?: ModelMetadata;
  isLoading: boolean;
};

export function ExperimentationPanel({ metadata, isLoading }: ExperimentationPanelProps) {
  const validationPrAuc = metadata
    ? metric(metadata.validation_metrics, "cv_pr_auc_mean")
    : null;
  const auditPrAuc = metadata ? metric(metadata.test_metrics, "pr_auc") : null;

  return (
    <section className="view-stack" aria-labelledby="experimentation-title">
      <div className="view-heading">
        <div>
          <p className="section-kicker">MLflow · AWS EC2</p>
          <h2 id="experimentation-title">Experimentación del modelo</h2>
          <p>Comparación reproducible de familias, features y parámetros bajo un protocolo común.</p>
        </div>
        <span className="data-badge success-badge">Campaña completada</span>
      </div>

      <section className="experiment-kpis" aria-label="Resumen de experimentación">
        <article><span>Corridas evaluadas</span><strong>{experimentSummary.candidates}</strong><small>{experimentSummary.failedCandidates} fallidas</small></article>
        <article><span>Validación</span><strong>{experimentSummary.folds} folds</strong><small>Group-aware</small></article>
        <article><span>PR-AUC champion</span><strong>{validationPrAuc === null ? "75,6%" : percentage.format(validationPrAuc)}</strong><small>Promedio CV</small></article>
        <article><span>PR-AUC auditoría</span><strong>{auditPrAuc === null ? "73,7%" : percentage.format(auditPrAuc)}</strong><small>{experimentSummary.auditRows.toLocaleString("es-CO")} sesiones</small></article>
      </section>

      <div className="experiment-layout">
        <section className="panel champion-card">
          <div className="champion-banner">
            <span className="trophy" aria-hidden="true">★</span>
            <span>Champion desplegado</span>
          </div>
          {isLoading ? (
            <p aria-busy="true">Cargando trazabilidad del modelo…</p>
          ) : (
            <>
              <h3>{metadata?.champion ?? "CatBoost depth 8"}</h3>
              <p className="champion-description">
                Mejor PR-AUC promedio en validación cruzada, con variables derivadas y PageValues.
              </p>
              <dl className="trace-list">
                <div><dt>Experimento</dt><dd>{metadata?.mlflow_experiment ?? "online-shoppers-ec2-large-experiment"}</dd></div>
                <div><dt>Run ID</dt><dd>{metadata?.mlflow_run_id ?? "315cd8d316ba47a899f6ba249cc721d9"}</dd></div>
                <div><dt>Dataset</dt><dd>{metadata?.data_version ?? "md5:cc6ec1db03b4f10f8de52c56ff48b085"}</dd></div>
                <div><dt>Umbral</dt><dd>{percentage.format(metadata?.threshold ?? 0.5673544537449113)}</dd></div>
              </dl>
            </>
          )}
        </section>

        <section className="panel protocol-card">
          <div className="panel-heading">
            <div>
              <p className="section-kicker">Protocolo</p>
              <h3>Evaluación sin fuga</h3>
            </div>
          </div>
          <ol className="protocol-list">
            <li><span>1</span><div><strong>Split group-aware</strong><p>StratifiedGroupKFold de {experimentSummary.folds} folds para mantener duplicados relacionados en el mismo grupo.</p></div></li>
            <li><span>2</span><div><strong>Selección por {experimentSummary.selectionMetric}</strong><p>Todos los candidatos compiten con la misma métrica y particiones.</p></div></li>
            <li><span>3</span><div><strong>Umbral por {experimentSummary.thresholdMetric}</strong><p>El umbral se ajusta sólo con predicciones out-of-fold.</p></div></li>
            <li><span>4</span><div><strong>Auditoría final</strong><p>{experimentSummary.auditGroups.toLocaleString("es-CO")} grupos reservados se evalúan una sola vez.</p></div></li>
          </ol>
          <p className="compute-note">Ejecutado en AWS EC2 {experimentSummary.instance} · {experimentSummary.region}. Artefactos persistidos en S3.</p>
        </section>
      </div>

      <section className="panel ranking-panel">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Leaderboard</p>
            <h3>Mejores candidatos por PR-AUC CV</h3>
          </div>
          <span className="metric-pill">Top 5 de 66</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr><th>#</th><th>Familia</th><th>Configuración</th><th>Features</th><th>PR-AUC</th><th>F1</th><th>Tiempo</th></tr>
            </thead>
            <tbody>
              {topCandidates.map((candidate) => (
                <tr className={candidate.rank === 1 ? "winner-row" : undefined} key={candidate.rank}>
                  <td><span className="rank-badge">{candidate.rank}</span></td>
                  <td><strong>{candidate.family}</strong>{candidate.rank === 1 ? <small className="winner-label">Champion</small> : null}</td>
                  <td>{candidate.configuration}</td>
                  <td>{candidate.featureSet}</td>
                  <td><strong>{percentage.format(candidate.prAuc)}</strong></td>
                  <td>{percentage.format(candidate.f1)}</td>
                  <td>{candidate.durationSeconds.toFixed(1)} s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="source-note">Fuente: campaña EC2/MLflow versionada en reports/experiments/final_model_comparison.json.</p>
      </section>
    </section>
  );
}

