"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";

import { datasetSummary } from "../data/dashboard";
import { getModelMetadata, predictPurchase } from "../lib/api";
import {
  type ModelMetadata,
  type PredictionResponse,
  type SessionFeatures,
  predictionResponseSchema,
  sessionFeaturesSchema,
} from "../lib/schemas";
import {
  DataAnalysisPanel,
  KpiGrid,
  MonthlyConversionChart,
  TrafficConversionChart,
  VisitorConversionChart,
} from "./AnalyticsPanels";
import { DashboardNavigation, type DashboardView } from "./DashboardNavigation";
import { ExperimentationPanel } from "./ExperimentationPanel";
import { ModelSummary } from "./ModelSummary";
import { PredictionForm } from "./PredictionForm";
import { PredictionHistory, type PredictionHistoryItem } from "./PredictionHistory";
import { ProjectInfo } from "./ProjectInfo";

const HISTORY_KEY = "online-shoppers-prediction-history-v1";
const integer = new Intl.NumberFormat("es-CO");

const viewTitles: Record<DashboardView, string> = {
  summary: "Resumen general",
  analysis: "Análisis de datos",
  prediction: "Predicción de intención",
  history: "Historial de predicciones",
  experiments: "Experimentación del modelo",
  project: "Información del proyecto",
};

type PredictionDashboardProps = {
  loadMetadata?: () => Promise<ModelMetadata>;
  predict?: (features: SessionFeatures) => Promise<PredictionResponse>;
};

function isHistoryItem(value: unknown): value is PredictionHistoryItem {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.createdAt === "string" &&
    !Number.isNaN(Date.parse(candidate.createdAt)) &&
    sessionFeaturesSchema.safeParse(candidate.features).success &&
    predictionResponseSchema.safeParse(candidate.result).success
  );
}

function readHistory(): PredictionHistoryItem[] {
  try {
    const rawHistory = window.localStorage.getItem(HISTORY_KEY);
    const parsed: unknown = rawHistory ? JSON.parse(rawHistory) : [];
    return Array.isArray(parsed) ? parsed.filter(isHistoryItem).slice(0, 10) : [];
  } catch {
    return [];
  }
}

export function PredictionDashboard({
  loadMetadata = getModelMetadata,
  predict = predictPurchase,
}: PredictionDashboardProps) {
  const [activeView, setActiveView] = useState<DashboardView>("summary");
  const [history, setHistory] = useState<PredictionHistoryItem[]>([]);
  const { data, error, isLoading } = useSWR("model-metadata", loadMetadata, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => setHistory(readHistory()));
    return () => window.cancelAnimationFrame(frame);
  }, []);

  function recordPrediction(features: SessionFeatures, result: PredictionResponse) {
    setHistory((current) => {
      const nextHistory = [
        {
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          createdAt: new Date().toISOString(),
          features,
          result,
        },
        ...current,
      ].slice(0, 10);
      try {
        window.localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory));
      } catch {
        // Browsers may disable storage; the in-memory history remains usable.
      }
      return nextHistory;
    });
  }

  function clearHistory() {
    try {
      window.localStorage.removeItem(HISTORY_KEY);
    } catch {
      // Clearing the in-memory state still gives the user the expected result.
    }
    setHistory([]);
  }

  return (
    <div className="dashboard-shell">
      <DashboardNavigation activeView={activeView} onNavigate={setActiveView} />

      <div className="dashboard-workspace">
        <header className="dashboard-header">
          <div>
            <p className="breadcrumb">IntentIQ / {viewTitles[activeView]}</p>
            <h1>Intención de Compra Online</h1>
            <p>Predicción y monitoreo del comportamiento de sesiones e-commerce.</p>
          </div>
          <div className="header-status">
            <span className={`live-indicator ${error ? "offline" : ""}`}>
              <i /> {isLoading ? "Verificando API" : error ? "API no disponible" : "API operativa"}
            </span>
            <span>Dataset UCI · {integer.format(datasetSummary.sessions)} sesiones</span>
          </div>
        </header>

        <main className="dashboard-main">
          {activeView === "summary" ? (
            <section className="view-stack" aria-labelledby="summary-title">
              <div className="view-heading compact-heading">
                <div>
                  <p className="section-kicker">Visión ejecutiva</p>
                  <h2 id="summary-title">Resumen general</h2>
                </div>
                <button className="secondary-button" onClick={() => setActiveView("analysis")} type="button">
                  Explorar datos <span aria-hidden="true">→</span>
                </button>
              </div>
              <KpiGrid />
              <ModelSummary metadata={data} isLoading={isLoading} hasError={error !== undefined} />
              <div className="overview-layout">
                <div className="overview-analytics">
                  <div className="analysis-grid">
                    <MonthlyConversionChart />
                    <VisitorConversionChart />
                  </div>
                  <TrafficConversionChart />
                </div>
                <aside className="panel prediction-rail" aria-label="Predicción rápida">
                  <div className="panel-heading">
                    <div>
                      <p className="section-kicker">Modelo en línea</p>
                      <h3>Predicción de compra</h3>
                    </div>
                    <span className="brain-icon" aria-hidden="true">◇</span>
                  </div>
                  <p className="panel-intro">Ingresa las señales de una sesión para estimar su probabilidad de conversión.</p>
                  <PredictionForm
                    baselineRate={data?.baseline_rate ?? undefined}
                    compact
                    onPrediction={recordPrediction}
                    predict={predict}
                  />
                </aside>
              </div>
            </section>
          ) : null}

          {activeView === "analysis" ? <DataAnalysisPanel /> : null}

          {activeView === "prediction" ? (
            <section className="view-stack" aria-labelledby="prediction-title">
              <div className="view-heading">
                <div>
                  <p className="section-kicker">Inferencia en tiempo real</p>
                  <h2 id="prediction-title">Predicción de intención</h2>
                  <p>Completa las 17 variables aceptadas por el contrato del API.</p>
                </div>
              </div>
              <ModelSummary metadata={data} isLoading={isLoading} hasError={error !== undefined} />
              <PredictionForm
                baselineRate={data?.baseline_rate ?? undefined}
                onPrediction={recordPrediction}
                predict={predict}
              />
            </section>
          ) : null}

          {activeView === "history" ? <PredictionHistory items={history} onClear={clearHistory} /> : null}
          {activeView === "experiments" ? <ExperimentationPanel metadata={data} isLoading={isLoading} /> : null}
          {activeView === "project" ? <ProjectInfo /> : null}
        </main>

        <footer className="dashboard-footer">
          Prototipo académico · Las estimaciones son predictivas, no causales.
        </footer>
      </div>
    </div>
  );
}
