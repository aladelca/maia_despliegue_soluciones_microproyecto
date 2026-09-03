import type { PredictionResponse } from "../lib/schemas";

const DEFAULT_BASELINE = 0.155;
const percentage = new Intl.NumberFormat("es-CO", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

type PredictionResultProps = {
  result: PredictionResponse;
  baselineRate?: number;
};

export function PredictionResult({
  result,
  baselineRate = DEFAULT_BASELINE,
}: PredictionResultProps) {
  const title = result.will_purchase ? "Compra probable" : "Compra poco probable";

  return (
    <section className="result-card" aria-labelledby="prediction-result" role="status">
      <div className="result-heading">
        <div>
          <p className="section-kicker">Resultado de la predicción</p>
          <h2 id="prediction-result">{title}</h2>
        </div>
        <span className={result.will_purchase ? "result-chip positive" : "result-chip negative"}>
          {result.will_purchase ? "Alta intención" : "Baja intención"}
        </span>
      </div>

      <div className="result-visual">
        <div
          aria-label={`Probabilidad ${percentage.format(result.purchase_probability)}`}
          className="probability-ring"
          style={{ background: `conic-gradient(var(--result-color) ${result.purchase_probability * 360}deg, #e8edf5 0deg)` }}
        >
          <span>{percentage.format(result.purchase_probability)}</span>
          <small>probabilidad</small>
        </div>

        <div className="comparison" aria-label="Comparación de probabilidades">
          <div className="bar-row">
            <span>Esta sesión</span>
            <div className="bar-track">
              <span
                className="bar-fill prediction"
                style={{ width: `${result.purchase_probability * 100}%` }}
              />
            </div>
          </div>
          <div className="bar-row">
            <span>Tasa base {percentage.format(baselineRate)}</span>
            <div className="bar-track">
              <span className="bar-fill baseline" style={{ width: `${baselineRate * 100}%` }} />
            </div>
          </div>
        </div>
      </div>

      <p className="model-note">
        Umbral {percentage.format(result.threshold)} · Modelo {result.model_version}
      </p>
    </section>
  );
}
