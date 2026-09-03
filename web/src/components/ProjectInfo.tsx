export function ProjectInfo() {
  return (
    <section className="view-stack" aria-labelledby="project-title">
      <div className="view-heading">
        <div>
          <p className="section-kicker">Entrega académica</p>
          <h2 id="project-title">Información del proyecto</h2>
          <p>Producto predictivo reproducible para intención de compra en sesiones de e-commerce.</p>
        </div>
      </div>

      <div className="project-grid">
        <article className="panel project-card">
          <span className="project-icon" aria-hidden="true">⌁</span>
          <h3>Objetivo</h3>
          <p>Estimar la probabilidad de Revenue a partir de 17 señales de navegación y contexto de la sesión.</p>
        </article>
        <article className="panel project-card">
          <span className="project-icon" aria-hidden="true">◇</span>
          <h3>Modelo</h3>
          <p>CatBoost con feature engineering, selección por PR-AUC y umbral optimizado con predicciones out-of-fold.</p>
        </article>
        <article className="panel project-card">
          <span className="project-icon" aria-hidden="true">☁</span>
          <h3>Despliegue</h3>
          <p>Experimentación en EC2 y MLflow; artefactos S3; inferencia FastAPI en Lambda/API Gateway; interfaz en Vercel.</p>
        </article>
      </div>

      <section className="panel architecture-panel">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Arquitectura</p>
            <h3>Del dato a la decisión</h3>
          </div>
        </div>
        <div className="architecture-flow" aria-label="Flujo de arquitectura">
          <div><strong>Dataset UCI</strong><span>DVC + S3</span></div><b aria-hidden="true">→</b>
          <div><strong>Entrenamiento</strong><span>EC2 + MLflow</span></div><b aria-hidden="true">→</b>
          <div><strong>Champion</strong><span>ECR + Lambda</span></div><b aria-hidden="true">→</b>
          <div><strong>Producto</strong><span>API Gateway + Vercel</span></div>
        </div>
      </section>

      <section className="panel limitations-panel">
        <h3>Uso responsable</h3>
        <p>El resultado identifica patrones predictivos del dataset académico. No demuestra causalidad y no debe utilizarse como única base para tomar decisiones sobre personas.</p>
      </section>
    </section>
  );
}
