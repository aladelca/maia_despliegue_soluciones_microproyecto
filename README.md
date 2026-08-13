# Online Shoppers Purchasing Intention

Prototipo académico para estimar si una sesión de comercio electrónico terminará en compra. El proyecto usa el dataset Online Shoppers Purchasing Intention de UCI, un pipeline supervisado de scikit-learn, MLflow para experimentos, DVC con un remoto S3 para datos/artefactos, FastAPI para inferencia y una pantalla Next.js para consumir la API.

## Arquitectura

- Entrenamiento bajo demanda desde notebooks; la lógica reutilizable vive en src/online_shoppers.
- Dataset y champion versionados con DVC; S3 será creado por Terraform cuando se despliegue.
- Experimentos registrados en MLflow local.
- FastAPI adaptada a Lambda mediante Mangum y empaquetada como imagen ECR.
- API Gateway expone HTTPS; Next.js se despliega en Vercel.
- Terraform declara los recursos AWS. Esta implementación no ejecuta terraform apply ni crea recursos externos.

## Inicio local

    uv sync --all-groups
    uv run dvc pull
    uv run pytest
    docker compose up --build

Docker se usa únicamente para el backend; la API queda en http://localhost:8000. Para ejecutar la interfaz:

    cd web
    pnpm install --frozen-lockfile
    NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 pnpm dev

La interfaz queda en http://localhost:3000. En producción, Vercel construye el proyecto Next.js directamente desde el repositorio GitHub, con `web` como Root Directory; no se usa una imagen Docker para el frontend.

## Datos y entrenamiento

1. Restaure el CSV con dvc pull o ejecute el procedimiento documentado en docs/dvc-s3.md.
2. Ejecute notebooks/01_eda.ipynb.
3. Ejecute notebooks/02_model_training.ipynb para registrar los experimentos y generar models/champion.joblib.
4. Abra MLflow con uv run mlflow ui --backend-store-uri sqlite:///mlflow.db.

El modelo se elige por F1 en validación, según la decisión confirmada para este prototipo. El test se reserva para una única evaluación final.

## Validación

    uv run ruff format --check src tests
    uv run ruff check src tests
    uv run mypy src tests
    uv run pytest -q
    pnpm --dir web lint
    pnpm --dir web typecheck
    pnpm --dir web test

Consulte docs/installation-guide.md para instalación completa y docs/user-guide.md para uso.

## Fuente

Sakar, C. y Kastro, Y. (2018), Online Shoppers Purchasing Intention Dataset, UCI Machine Learning Repository, DOI 10.24432/C5F88Q, licencia CC BY 4.0.
