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

> [!IMPORTANT]
> No existe todavía un bucket S3 real para este proyecto. La URL
> `s3://replace-with-dvc-bucket/online-shoppers` de `.dvc/config` es un
> placeholder y `dvc pull` fallará mientras no se aplique Terraform y se
> publique el contenido con `dvc push`. Para ejecutar el proyecto localmente
> no necesita AWS, credenciales ni `dvc pull`: siga la ruta completa descrita
> a continuación.

### Requisitos locales

- Git.
- Python 3.12 y [uv](https://docs.astral.sh/uv/).
- Node.js 24 o posterior para ejecutar el frontend.
- Docker es opcional y se utiliza solamente para el backend.

Todos los comandos de esta sección se ejecutan desde la raíz del repositorio:

    uv sync --all-groups --locked

### 1. Preparar el dataset y el modelo sin AWS

Primero revise si el modelo ya está materializado:

    test -f models/champion.joblib && echo "Modelo local disponible"

Si el archivo existe, puede pasar directamente al paso 2. El CSV no es
necesario para hacer inferencia.

En un clon nuevo el CSV y el joblib normalmente no existen porque Git solo
versiona sus punteros `.dvc`. Como el remoto S3 todavía no está disponible,
descargue temporalmente el dataset desde UCI y ejecute una vez el notebook de
entrenamiento:

    mkdir -p data/raw models
    curl --fail --location \
      --output /tmp/online-shoppers-dataset.zip \
      "https://archive.ics.uci.edu/static/public/468/online+shoppers+purchasing+intention+dataset.zip"
    unzip -o /tmp/online-shoppers-dataset.zip -d data/raw
    uv run jupyter nbconvert \
      --to notebook \
      --execute \
      --inplace notebooks/02_model_training.ipynb

Al terminar deben existir juntos:

- `data/raw/online_shoppers_intention.csv`;
- `models/champion.joblib`;
- `models/model_metadata.json`.

El notebook también genera las métricas y el registro MLflow local. Si desea
ejecutar primero el análisis exploratorio, use:

    uv run jupyter nbconvert \
      --to notebook \
      --execute \
      --inplace notebooks/01_eda.ipynb

### 2. Ejecutar FastAPI con archivos locales

La API puede ejecutarse directamente con archivos locales; no consulta S3 durante la inferencia. Por defecto carga:

- `models/champion.joblib`, artefacto binario ignorado por Git y versionado mediante DVC;
- `models/model_metadata.json`, metadata versionada en Git.

Con el joblib generado o recuperado, ejecute:

    uv run uvicorn online_shoppers.api.main:app --reload

La API queda disponible en http://localhost:8000 y su documentación en http://localhost:8000/docs. Compruebe la carga del modelo con:

    curl http://localhost:8000/health

La respuesta debe incluir `"status":"ok"`. Si devuelve
`"status":"degraded"`, detenga la API y confirme que el joblib y la metadata
existan y correspondan entre sí. Sin un modelo válido, `/v1/predict` responde
con HTTP 503.

Las rutas pueden sobrescribirse si se desea usar otra ubicación local:

    MODEL_PATH=/ruta/al/champion.joblib \
    MODEL_METADATA_PATH=/ruta/a/model_metadata.json \
    uv run uvicorn online_shoppers.api.main:app --reload

### 3. Ejecutar el frontend local

Mantenga FastAPI ejecutándose y, en una segunda terminal abierta en la raíz
del repositorio, instale y levante Next.js:

    npx --yes pnpm@11.21.0 --dir web install --frozen-lockfile
    NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 \
      npx --yes pnpm@11.21.0 --dir web dev

Abra http://localhost:3000. La API debe seguir disponible en el puerto 8000.

### 4. Alternativa: backend local con Docker

También se puede construir únicamente el backend desde los mismos archivos locales:

    docker compose up --build

El build copia `models/champion.joblib` dentro de la imagen, por lo que el
archivo debe existir antes de ejecutar Docker. El contenedor no descarga el
modelo desde S3. El frontend se ejecuta con los mismos comandos del paso 3.

En producción, Vercel construye el proyecto Next.js directamente desde GitHub,
con `web` como Root Directory; no se usa una imagen Docker para el frontend.

### Diferencia frente al despliegue AWS

    Local: models/champion.joblib -> FastAPI
    AWS:   DVC/S3 -> GitHub Actions -> imagen Docker -> ECR -> Lambda

S3 funciona como remoto versionado de DVC. GitHub Actions recupera el modelo exacto y lo incorpora en la imagen; Lambda ejecuta esa imagen y tampoco consulta S3 durante una predicción.

### Cuándo usar DVC con S3

No ejecute `dvc pull` contra el placeholder actual. El flujo S3 solo estará
disponible después de crear la infraestructura declarada en Terraform. La
configuración correcta se obtiene después de aplicar `foundation`:

    DVC_BUCKET=$(terraform -chdir=infra/terraform/foundation output -raw dvc_bucket_name)
    uv run dvc remote add -f -d aws-s3 "s3://${DVC_BUCKET}/online-shoppers"
    uv run dvc push

A partir de ese momento, otro clon con credenciales AWS autorizadas podrá usar
`uv run dvc pull`. El nombre exacto del bucket no puede documentarse antes del
`terraform apply`; consulte [la guía DVC/S3](docs/dvc-s3.md) para ese despliegue.

## Generar una predicción mediante la API

Con FastAPI ejecutándose localmente, envíe una sesión completa a `POST /v1/predict`:

    curl --request POST http://localhost:8000/v1/predict \
      --header 'Content-Type: application/json' \
      --data '{
        "Administrative": 2,
        "Administrative_Duration": 35.5,
        "Informational": 1,
        "Informational_Duration": 12.0,
        "ProductRelated": 12,
        "ProductRelated_Duration": 420.0,
        "BounceRates": 0.01,
        "ExitRates": 0.03,
        "PageValues": 18.5,
        "SpecialDay": 0.0,
        "Month": "Nov",
        "OperatingSystems": 2,
        "Browser": 2,
        "Region": 1,
        "TrafficType": 3,
        "VisitorType": "Returning_Visitor",
        "Weekend": false
      }'

La respuesta contiene `purchase_probability`, la decisión `will_purchase`, el `threshold` utilizado y `model_version`. La especificación interactiva está disponible en http://localhost:8000/docs.

Consulte la [guía completa de la API](docs/api-guide.md) para conocer todas las variables, ejemplos con curl y Python, interpretación de la respuesta y manejo de errores.

## Datos y entrenamiento

Para el flujo local sin AWS, descargue el CSV desde UCI y ejecute los notebooks
como se indica en el paso 1 de **Inicio local**. Use `dvc pull` únicamente
cuando el remoto S3 real ya exista y contenga los objetos. Para explorar las
corridas generadas por el entrenamiento:

    uv run mlflow ui --backend-store-uri sqlite:///mlflow.db

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
