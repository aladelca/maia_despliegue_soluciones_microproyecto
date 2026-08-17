# Online Shoppers Purchasing Intention

Prototipo académico para estimar si una sesión de comercio electrónico terminará en compra. El proyecto usa el dataset Online Shoppers Purchasing Intention de UCI, un pipeline supervisado de scikit-learn, MLflow para experimentos, DVC con un remoto S3 para datos/artefactos, FastAPI para inferencia y una pantalla Next.js para consumir la API.

## Arquitectura

- Entrenamiento bajo demanda desde notebooks; la lógica reutilizable vive en src/online_shoppers.
- Dataset y champion versionados con DVC en un bucket S3 privado administrado por Terraform.
- Experimentos registrados en MLflow local.
- FastAPI adaptada a Lambda mediante Mangum y empaquetada como imagen ECR.
- API Gateway expone HTTPS; Next.js se despliega en Vercel.
- Terraform declara y administra los recursos AWS del proyecto.

## Ejecución en AWS desde cero

Esta ruta crea o recupera la infraestructura con Terraform y delega a GitHub
Actions la descarga DVC, las pruebas, el build Docker, el push a ECR y la
actualización de Lambda. No requiere EC2 ni Docker local. Se asume que los
objetos señalados por los archivos `.dvc` ya existen en el remoto S3; más abajo
se valida esa precondición sin descargarlos al equipo.

### 1. Instalar herramientas

Se necesita Git, AWS CLI, Terraform y, para controlar Actions desde terminal,
GitHub CLI. En macOS con Homebrew:

    brew install awscli gh
    brew tap hashicorp/tap
    brew install hashicorp/tap/terraform
    aws --version
    terraform version
    gh --version

El proyecto requiere Terraform 1.10 o superior y CI usa 1.15.8. Para instalar
exactamente esa versión en un Mac Apple Silicon sin Homebrew:

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

En un Mac Intel, cambie `darwin_arm64` por `darwin_amd64`. Consulte la
[instalación oficial de Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
y la [verificación oficial del archivo](https://developer.hashicorp.com/terraform/tutorials/cli/verify-archive).

### 2. Preparar `.env` y autenticar AWS

Desde la raíz de un clon nuevo:

    cp .env.example .env
    chmod 600 .env

Agregue al `.env` los valores temporales entregados por AWS Academy con estos
nombres: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`,
`AWS_REGION` y `AWS_DEFAULT_REGION`. No los agregue a `.env.example`, Terraform,
DVC ni Git. Después cargue y valide todo:

    set -a
    source .env
    set +a
    : "${TF_STATE_BUCKET:?Falta TF_STATE_BUCKET en .env}"
    : "${TF_FOUNDATION_STATE_KEY:?Falta TF_FOUNDATION_STATE_KEY en .env}"
    : "${TF_SERVICE_STATE_KEY:?Falta TF_SERVICE_STATE_KEY en .env}"
    : "${DVC_S3_BUCKET:?Falta DVC_S3_BUCKET en .env}"
    : "${DVC_S3_PREFIX:?Falta DVC_S3_PREFIX en .env}"
    : "${CLOUD_AWS_REGION:?Falta CLOUD_AWS_REGION en .env}"
    : "${CLOUD_OWNER:?Falta CLOUD_OWNER en .env}"
    : "${LAB_ROLE_ARN:?Falta LAB_ROLE_ARN en .env}"
    aws sts get-caller-identity
    aws iam get-role --role-name LabRole --query 'Role.Arn' --output text

La identidad debe pertenecer a la cuenta `712986489191` y mostrar un ARN
`assumed-role/voclabs/...`.

### 3. Crear o recuperar el backend Terraform

`bootstrap` usa estado local porque crea el bucket que servirá de backend. En
un clon nuevo, recupere primero la copia versionada si ya existe:

    if test ! -f infra/terraform/bootstrap/terraform.tfstate && \
      aws s3api head-object \
        --bucket "$TF_STATE_BUCKET" \
        --key online-shoppers/dev/bootstrap.tfstate >/dev/null 2>&1; then
      aws s3 cp \
        "s3://$TF_STATE_BUCKET/online-shoppers/dev/bootstrap.tfstate" \
        infra/terraform/bootstrap/terraform.tfstate
    fi

Inicialice, revise y aplique. El plan debe crear el bucket en una cuenta nueva
o indicar `No changes` cuando se recuperó el estado existente:

    terraform -chdir=infra/terraform/bootstrap init
    terraform -chdir=infra/terraform/bootstrap plan \
      -var="aws_region=$CLOUD_AWS_REGION" \
      -var="owner=$CLOUD_OWNER" \
      -var="state_bucket_name=$TF_STATE_BUCKET" \
      -out=/tmp/online-shoppers-bootstrap.tfplan
    terraform -chdir=infra/terraform/bootstrap apply \
      /tmp/online-shoppers-bootstrap.tfplan
    aws s3 cp infra/terraform/bootstrap/terraform.tfstate \
      "s3://$TF_STATE_BUCKET/online-shoppers/dev/bootstrap.tfstate"

### 4. Crear o recuperar DVC y ECR

El laboratorio permite S3 y ECR, pero no crear IAM/OIDC. Por eso se crea ECR y
se deshabilitan solamente los recursos OIDC de GitHub:

    terraform -chdir=infra/terraform/foundation init -reconfigure \
      -backend-config="bucket=$TF_STATE_BUCKET" \
      -backend-config="key=$TF_FOUNDATION_STATE_KEY" \
      -backend-config="region=$CLOUD_AWS_REGION" \
      -backend-config='use_lockfile=true' \
      -backend-config='encrypt=true'
    terraform -chdir=infra/terraform/foundation plan \
      -var="owner=$CLOUD_OWNER" \
      -var="dvc_bucket_name=$DVC_S3_BUCKET" \
      -var="terraform_state_bucket_name=$TF_STATE_BUCKET" \
      -var='github_owner=aladelca' \
      -var='github_repository=maia_despliegue_soluciones_microproyecto' \
      -var='enable_deployment_resources=true' \
      -var='enable_github_oidc_resources=false' \
      -out=/tmp/online-shoppers-foundation.tfplan
    terraform -chdir=infra/terraform/foundation apply \
      /tmp/online-shoppers-foundation.tfplan
    terraform -chdir=infra/terraform/foundation output

### 5. Verificar los objetos DVC sin descargarlos

Construya las keys content-addressed a partir de los punteros versionados y
confirme que S3 contiene ambos artefactos:

    MODEL_HASH=$(awk '$2 == "md5:" { print $3 }' models/champion.joblib.dvc)
    DATA_HASH=$(awk '$2 == "md5:" { print $3 }' \
      data/raw/online_shoppers_intention.csv.dvc)
    test -n "$MODEL_HASH" && test -n "$DATA_HASH"
    MODEL_KEY="$DVC_S3_PREFIX/files/md5/$(printf %s "$MODEL_HASH" | cut -c1-2)/$(printf %s "$MODEL_HASH" | cut -c3-)"
    DATA_KEY="$DVC_S3_PREFIX/files/md5/$(printf %s "$DATA_HASH" | cut -c1-2)/$(printf %s "$DATA_HASH" | cut -c3-)"
    aws s3api head-object --bucket "$DVC_S3_BUCKET" --key "$MODEL_KEY"
    aws s3api head-object --bucket "$DVC_S3_BUCKET" --key "$DATA_KEY"

Si alguno no existe, el workflow se detendrá en `dvc pull`. Un responsable que
tenga los artefactos materializados debe ejecutar `uv run dvc push` antes de
continuar.

### 6. Configurar GitHub

Autentique GitHub CLI y guarde las credenciales AWS temporales como repository
secrets. Los comandos solicitan el valor de forma interactiva y no deben recibir
valores en la línea de comandos:

    gh auth login
    gh secret set AWS_ACCESS_KEY_ID
    gh secret set AWS_SECRET_ACCESS_KEY
    gh secret set AWS_SESSION_TOKEN

Configure las variables no secretas requeridas:

    gh variable set AWS_REGION --body us-east-1
    gh variable set TERRAFORM_STATE_BUCKET \
      --body maia-online-shoppers-tfstate-712986489191-us-east-1
    gh variable set OWNER --body adrian-alarcon
    gh variable set ALLOWED_ORIGIN --body http://localhost:3000
    gh variable set LAMBDA_EXECUTION_ROLE_ARN \
      --body arn:aws:iam::712986489191:role/LabRole
    gh secret list
    gh variable list

Use como `ALLOWED_ORIGIN` el dominio real del frontend cuando esté disponible.
El workflow valida la cuenta AWS esperada y reutiliza `LabRole`; nunca crea ni
modifica IAM.

### 7. Desplegar Lambda y API Gateway

El workflow realiza `dvc pull`, pruebas, build `linux/amd64`, push a ECR,
resolución del digest, `terraform apply` y smoke test. Desde `main`:

    gh workflow run deploy-api.yml --ref main
    RUN_ID=$(gh run list --workflow deploy-api.yml --limit 1 \
      --json databaseId --jq '.[0].databaseId')
    gh run watch "$RUN_ID" --exit-status

Una ejecución repetida del mismo commit reutiliza la imagen inmutable existente
en ECR. Para comprobar la API sin leer el estado Terraform local:

    API_URL=$(aws apigatewayv2 get-apis \
      --region "$CLOUD_AWS_REGION" \
      --query "Items[?Name=='online-shoppers-ml-dev'].ApiEndpoint | [0]" \
      --output text)
    test -n "$API_URL" && test "$API_URL" != None
    curl --fail --retry 5 --retry-delay 5 "$API_URL/health"
    curl --fail "$API_URL/v1/model/metadata"

### Actualizaciones posteriores

Para un cambio de código o de modelo, publique el commit —incluido el puntero
`.dvc` actualizado cuando corresponda— y vuelva a ejecutar el paso 7. Terraform
actualiza `image_uri` en la Lambda existente; no recrea API Gateway. Cuando
expire o se reinicie AWS Academy, renueve los tres repository secrets antes de
lanzar el workflow. En una cuenta permanente se recomienda OIDC.

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
