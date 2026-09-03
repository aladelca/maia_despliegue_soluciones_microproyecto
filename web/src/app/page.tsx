import { PredictionDashboard } from "../components/PredictionDashboard";

export default function Home() {
  return (
    <main>
      <header className="hero">
        <p className="eyebrow">Online Shoppers · Prototipo ML</p>
        <h1>¿Esta sesión terminará en compra?</h1>
        <p>
          Complete las señales disponibles. El modelo compara esta sesión con patrones del
          dataset de UCI y devuelve una probabilidad de conversión.
        </p>
      </header>

      <PredictionDashboard />

      <footer>
        Esta predicción es orientativa y no demuestra que una variable o intervención cause la
        compra.
      </footer>
    </main>
  );
}
