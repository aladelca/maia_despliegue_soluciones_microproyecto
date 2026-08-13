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

### Ruta local sin AWS

La API puede ejecutarse directamente con archivos locales; no consulta S3 durante la inferencia. Por defecto carga:

- `models/champion.joblib`, artefacto binario ignorado por Git y versionado mediante DVC;
- `models/model_metadata.json`, metadata versionada en Git.

Si `models/champion.joblib` ya está materializado, no es necesario ejecutar `dvc pull` ni tener credenciales AWS. El CSV tampoco es necesario para servir predicciones. Ejecute:

    uv sync --all-groups
    uv run pytest
    uv run uvicorn online_shoppers.api.main:app --reload

La API queda disponible en http://localhost:8000 y su documentación en http://localhost:8000/docs. Compruebe la carga del modelo con:

    curl http://localhost:8000/health

La respuesta debe tener `status: "ok"`. Si el joblib no existe, hay dos formas de materializarlo:

1. Recuperarlo con `uv run dvc pull models/champion.joblib.dvc` cuando el remoto S3 ya esté configurado y poblado.
2. Ejecutar `notebooks/02_model_training.ipynb`, que entrena y guarda el champion localmente.

Las rutas pueden sobrescribirse con `MODEL_PATH` y `MODEL_METADATA_PATH` si se desea usar otra ubicación local.

### Ruta local con Docker

También se puede construir únicamente el backend desde los mismos archivos locales:

    docker compose up --build

El build copia `models/champion.joblib` dentro de la imagen, por lo que el archivo debe existir antes de ejecutar Docker. El contenedor no descarga el modelo desde S3.

### Frontend local

Para ejecutar la interfaz contra cualquiera de las dos rutas locales de FastAPI:

    cd web
    pnpm install --frozen-lockfile
    NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 pnpm dev

La interfaz queda en http://localhost:3000. En producción, Vercel construye el proyecto Next.js directamente desde el repositorio GitHub, con `web` como Root Directory; no se usa una imagen Docker para el frontend.

### Diferencia frente al despliegue AWS

    Local: models/champion.joblib -> FastAPI
    AWS:   DVC/S3 -> GitHub Actions -> imagen Docker -> ECR -> Lambda

S3 funciona como remoto versionado de DVC. GitHub Actions recupera el modelo exacto y lo incorpora en la imagen; Lambda ejecuta esa imagen y tampoco consulta S3 durante una predicción.

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
