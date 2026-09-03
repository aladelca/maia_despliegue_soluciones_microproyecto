import {
  datasetSummary,
  monthlyConversion,
  signalComparison,
  trafficConversion,
  visitorConversion,
} from "../data/dashboard";

const integer = new Intl.NumberFormat("es-CO");
const percentage = new Intl.NumberFormat("es-CO", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const kpis = [
  {
    label: "Sesiones totales",
    value: integer.format(datasetSummary.sessions),
    detail: "100% del dataset",
    tone: "blue",
    icon: "◉",
  },
  {
    label: "Compras",
    value: integer.format(datasetSummary.purchases),
    detail: percentage.format(datasetSummary.conversionRate),
    tone: "green",
    icon: "✓",
  },
  {
    label: "No compras",
    value: integer.format(datasetSummary.nonPurchases),
    detail: percentage.format(1 - datasetSummary.conversionRate),
    tone: "orange",
    icon: "×",
  },
  {
    label: "Tasa de conversión",
    value: percentage.format(datasetSummary.conversionRate),
    detail: "Compras / sesiones",
    tone: "purple",
    icon: "↗",
  },
] as const;

export function KpiGrid() {
  return (
    <section className="kpi-grid" aria-label="Resumen general">
      {kpis.map((kpi) => (
        <article className={`kpi-card tone-${kpi.tone}`} key={kpi.label}>
          <span className="kpi-icon" aria-hidden="true">{kpi.icon}</span>
          <div>
            <p>{kpi.label}</p>
            <strong>{kpi.value}</strong>
            <small>{kpi.detail}</small>
          </div>
        </article>
      ))}
    </section>
  );
}

export function MonthlyConversionChart() {
  const maxValue = Math.max(...monthlyConversion.map(({ value }) => value));

  return (
    <article className="panel chart-panel">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Estacionalidad</p>
          <h3>Conversión por mes</h3>
        </div>
        <span className="metric-pill">Pico en noviembre</span>
      </div>
      <div className="vertical-chart" aria-label="Tasa de conversión mensual">
        {monthlyConversion.map(({ label, value }) => (
          <div className="vertical-bar-item" key={label}>
            <span className="bar-value">{percentage.format(value)}</span>
            <div className="vertical-track">
              <span
                className="vertical-fill"
                style={{ height: `${Math.max((value / maxValue) * 100, 2)}%` }}
              />
            </div>
            <span className="bar-label">{label}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

export function VisitorConversionChart() {
  const maxValue = Math.max(...visitorConversion.map(({ value }) => value));

  return (
    <article className="panel chart-panel">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Audiencia</p>
          <h3>Conversión por visitante</h3>
        </div>
      </div>
      <div className="horizontal-chart" aria-label="Conversión por tipo de visitante">
        {visitorConversion.map(({ label, value }) => (
          <div className="horizontal-bar-item" key={label}>
            <span>{label}</span>
            <div className="horizontal-track">
              <span style={{ width: `${(value / maxValue) * 100}%` }} />
            </div>
            <strong>{percentage.format(value)}</strong>
          </div>
        ))}
      </div>
      <p className="chart-insight">
        Los visitantes nuevos convierten 1,8× más que los recurrentes en este dataset.
      </p>
    </article>
  );
}

export function TrafficConversionChart() {
  const maxValue = Math.max(...trafficConversion.map(({ value }) => value));

  return (
    <article className="panel chart-panel traffic-panel">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Adquisición</p>
          <h3>Conversión por fuente de tráfico</h3>
        </div>
        <span className="metric-pill">20 categorías</span>
      </div>
      <div className="traffic-chart" aria-label="Conversión por código de fuente de tráfico">
        {trafficConversion.map(({ label, value }) => (
          <div className="traffic-item" key={label} title={`Fuente ${label}: ${percentage.format(value)}`}>
            <span
              className="traffic-fill"
              style={{ height: `${Math.max((value / maxValue) * 100, value === 0 ? 0 : 2)}%` }}
            />
            <small>{label}</small>
          </div>
        ))}
      </div>
    </article>
  );
}

export function DataAnalysisPanel() {
  return (
    <section className="view-stack" aria-labelledby="analysis-title">
      <div className="view-heading">
        <div>
          <p className="section-kicker">Exploración descriptiva</p>
          <h2 id="analysis-title">Análisis de datos</h2>
          <p>Patrones observados en las 12.330 sesiones del dataset UCI.</p>
        </div>
        <span className="data-badge">Sin valores faltantes</span>
      </div>

      <KpiGrid />
      <div className="analysis-grid">
        <MonthlyConversionChart />
        <VisitorConversionChart />
      </div>
      <TrafficConversionChart />

      <section className="panel signal-panel">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Señales del comportamiento</p>
            <h3>Promedio según resultado de compra</h3>
          </div>
        </div>
        <div className="signal-grid">
          {signalComparison.map((signal) => (
            <article key={signal.label}>
              <h4>{signal.label}</h4>
              <div className="signal-values">
                <p><span className="legend-dot purchase" />Compra <strong>{signal.purchase.toFixed(3)}</strong></p>
                <p><span className="legend-dot no-purchase" />No compra <strong>{signal.noPurchase.toFixed(3)}</strong></p>
              </div>
            </article>
          ))}
        </div>
        <p className="source-note">
          Fuente: resumen EDA versionado. Las relaciones son descriptivas y no implican causalidad.
        </p>
      </section>
    </section>
  );
}
