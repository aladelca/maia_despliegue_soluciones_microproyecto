# Instalación y despliegue

## Orden de despliegue

La solución tiene cuatro estados Terraform y dos planos de ejecución independientes:

```text
bootstrap -> foundation/DVC -> mlflow/EC2 -> promoción del champion
                                             |
                                             v
                                      ECR -> service/API
                                             |
                                             v
                                           Vercel
                                             |
                                             v
                                     actualización de CORS
```

El frontend puede construirse antes del API porque obtiene la metadata en el navegador, pero no
podrá consultar ni predecir hasta que API Gateway permita su origen exacto.

## Prerrequisitos

- AWS CLI autenticado en la cuenta correcta y región `us-east-1`.
- Terraform 1.10 o superior, `uv`, GitHub CLI, Docker y Node.js 24.
- Un instance profile EC2 con acceso a S3 y SSM; en AWS Academy suele llamarse
  `LabInstanceProfile`.
- Un rol Lambda existente, como `LabRole`, cuando la cuenta no permite crear IAM.
- Dataset publicado en el remoto DVC/S3.
- Acceso al repositorio desde Vercel.

Use credenciales temporales mediante variables de entorno, perfil AWS u OIDC. Nunca confirme
`.env`, `*.tfvars`, `*.tfbackend`, state, CSV, joblib o credenciales.

## 1. Bootstrap y foundation

`bootstrap` crea el bucket del backend desde estado local. `foundation` usa ese backend para crear
el bucket DVC y ECR. La receta completa, incluidos los comandos de recuperación del state en un
clon nuevo, está en [Reproducir la solución completa](../README.md#reproducir-la-solución-completa).

Para AWS Academy, deshabilite recursos OIDC y reutilice los roles del laboratorio:

```bash
terraform -chdir=infra/terraform/foundation apply \
  -var="owner=$CLOUD_OWNER" \
  -var="dvc_bucket_name=$DVC_S3_BUCKET" \
  -var="terraform_state_bucket_name=$TF_STATE_BUCKET" \
  -var='github_owner=aladelca' \
  -var='github_repository=maia_despliegue_soluciones_microproyecto' \
  -var='enable_deployment_resources=true' \
  -var='enable_github_oidc_resources=false'
```

En una cuenta permanente puede habilitar OIDC y entregar a GitHub el output
`github_deploy_role_arn`, sin guardar access keys.

## 2. Campaña EC2/MLflow

Copie y complete los ejemplos ignorados por Git:

```bash
cp infra/terraform/environments/dev/mlflow.example.tfbackend \
  infra/terraform/environments/dev/mlflow.tfbackend
cp infra/terraform/environments/dev/mlflow.example.tfvars \
  infra/terraform/environments/dev/mlflow.tfvars
terraform -chdir=infra/terraform/mlflow init -reconfigure \
  -backend-config=../environments/dev/mlflow.tfbackend
terraform -chdir=infra/terraform/mlflow plan \
  -var-file=../environments/dev/mlflow.tfvars \
  -out=/tmp/online-shoppers-mlflow.tfplan
terraform -chdir=infra/terraform/mlflow apply /tmp/online-shoppers-mlflow.tfplan
```

El apply crea un bucket de artifacts, security group y una EC2 `t3.medium`. El bootstrap de la
instancia:

1. habilita Docker y 4 GiB de swap;
2. programa autoapagado a cuatro horas;
3. clona `repository_url` en `git_ref` y registra el SHA resuelto;
4. inicia MLflow 3.15.1 con SQLite en EBS y artifacts en S3;
5. descarga el objeto DVC indicado por `dvc_dataset_s3_uri`;
6. construye el contenedor CPU-only y ejecuta el perfil `full`;
7. sincroniza outputs y status a `s3://<bucket>/campaign-output/<git-ref>/`.

Monitoree sin abrir SSH:

```bash
INSTANCE_ID=$(terraform -chdir=infra/terraform/mlflow output -raw instance_id)
ARTIFACT_BUCKET=$(terraform -chdir=infra/terraform/mlflow output -raw artifact_bucket_name)
terraform -chdir=infra/terraform/mlflow output -raw mlflow_url
aws ssm start-session \
  --target "$INSTANCE_ID" \
  --document-name AWS-StartInteractiveCommand \
  --parameters 'command=["sudo tail -f /var/log/online-shoppers-bootstrap.log"]'
aws s3 cp "s3://$ARTIFACT_BUCKET/campaign-output/<git-ref>/status" -
```

No despliegue un resultado cuyo status no sea `success`. El runner tiene `prevent_destroy`; se
detiene, no se termina, después de descargar los artifacts.

El `user_data` se ejecuta al crear la instancia, no cada vez que se inicia. Para una campaña nueva,
cree un state/backend key y un bucket de artifacts distintos —y use otro `environment`— o ejecute
el contenedor explícitamente mediante SSM. Cambiar sólo `git_ref` sobre la EC2 existente no repite
`cloud-init`.

## 3. Promoción del modelo

Sincronice el prefijo de campaña, verifique `failures == []`, copie joblib/metadata/reportes y
publique el binario con DVC. Los comandos completos están en el paso 7 del README. El commit de
promoción debe incluir al menos:

```bash
git add \
  models/champion.joblib.dvc \
  models/model_metadata.json \
  reports/model_metrics.json \
  reports/experiments/final_model_comparison.json \
  reports/experiments/protocol_manifest.json
git commit -m "feat(model): promote EC2 MLflow champion"
git push
```

`models/champion.joblib` no se agrega a Git. Antes del commit, `dvc push` debe haber almacenado el
objeto señalado por el nuevo pointer.

## 4. Imagen, Lambda y API Gateway

El workflow `.github/workflows/deploy-api.yml`:

1. obtiene el modelo exacto con `dvc pull`;
2. ejecuta pruebas de integración;
3. construye `docker/api.Dockerfile` para `linux/amd64` sin provenance OCI adicional;
4. publica un tag inmutable igual al Git SHA y resuelve el digest;
5. actualiza Lambda in-place mediante el stack `service`;
6. prueba `/health`.

Configure GitHub en AWS Academy:

```bash
gh secret set AWS_ACCESS_KEY_ID
gh secret set AWS_SECRET_ACCESS_KEY
gh secret set AWS_SESSION_TOKEN
gh variable set AWS_REGION --body us-east-1
gh variable set TERRAFORM_STATE_BUCKET --body <bucket-state>
gh variable set OWNER --body <owner>
gh variable set ECR_REPOSITORY --body online-shoppers-ml-api
gh variable set LAMBDA_EXECUTION_ROLE_ARN --body <arn-lab-role>
gh variable set ALLOWED_ORIGIN --body http://localhost:3000
gh workflow run deploy-api.yml --ref main
```

Los tres secrets de sesión deben renovarse cuando AWS Academy expire. En una cuenta con OIDC, no
se configuran access keys.

Recupere y pruebe el endpoint:

```bash
API_URL=$(aws apigatewayv2 get-apis \
  --region us-east-1 \
  --query "Items[?Name=='online-shoppers-ml-dev'].ApiEndpoint | [0]" \
  --output text)
curl --fail --retry 5 --retry-delay 5 "$API_URL/health"
curl --fail "$API_URL/v1/model/metadata"
```

El servicio actual usa 2048 MB, timeout Lambda de 30 segundos y timeout de integración de 30
segundos. El frontend espera hasta 29 segundos para tolerar el cold start observado; una llamada
caliente debe ser sub-segundo.

## 5. Vercel

Importe `main` desde GitHub con esta configuración:

| Configuración | Valor |
| --- | --- |
| Project Name | `maia-online-shoppers-web` o cualquier slug disponible |
| Framework Preset | `Next.js` |
| Root Directory | `web` |
| Install Command | `pnpm install --frozen-lockfile` |
| Build Command | `pnpm build` |
| Output Directory | `.next` |
| Environment Variable | `NEXT_PUBLIC_API_BASE_URL=https://<api-id>.execute-api.us-east-1.amazonaws.com` |

Configure la variable para Preview y Production. No seleccione FastAPI: Python se ejecuta en AWS,
no en Vercel. Ignore las variables sugeridas desde `.env.example` raíz y no copie credenciales AWS.

Una vez Vercel entregue el dominio definitivo, actualice CORS y redespliegue el servicio:

```bash
VERCEL_ORIGIN=https://<proyecto>.vercel.app
gh variable set ALLOWED_ORIGIN --body "$VERCEL_ORIGIN"
gh workflow run deploy-api.yml --ref main
```

El valor debe ser el origin exacto, sin path ni `/` final. Si cambia el dominio de producción,
repita el update. El frontend incorpora `NEXT_PUBLIC_*` en build time, así que también necesita un
redeploy si cambia `API_URL`.

## 6. Verificación final

```bash
curl --fail "$API_URL/health"
curl --fail "$API_URL/v1/model/metadata"
curl --fail -X OPTIONS "$API_URL/v1/predict" \
  -H "Origin: $VERCEL_ORIGIN" \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type' \
  -D - -o /dev/null
```

Además de HTTP 200, confirme en el navegador que el panel muestre champion, run ID, hash DVC,
PR-AUC CV/audit y umbral, y que una predicción devuelva la misma `model_version` de `/health`.

## Operación y rollback

- **MLflow:** inicie la EC2 existente para consultar runs; la nueva IP aparece en
  `terraform output mlflow_url`. Deténgala al terminar. No use `terraform destroy` sobre los
  recursos protegidos.
- **API:** reaplique `service` con el digest ECR anterior.
- **Frontend:** promueva un deployment Vercel anterior.
- **Modelo/datos:** cambie al commit con el pointer DVC deseado y ejecute `dvc pull`.
- **CORS:** cada dominio Vercel nuevo requiere aplicar `allowed_origin` y un smoke preflight.
