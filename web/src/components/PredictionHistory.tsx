import type { PredictionResponse, SessionFeatures } from "../lib/schemas";

const percentage = new Intl.NumberFormat("es-CO", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export type PredictionHistoryItem = {
  id: string;
  createdAt: string;
  features: SessionFeatures;
  result: PredictionResponse;
};

type PredictionHistoryProps = {
  items: PredictionHistoryItem[];
  onClear: () => void;
};

export function PredictionHistory({ items, onClear }: PredictionHistoryProps) {
  return (
    <section className="view-stack" aria-labelledby="history-title">
      <div className="view-heading">
        <div>
          <p className="section-kicker">Sesión del navegador</p>
          <h2 id="history-title">Historial de predicciones</h2>
          <p>Últimas inferencias guardadas localmente en este dispositivo.</p>
        </div>
        {items.length > 0 ? <button className="secondary-button" onClick={onClear} type="button">Limpiar historial</button> : null}
      </div>

      {items.length === 0 ? (
        <section className="panel empty-state">
          <span aria-hidden="true">↺</span>
          <h3>Aún no hay predicciones</h3>
          <p>Realiza una predicción y aparecerá aquí con su probabilidad y contexto.</p>
        </section>
      ) : (
        <div className="history-list">
          {items.map((item) => (
            <article className="panel history-card" key={item.id}>
              <div className={item.result.will_purchase ? "history-status positive" : "history-status negative"}>
                {item.result.will_purchase ? "Compra probable" : "Compra poco probable"}
              </div>
              <strong className="history-probability">{percentage.format(item.result.purchase_probability)}</strong>
              <p>{item.features.Month} · {item.features.VisitorType.replaceAll("_", " ")} · {item.features.ProductRelated} páginas de producto</p>
              <small>{new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.createdAt))}</small>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
