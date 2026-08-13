import type { PredictionResponse } from "../lib/schemas";

const BASELINE = 0.155;
const percentage = new Intl.NumberFormat("es-CO", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

type PredictionResultProps = {
  result: PredictionResponse;
};

export function PredictionResult({ result }: PredictionResultProps) {
  const title = result.will_purchase ? "Compra probable" : "Compra poco probable";

  return (
    <section className="result-card" aria-labelledby="prediction-result" role="status">
      <p className="eyebrow">Resultado</p>
      <h2 id="prediction-result">{title}</h2>
      <p className="probability">{percentage.format(result.purchase_probability)}</p>

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
          <span>Tasa base 15.5%</span>
          <div className="bar-track">
            <span className="bar-fill baseline" style={{ width: `${BASELINE * 100}%` }} />
          </div>
        </div>
      </div>

      <p className="model-note">
        Umbral {percentage.format(result.threshold)} · Modelo {result.model_version}
      </p>
    </section>
  );
}
