"use client";

import { useState } from "react";

import { predictPurchase } from "../lib/api";
import {
  type PredictionResponse,
  type SessionFeatures,
  sessionFeaturesSchema,
} from "../lib/schemas";
import { PredictionResult } from "./PredictionResult";

type PredictionFormProps = {
  predict?: (features: SessionFeatures) => Promise<PredictionResponse>;
};

type NumberField = {
  name: keyof SessionFeatures;
  label: string;
  defaultValue: number;
  step?: number;
  max?: number;
};

const behaviorFields: NumberField[] = [
  { name: "Administrative", label: "Páginas administrativas", defaultValue: 0 },
  { name: "Administrative_Duration", label: "Duración administrativa", defaultValue: 0, step: 0.1 },
  { name: "Informational", label: "Páginas informativas", defaultValue: 0 },
  { name: "Informational_Duration", label: "Duración informativa", defaultValue: 0, step: 0.1 },
  { name: "ProductRelated", label: "Páginas de producto", defaultValue: 1 },
  { name: "ProductRelated_Duration", label: "Duración en productos", defaultValue: 0, step: 0.1 },
  { name: "BounceRates", label: "Tasa de rebote", defaultValue: 0, step: 0.001, max: 1 },
  { name: "ExitRates", label: "Tasa de salida", defaultValue: 0, step: 0.001, max: 1 },
  { name: "PageValues", label: "Valor de página", defaultValue: 0, step: 0.1 },
  { name: "SpecialDay", label: "Cercanía a fecha especial", defaultValue: 0, step: 0.1, max: 1 },
];

const categoryFields: NumberField[] = [
  { name: "OperatingSystems", label: "Código de sistema operativo", defaultValue: 1 },
  { name: "Browser", label: "Código de navegador", defaultValue: 1 },
  { name: "Region", label: "Código de región", defaultValue: 1 },
  { name: "TrafficType", label: "Código de fuente de tráfico", defaultValue: 1 },
];

function NumberInput({ field }: { field: NumberField }) {
  return (
    <label>
      <span>{field.label}</span>
      <input
        name={field.name}
        type="number"
        defaultValue={field.defaultValue}
        min={0}
        max={field.max}
        step={field.step ?? 1}
        required
      />
    </label>
  );
}

export function PredictionForm({ predict = predictPurchase }: PredictionFormProps) {
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const form = new FormData(event.currentTarget);
      const parsed = sessionFeaturesSchema.parse({
        ...Object.fromEntries(form.entries()),
        Weekend: form.get("Weekend") === "true",
      });
      setResult(await predict(parsed));
    } catch {
      setResult(null);
      setError("No fue posible obtener la predicción. Revise los valores e intente nuevamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <form className="prediction-form" onSubmit={handleSubmit}>
        <fieldset disabled={loading}>
          <legend>Comportamiento de la sesión</legend>
          <div className="field-grid">
            {behaviorFields.map((field) => (
              <NumberInput field={field} key={field.name} />
            ))}
          </div>
        </fieldset>

        <fieldset disabled={loading}>
          <legend>Contexto</legend>
          <div className="field-grid">
            <label>
              <span>Mes</span>
              <select name="Month" defaultValue="Nov">
                {(["Feb", "Mar", "May", "June", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"] as const).map((month) => (
                  <option key={month}>{month}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Tipo de visitante</span>
              <select name="VisitorType" defaultValue="Returning_Visitor">
                <option value="Returning_Visitor">Recurrente</option>
                <option value="New_Visitor">Nuevo</option>
                <option value="Other">Otro</option>
              </select>
            </label>
            <label>
              <span>Fin de semana</span>
              <select name="Weekend" defaultValue="false">
                <option value="false">No</option>
                <option value="true">Sí</option>
              </select>
            </label>
            {categoryFields.map((field) => (
              <NumberInput field={field} key={field.name} />
            ))}
          </div>
        </fieldset>

        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? "Calculando…" : "Predecir compra"}
        </button>
      </form>

      {error ? <p role="alert" className="error-message">{error}</p> : null}
      {result ? <PredictionResult result={result} /> : null}
    </>
  );
}
