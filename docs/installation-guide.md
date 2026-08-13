# Manual de instalación

## Requisitos

- Python 3.12, uv, Git y Docker.
- Node.js 24 o posterior y pnpm 11.21.0.
- Para infraestructura: AWS CLI, Terraform >=1.10 y credenciales mediante SSO/profile.

## Entorno Python

    uv sync --all-groups
    uv run dvc pull
    uv run pytest -q

Los dos notebooks pueden ejecutarse desde la raíz con Jupyter. El entrenamiento genera MLflow SQLite, metadata, métricas y el champion.

    uv run jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda.ipynb
    uv run jupyter nbconvert --to notebook --execute --inplace notebooks/02_model_training.ipynb
    uv run mlflow ui --backend-store-uri sqlite:///mlflow.db

## Frontend

    cd web
    pnpm install --frozen-lockfile
    pnpm test
    pnpm dev

## Backend con Docker

    docker compose up --build

Docker levanta solamente FastAPI. La API está disponible en http://localhost:8000/docs. Ejecute el frontend con `pnpm dev`, como se indicó arriba, y abra http://localhost:3000.

## AWS y Vercel

Siga docs/deployment.md. El frontend se conecta a Vercel mediante la integración nativa con GitHub; solamente el backend se construye como contenedor. No use access keys estáticas ni confirme .tfvars, tfstate, .env, mlflow.db, CSV o joblib en Git.
