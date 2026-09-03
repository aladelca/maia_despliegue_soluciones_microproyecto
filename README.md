# Online Shoppers Purchasing Intention

Prototipo académico para estimar si una sesión de comercio electrónico terminará en compra. El proyecto usa el dataset Online Shoppers Purchasing Intention de UCI, un pipeline supervisado de scikit-learn, MLflow para experimentos, DVC con un remoto S3 para datos/artefactos, FastAPI para inferencia y una pantalla Next.js para consumir la API.

## Arquitectura

- Campaña reproducible en una instancia EC2 temporal; la lógica reutilizable vive en
  `src/online_shoppers` y el notebook canónico en `notebook/` consume sus resultados.
- Dataset y champion versionados con DVC en un bucket S3 privado administrado por Terraform.
- MLflow se ejecuta en EC2, persiste su backend SQLite en EBS y guarda artefactos y resultados
  de campaña en un segundo bucket S3 privado.
- FastAPI se adapta a Lambda mediante Mangum y se empaqueta, junto con el champion, como una
  imagen inmutable de ECR.
- API Gateway expone HTTPS; Next.js se construye desde `web/` y se despliega en Vercel.
- Terraform separa los ciclos de vida de `bootstrap`, `foundation`, `mlflow` y `service`.

## Cambios de la Entrega 2

- Feature engineering dentro del pipeline para evitar leakage: agregados de duración y páginas,
  ratios de engagement, transformaciones logarítmicas, estacionalidad, tráfico infrecuente e
  interacciones de visitante/fin de semana.
- Comparación de 66 configuraciones: dummy, regresión logística, Random Forest, Extra Trees,
  HistGradientBoosting, CatBoost, XGBoost, LightGBM y MLP de PyTorch; cada candidato se registra
  como un child run de MLflow.
- Separación por sesiones duplicadas mediante `StratifiedGroupKFold`: un audit set sellado y
  cinco folds para selección por PR-AUC. El umbral se elige únicamente con predicciones OOF.
- Registro del ganador en MLflow Model Registry como
  `online-shoppers-purchase-intention`, versión `1`, alias `champion`.
- Promoción del CatBoost ganador a DVC/S3 y despliegue por digest OCI inmutable en Lambda.
- Endpoint `/v1/model/metadata` y tablero Next.js conectado a metadata y predicciones reales. El
  dashboard incluye resumen ejecutivo, análisis descriptivo, formulario de inferencia, historial
  local, leaderboard de experimentación y trazabilidad del proyecto.
- Terraform para EC2/MLflow/S3, protección contra destrucción, autoapagado y acceso al puerto
  5000 restringido a un CIDR confiable.

Resultado de la campaña versionada:

| Resultado | Valor |
| --- | --- |
| Candidatos terminados | 66 de 66 |
| Champion | `catboost__engineered_with_page_values__depth_8_lr_0.03_l2_5` |
| PR-AUC CV | `0.7562 ± 0.0225` |
| F1 OOF | `0.6905` |
| PR-AUC audit | `0.7368` |
| F1 audit | `0.6636` |
| Umbral | `0.5674` |

Estado operativo documentado:

- API Gateway/Lambda: <https://nzm0y8hoja.execute-api.us-east-1.amazonaws.com>.
- EC2 de MLflow: detenida después de la campaña; EBS y S3 conservan los runs.
- Vercel: [dashboard público de producción](https://maia-despliegue-soluciones-micropro.vercel.app),
  conectado a GitHub y al API mediante CORS restringido a ese origin estable.

Consulte la [arquitectura](docs/architecture.md), la
[guía de experimentación](docs/experimentation.md), la
[guía de despliegue](docs/deployment.md) y la
[evidencia técnica](docs/evidence/e2/README.md) para el detalle.

## Reproducir la solución completa

Los comandos siguientes reconstruyen la infraestructura, ejecutan la campaña en EC2, recuperan
el champion trazable, despliegan el API en AWS y conectan un proyecto Vercel. Ejecútelos desde la
raíz de un clon limpio. Los nombres globales de buckets deben sustituirse por valores disponibles
en la cuenta que se use.

### 1. Instalar herramientas y dependencias

Se necesita Git, AWS CLI, Terraform y, para controlar Actions desde terminal,
GitHub CLI. En macOS con Homebrew:

    brew install awscli gh uv node
    brew tap hashicorp/tap
    brew install hashicorp/tap/terraform
    aws --version
    terraform version
    gh --version

Instale las dependencias bloqueadas y valide el checkout antes de crear recursos:

    uv sync --all-groups --locked
    npx --yes pnpm@11.21.0 --dir web install --frozen-lockfile
    uv run pytest -q
    npx --yes pnpm@11.21.0 --dir web test

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

En AWS Academy la identidad normalmente muestra un ARN `assumed-role/voclabs/...`. En otra cuenta,
ajuste nombres, roles y variables de acuerdo con sus políticas. Las credenciales temporales nunca
se pasan como variables Terraform ni se guardan en archivos versionados.

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

### 5. Publicar y resolver la versión exacta del dataset

Materialice el CSV con `dvc pull` o publíquelo una vez con `dvc push`. Después construya la URI
content-addressed que usará EC2; no se entrega a la campaña una ruta mutable:

    DATA_HASH=$(awk '$2 == "md5:" { print $3 }' \
      data/raw/online_shoppers_intention.csv.dvc)
    test -n "$DATA_HASH"
    DATA_KEY="$DVC_S3_PREFIX/files/md5/$(printf %s "$DATA_HASH" | cut -c1-2)/$(printf %s "$DATA_HASH" | cut -c3-)"
    aws s3api head-object --bucket "$DVC_S3_BUCKET" --key "$DATA_KEY"
    export DVC_DATA_VERSION="md5:$DATA_HASH"
    export DVC_DATASET_S3_URI="s3://$DVC_S3_BUCKET/$DATA_KEY"

Si `head-object` falla, un responsable que tenga el CSV materializado debe ejecutar:

    uv run dvc add data/raw/online_shoppers_intention.csv
    uv run dvc push data/raw/online_shoppers_intention.csv.dvc

### 6. Ejecutar la campaña EC2/MLflow

La cuenta debe ofrecer un instance profile con lectura/escritura S3 y acceso SSM; AWS Academy
incluye normalmente `LabInstanceProfile`. Copie los ejemplos a archivos ignorados por Git:

    cp infra/terraform/environments/dev/mlflow.example.tfbackend \
      infra/terraform/environments/dev/mlflow.tfbackend
    cp infra/terraform/environments/dev/mlflow.example.tfvars \
      infra/terraform/environments/dev/mlflow.tfvars

Complete ambos archivos. En `mlflow.tfvars` use:

- un bucket globalmente único para `artifact_bucket_name`;
- `dvc_dataset_s3_uri` igual a `$DVC_DATASET_S3_URI`;
- `dvc_data_version` igual a `$DVC_DATA_VERSION`;
- la URL HTTPS pública del repositorio y una rama o tag existente en `git_ref`;
- su IP pública seguida de `/32` en `allowed_cidr`;
- el instance profile autorizado en `instance_profile_name`.

Inicialice, revise el plan y aplíquelo:

    terraform -chdir=infra/terraform/mlflow init -reconfigure \
      -backend-config=../environments/dev/mlflow.tfbackend
    terraform -chdir=infra/terraform/mlflow plan \
      -var-file=../environments/dev/mlflow.tfvars \
      -out=/tmp/online-shoppers-mlflow.tfplan
    terraform -chdir=infra/terraform/mlflow apply \
      /tmp/online-shoppers-mlflow.tfplan

El `user_data` clona la revisión indicada, construye dos contenedores —MLflow y la campaña—,
descarga el objeto DVC exacto y ejecuta el perfil `full`. Consulte URL, instancia y logs así:

    MLFLOW_INSTANCE_ID=$(terraform -chdir=infra/terraform/mlflow output -raw instance_id)
    MLFLOW_BUCKET=$(terraform -chdir=infra/terraform/mlflow output -raw artifact_bucket_name)
    MLFLOW_URL=$(terraform -chdir=infra/terraform/mlflow output -raw mlflow_url)
    aws ec2 wait instance-status-ok --instance-ids "$MLFLOW_INSTANCE_ID"
    printf 'MLflow: %s\nEC2: %s\n' "$MLFLOW_URL" "$MLFLOW_INSTANCE_ID"
    aws ssm start-session \
      --target "$MLFLOW_INSTANCE_ID" \
      --document-name AWS-StartInteractiveCommand \
      --parameters 'command=["sudo tail -f /var/log/online-shoppers-bootstrap.log"]'

El comando SSM anterior requiere el Session Manager plugin. En otra terminal, verifique el estado
publicado en S3; reemplace `<git-ref>` por el mismo valor de `git_ref`:

    aws s3 cp \
      "s3://$MLFLOW_BUCKET/campaign-output/<git-ref>/status" -

La salida debe ser `success`. MLflow queda disponible en `$MLFLOW_URL` mientras la instancia está
encendida y sólo desde el CIDR configurado.

El bootstrap ejecuta la campaña cuando se crea una EC2 nueva. Reiniciar una instancia existente
sólo recupera su MLflow; cambiar `git_ref` en el mismo state no vuelve a ejecutar `cloud-init`. Para
otra campaña aislada use un backend key, `environment` y bucket de artifacts nuevos, o ejecute el
contenedor de experimentación de forma explícita mediante SSM.

### 7. Recuperar y promover el champion

Descargue los resultados con el mismo prefijo de la campaña y valide que no hubo fallos:

    CAMPAIGN_DIR=/tmp/online-shoppers-campaign
    mkdir -p "$CAMPAIGN_DIR"
    aws s3 sync \
      "s3://$MLFLOW_BUCKET/campaign-output/<git-ref>/" \
      "$CAMPAIGN_DIR/"
    test "$(tr -d '\n' < "$CAMPAIGN_DIR/status")" = success
    python - <<'PY'
    import json
    from pathlib import Path

    comparison = json.loads(
        Path("/tmp/online-shoppers-campaign/reports/experiments/final_model_comparison.json")
        .read_text(encoding="utf-8")
    )
    assert len(comparison["candidates"]) == 66
    assert comparison["failures"] == []
    print(comparison["champion"])
    PY

Promueva juntos el binario y sus documentos de trazabilidad:

    cp "$CAMPAIGN_DIR/models/champion.joblib" models/champion.joblib
    cp "$CAMPAIGN_DIR/models/model_metadata.json" models/model_metadata.json
    cp "$CAMPAIGN_DIR/reports/model_metrics.json" reports/model_metrics.json
    cp "$CAMPAIGN_DIR/reports/experiments/final_model_comparison.json" \
      reports/experiments/final_model_comparison.json
    cp "$CAMPAIGN_DIR/reports/experiments/protocol_manifest.json" \
      reports/experiments/protocol_manifest.json
    uv run dvc add models/champion.joblib
    uv run dvc push models/champion.joblib.dvc
    uv run pytest -q

Confirme el checksum del artefacto antes de desplegar:

    python - <<'PY'
    import hashlib
    import json
    from pathlib import Path

    artifact = Path("models/champion.joblib")
    metadata = json.loads(Path("models/model_metadata.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == metadata["sha256"]
    print(metadata["champion"], metadata["mlflow_run_id"])
    PY

Versione juntos el pointer y los documentos de trazabilidad —nunca el joblib— y fusione el PR
validado antes de desplegar desde `main`:

    git add \
      models/champion.joblib.dvc \
      models/model_metadata.json \
      reports/model_metrics.json \
      reports/experiments/final_model_comparison.json \
      reports/experiments/protocol_manifest.json
    git commit -m "feat(model): promote EC2 MLflow champion"
    git push

Detenga la instancia cuando termine de consultar MLflow. EBS y S3 conservan los runs:

    aws ec2 stop-instances --instance-ids "$MLFLOW_INSTANCE_ID"
    aws ec2 wait instance-stopped --instance-ids "$MLFLOW_INSTANCE_ID"
    terraform -chdir=infra/terraform/mlflow apply -refresh-only -auto-approve \
      -var-file=../environments/dev/mlflow.tfvars

### 8. Configurar GitHub Actions

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

### 9. Desplegar Lambda y API Gateway

El workflow realiza `dvc pull`, pruebas, build `linux/amd64`, push a ECR,
resolución del digest, `terraform apply` y smoke test. Desde `main`:

> [!NOTE]
> El workflow versionado valida la cuenta AWS Academy `712986489191`. Para replicarlo en otra
> cuenta, cambie `allowed-account-ids` y todos los nombres/ARN configurados antes de ejecutarlo.

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

Pruebe inferencia con el payload completo de la sección
[Generar una predicción mediante la API](#generar-una-predicción-mediante-la-api), sustituyendo
`http://localhost:8000` por `$API_URL`.

### 10. Desplegar el frontend en Vercel

Importe el repositorio desde Vercel después de fusionar la rama validada en `main` y configure:

| Campo | Valor |
| --- | --- |
| Framework Preset | `Next.js` |
| Root Directory | `web` |
| Install Command | `pnpm install --frozen-lockfile` |
| Build Command | `pnpm build` |
| Output Directory | `.next` |
| Variable | `NEXT_PUBLIC_API_BASE_URL=https://<api-id>.execute-api.us-east-1.amazonaws.com` |

No importe en Vercel las variables del `.env.example` raíz ni credenciales AWS. Después del primer
deployment, copie su origen exacto —por ejemplo `https://mi-proyecto.vercel.app`, sin `/` final—,
actualice CORS y vuelva a ejecutar el workflow:

    gh variable set ALLOWED_ORIGIN --body https://<proyecto>.vercel.app
    gh workflow run deploy-api.yml --ref main

Verifique el enlace completo:

    curl --fail "$API_URL/health"
    curl --fail \
      -X OPTIONS "$API_URL/v1/predict" \
      -H 'Origin: https://<proyecto>.vercel.app' \
      -H 'Access-Control-Request-Method: POST' \
      -H 'Access-Control-Request-Headers: content-type' \
      -D - -o /dev/null

Abra el dominio Vercel, confirme que aparezcan el nombre del champion, los IDs de MLflow, PR-AUC
y umbral, y envíe una predicción real.

El dashboard combina tres fuentes explícitas:

- `reports/eda_summary.json` para KPIs y gráficas descriptivas;
- `reports/experiments/final_model_comparison.json` para el leaderboard de candidatos;
- `GET /v1/model/metadata` y `POST /v1/predict` para el champion y las inferencias actualmente
  desplegadas. El historial se conserva sólo en `localStorage` del navegador.

### Actualizaciones posteriores

Para un cambio de código o de modelo, publique el commit —incluido el puntero
`.dvc` actualizado cuando corresponda— y vuelva a ejecutar el paso 9. Terraform
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

Ese notebook genera un baseline y registro MLflow locales para desarrollo; no reproduce ni
reemplaza el champion de la campaña EC2 `full`. Si desea ejecutar primero el análisis exploratorio,
use:

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
autorizadas, use `dvc pull` para recuperar los objetos del remoto. El perfil smoke puede validar
el orquestador en una base MLflow local sin ejecutar la campaña completa:

    uv run python -m online_shoppers experiment \
      --profile smoke \
      --tracking-uri sqlite:///mlflow.db \
      --data-path data/raw/online_shoppers_intention.csv \
      --output-root /tmp/online-shoppers-smoke
    uv run mlflow ui --backend-store-uri sqlite:///mlflow.db

El perfil `full` exige un tracking URI HTTP y está diseñado para EC2. Selecciona por PR-AUC promedio
en cinco folds group-aware, calcula el umbral por F1 OOF y consulta el audit set una sola vez después
de declarar el champion.

## Validación

    uv run ruff format --check src tests notebook/online-shoppers-ec2-large.ipynb
    uv run ruff check src tests notebook/online-shoppers-ec2-large.ipynb
    uv run mypy src tests
    uv run pytest -q
    pnpm --dir web lint
    pnpm --dir web typecheck
    pnpm --dir web test
    pnpm --dir web build
    terraform fmt -check -recursive infra/terraform

Consulte docs/installation-guide.md para instalación completa y docs/user-guide.md para uso.

## Fuente

Sakar, C. y Kastro, Y. (2018), Online Shoppers Purchasing Intention Dataset, UCI Machine Learning Repository, DOI 10.24432/C5F88Q, licencia CC BY 4.0.
