# Manual de instalación

## Requisitos

- Python 3.12 y `uv`.
- Git y Docker.
- Node.js 24 y pnpm 11.21.0.
- Para AWS: AWS CLI, Terraform >= 1.10, GitHub CLI y credenciales temporales/perfil.
- Para consultar logs EC2: AWS Session Manager plugin.

## Checkout y dependencias

```bash
git clone https://github.com/aladelca/maia_despliegue_soluciones_microproyecto.git
cd maia_despliegue_soluciones_microproyecto
uv sync --all-groups --locked
npx --yes pnpm@11.21.0 --dir web install --frozen-lockfile
```

El CSV y `models/champion.joblib` viven en el remoto DVC/S3. Con acceso AWS:

```bash
aws sts get-caller-identity
uv run dvc pull
uv run dvc status
```

Sin AWS puede descargar el dataset UCI y generar un modelo local siguiendo la sección
[Inicio local](../README.md#inicio-local). Esa ruta es útil para desarrollo, pero no reproduce la
campaña `full` ejecutada en EC2.

## Validar la experimentación localmente

El perfil smoke ejecuta dos candidatos y dos folds contra una base MLflow local:

```bash
uv run python -m online_shoppers experiment \
  --profile smoke \
  --tracking-uri sqlite:///mlflow.db \
  --data-path data/raw/online_shoppers_intention.csv \
  --output-root /tmp/online-shoppers-smoke \
  --experiment-name online-shoppers-smoke
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
```

Abra <http://127.0.0.1:5000>. El perfil `full` rechaza backends locales: debe usar el tracking URI
HTTP del servidor MLflow en EC2. La guía completa está en
[Experimentación reproducible](experimentation.md).

## Backend local

Con `models/champion.joblib` materializado:

```bash
uv run uvicorn online_shoppers.api.main:app --reload
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/v1/model/metadata
```

Swagger está en <http://localhost:8000/docs>. La alternativa Docker es:

```bash
docker compose up --build
```

Docker levanta solamente FastAPI; no incluye el frontend ni ejecuta experimentos.

## Frontend local

En otra terminal:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 \
  npx --yes pnpm@11.21.0 --dir web dev
```

Abra <http://localhost:3000>. El panel consulta `/v1/model/metadata` y el formulario envía
`POST /v1/predict`.

## Validación completa

```bash
uv run ruff format --check src tests notebook/online-shoppers-ec2-large.ipynb
uv run ruff check src tests notebook/online-shoppers-ec2-large.ipynb
uv run mypy src tests
uv run pytest -q
npx --yes pnpm@11.21.0 --dir web lint
npx --yes pnpm@11.21.0 --dir web typecheck
npx --yes pnpm@11.21.0 --dir web test
npx --yes pnpm@11.21.0 --dir web build
terraform fmt -check -recursive infra/terraform
docker compose config --quiet
```

## AWS y Vercel

Siga la [guía de despliegue](deployment.md). El perfil `full` y MLflow corren en EC2; el champion
corre en Lambda; Next.js corre en Vercel. No confirme `*.tfvars`, `*.tfbackend`, tfstate, `.env`,
`mlflow.db`, CSV, joblib ni credenciales.
