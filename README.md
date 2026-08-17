# Online Shoppers Purchasing Intention

Prototipo académico para estimar si una sesión de comercio electrónico terminará en compra. El proyecto usa el dataset Online Shoppers Purchasing Intention de UCI, un pipeline supervisado de scikit-learn, MLflow para experimentos, DVC con un remoto S3 para datos/artefactos, FastAPI para inferencia y una pantalla Next.js para consumir la API.

## Arquitectura

- Entrenamiento bajo demanda desde notebooks; la lógica reutilizable vive en src/online_shoppers.
- Dataset y champion versionados con DVC en un bucket S3 privado administrado por Terraform.
- Experimentos registrados en MLflow local.
- FastAPI adaptada a Lambda mediante Mangum y empaquetada como imagen ECR.
- API Gateway expone HTTPS; Next.js se despliega en Vercel.
- Terraform declara y administra los recursos AWS del proyecto.

## Ejecución en AWS

### Requisitos de nube

- AWS CLI autenticado con credenciales temporales.
- Terraform 1.15.8.
- Docker con `buildx` para publicar la imagen Lambda en ECR.
- Python 3.12 y `uv` para recuperar y validar el modelo antes del build.
- Para el despliegue completo: permisos sobre ECR, IAM, Lambda, API Gateway,
  CloudWatch y el backend S3 de Terraform.

#### Instalar Terraform en macOS

La opción recomendada por HashiCorp es instalar Terraform desde su tap oficial
de Homebrew:

    brew tap hashicorp/tap
    brew install hashicorp/tap/terraform
    terraform version

Si Terraform ya estaba instalado desde ese tap, actualícelo con
`brew upgrade hashicorp/tap/terraform`. El proyecto requiere Terraform 1.10 o
superior y CI utiliza la versión 1.15.8.

Para usar exactamente la misma versión que CI sin depender de Homebrew,
descargue el binario oficial y valide su checksum. En un Mac con Apple Silicon:

    TERRAFORM_VERSION=1.15.8
    TERRAFORM_PACKAGE="terraform_${TERRAFORM_VERSION}_darwin_arm64.zip"
    curl --fail --location \
      --output "/tmp/${TERRAFORM_PACKAGE}" \
      "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/${TERRAFORM_PACKAGE}"
    curl --fail --location \
      --output "/tmp/terraform_${TERRAFORM_VERSION}_SHA256SUMS" \
      "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_SHA256SUMS"
    EXPECTED_SHA=$(awk -v package="$TERRAFORM_PACKAGE" '$2 == package { print $1 }' \
      "/tmp/terraform_${TERRAFORM_VERSION}_SHA256SUMS")
    ACTUAL_SHA=$(shasum -a 256 "/tmp/${TERRAFORM_PACKAGE}" | awk '{ print $1 }')
    test -n "$EXPECTED_SHA" && test "$ACTUAL_SHA" = "$EXPECTED_SHA"
    unzip -o "/tmp/${TERRAFORM_PACKAGE}" -d "/tmp/terraform-${TERRAFORM_VERSION}"
    sudo install -m 0755 "/tmp/terraform-${TERRAFORM_VERSION}/terraform" \
      /usr/local/bin/terraform
    terraform version

En un Mac Intel, sustituya `darwin_arm64` por `darwin_amd64`. Consulte la
[instalación oficial de Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
y la [verificación oficial del archivo](https://developer.hashicorp.com/terraform/tutorials/cli/verify-archive)
para más detalles.

Nunca incluya access keys en Git ni en `.dvc/config`. Si las credenciales
temporales están en el `.env` local ignorado por Git, cárguelas y compruebe la
identidad antes de ejecutar Terraform o DVC:

    set -a
    source .env
    set +a
    aws sts get-caller-identity
    aws configure get region

La sesión AWS Academy usada para este proyecto debe mostrar la cuenta
`712986489191` y un ARN `assumed-role/voclabs/...`.

### 1. Recuperar datos y modelo desde S3

Desde la raíz del repositorio:

    uv sync --all-groups --locked
    uv run dvc remote list
    uv run dvc pull
    uv run dvc status -c
    test -f data/raw/online_shoppers_intention.csv
    test -f models/champion.joblib

El remoto esperado es:

    s3://maia-online-shoppers-dvc-712986489191-us-east-1/online-shoppers

### 2. Verificar o reaplicar DVC/S3 en `voclabs`

El laboratorio permite administrar S3, pero no crear IAM u OIDC. Por eso se
aplica `foundation` con `enable_deployment_resources=false`:

    terraform -chdir=infra/terraform/foundation init -reconfigure \
      -backend-config='bucket=maia-online-shoppers-tfstate-712986489191-us-east-1' \
      -backend-config='key=online-shoppers/dev/foundation.tfstate' \
      -backend-config='region=us-east-1' \
      -backend-config='use_lockfile=true' \
      -backend-config='encrypt=true'

    terraform -chdir=infra/terraform/foundation plan \
      -var='owner=adrian-alarcon' \
      -var='dvc_bucket_name=maia-online-shoppers-dvc-712986489191-us-east-1' \
      -var='terraform_state_bucket_name=maia-online-shoppers-tfstate-712986489191-us-east-1' \
      -var='github_owner=aladelca' \
      -var='github_repository=maia_despliegue_soluciones_microproyecto' \
      -var='enable_deployment_resources=false' \
      -out=/tmp/online-shoppers-foundation.tfplan

Revise que el plan no destruya recursos. Para aplicar exactamente el plan
guardado:

    terraform -chdir=infra/terraform/foundation apply \
      /tmp/online-shoppers-foundation.tfplan

Después de publicar una nueva versión del dataset o modelo:

    uv run dvc add data/raw/online_shoppers_intention.csv
    uv run dvc add models/champion.joblib
    uv run dvc push
    uv run dvc status -c

### 3. Desplegar la API completa en AWS

Este paso no funciona con el rol `voclabs`, porque el stack necesita crear IAM
y OIDC. Ejecútelo en una cuenta o rol autorizado que también pueda leer el
bucket DVC; lo más simple es mantener S3, ECR, Lambda y Terraform en la misma
cuenta.

Antes de cambiar de cuenta, complete el paso 1 para conservar una copia local
del dataset y el modelo. En la cuenta definitiva, cree primero el bucket de
estado con el paso 1 de [la guía de despliegue](docs/deployment.md) y sustituya
todos los valores `replace-*` y `<...>` de los siguientes comandos.

Después copie el archivo de variables y aplique `foundation` con los recursos
de despliegue habilitados:

    CLOUD_AWS_REGION=us-east-1
    test -f infra/terraform/environments/dev/foundation.tfvars || \
      cp infra/terraform/environments/dev/foundation.example.tfvars \
        infra/terraform/environments/dev/foundation.tfvars

    terraform -chdir=infra/terraform/foundation init -reconfigure \
      -backend-config='bucket=<terraform-state-bucket>' \
      -backend-config='key=online-shoppers/dev/foundation.tfstate' \
      -backend-config="region=$CLOUD_AWS_REGION" \
      -backend-config='use_lockfile=true' \
      -backend-config='encrypt=true'

    terraform -chdir=infra/terraform/foundation plan \
      -var-file=../environments/dev/foundation.tfvars \
      -var='enable_deployment_resources=true' \
      -out=/tmp/online-shoppers-cloud-foundation.tfplan

    terraform -chdir=infra/terraform/foundation apply \
      /tmp/online-shoppers-cloud-foundation.tfplan

Si la cuenta definitiva usa otro bucket DVC, actualice la configuración
versionada y publique los artefactos materializados antes del build:

    CLOUD_DVC_BUCKET=$(terraform -chdir=infra/terraform/foundation output -raw dvc_bucket_name)
    uv run dvc remote modify aws-s3 url \
      "s3://$CLOUD_DVC_BUCKET/online-shoppers"
    uv run dvc push
    uv run dvc status -c

Incluya el cambio resultante de `.dvc/config` en el mismo commit que cambia de
cuenta o entorno.

Recupere el modelo, construya la imagen para Lambda y publíquela con un tag
inmutable igual al commit Git:

    uv run dvc pull models/champion.joblib.dvc
    uv run pytest -q tests/integration/test_model_smoke.py tests/integration/api

    ECR_REPOSITORY_URL=$(terraform -chdir=infra/terraform/foundation output -raw ecr_repository_url)
    ECR_REGISTRY=${ECR_REPOSITORY_URL%%/*}
    ECR_REPOSITORY_NAME=${ECR_REPOSITORY_URL##*/}
    IMAGE_TAG=$(git rev-parse HEAD)

    aws ecr get-login-password --region "$CLOUD_AWS_REGION" | \
      docker login --username AWS --password-stdin "$ECR_REGISTRY"

    docker buildx build \
      --platform linux/amd64 \
      --provenance=false \
      -f docker/api.Dockerfile \
      -t "$ECR_REPOSITORY_URL:$IMAGE_TAG" \
      --push .

Resuelva el digest publicado; Terraform rechaza tags mutables:

    IMAGE_DIGEST=$(aws ecr describe-images \
      --region "$CLOUD_AWS_REGION" \
      --repository-name "$ECR_REPOSITORY_NAME" \
      --image-ids imageTag="$IMAGE_TAG" \
      --query 'imageDetails[0].imageDigest' \
      --output text)
    IMAGE_URI="$ECR_REPOSITORY_URL@$IMAGE_DIGEST"

Inicialice y aplique el servicio:

    terraform -chdir=infra/terraform/service init -reconfigure \
      -backend-config='bucket=<terraform-state-bucket>' \
      -backend-config='key=online-shoppers/dev/service.tfstate' \
      -backend-config="region=$CLOUD_AWS_REGION" \
      -backend-config='use_lockfile=true' \
      -backend-config='encrypt=true'

    terraform -chdir=infra/terraform/service plan \
      -var="aws_region=$CLOUD_AWS_REGION" \
      -var='owner=<owner>' \
      -var="image_uri=$IMAGE_URI" \
      -var='allowed_origin=https://<frontend-domain>' \
      -out=/tmp/online-shoppers-service.tfplan

    terraform -chdir=infra/terraform/service apply \
      /tmp/online-shoppers-service.tfplan

Compruebe que Lambda cargó el modelo incluido en la imagen:

    API_URL=$(terraform -chdir=infra/terraform/service output -raw api_base_url)
    curl --fail --retry 5 --retry-delay 5 "$API_URL/health"
    curl --fail "$API_URL/v1/model/metadata"

El mismo proceso está automatizado en `.github/workflows/deploy-api.yml`. Una
vez configurados el environment `dev`, el secreto `AWS_DEPLOY_ROLE_ARN` y las
variables descritas en [la guía de despliegue](docs/deployment.md), ejecútelo
desde GitHub CLI:

    gh workflow run deploy-api.yml --ref main
    gh run list --workflow deploy-api.yml --limit 5
    gh run watch <run-id> --exit-status

## Inicio local

> [!IMPORTANT]
> El remoto DVC está configurado en
> `s3://maia-online-shoppers-dvc-712986489191-us-east-1/online-shoppers`.
> `dvc pull` requiere credenciales temporales con acceso al bucket. Para
> ejecutar el proyecto localmente sin AWS, siga la ruta completa descrita a
> continuación.

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
versiona sus punteros `.dvc`. Si no dispone de credenciales para el remoto S3,
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

El remoto compartido está versionado en `.dvc/config`. Después de autenticarse
en la cuenta AWS autorizada, valide su configuración y publique cambios así:

    uv run dvc remote list
    uv run dvc status -c
    uv run dvc push

Otro clon con credenciales AWS autorizadas podrá usar `uv run dvc pull`.
Consulte [la guía DVC/S3](docs/dvc-s3.md) para operación y validación.

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
como se indica en el paso 1 de **Inicio local**. Con credenciales AWS
autorizadas, use `dvc pull` para recuperar los objetos del remoto. Para explorar
las corridas generadas por el entrenamiento:

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
