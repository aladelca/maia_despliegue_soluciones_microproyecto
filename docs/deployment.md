# Instalación y despliegue

El orden evita dependencias circulares. El entorno de laboratorio mantiene el estado Terraform y el remoto DVC en buckets separados.

## 1. Bootstrap de estado

    terraform -chdir=infra/terraform/bootstrap init
    terraform -chdir=infra/terraform/bootstrap apply \
      -var='owner=<owner>' \
      -var='state_bucket_name=<nombre-global-unico>'

## 2. Foundation

Copie los archivos example y complete valores no secretos. Inicialice el backend parcial y aplique S3 DVC, ECR y GitHub OIDC:

    terraform -chdir=infra/terraform/foundation init \
      -backend-config=../environments/dev/foundation.tfbackend
    terraform -chdir=infra/terraform/foundation plan -var-file=../environments/dev/foundation.tfvars
    terraform -chdir=infra/terraform/foundation apply -var-file=../environments/dev/foundation.tfvars

Compruebe el remoto versionado siguiendo `docs/dvc-s3.md` y ejecute `dvc push`.

Copie el output `github_deploy_role_arn` al secreto de entorno `AWS_DEPLOY_ROLE_ARN` de GitHub. Configure también las variables `AWS_REGION`, `TERRAFORM_STATE_BUCKET`, `OWNER`, `ALLOWED_ORIGIN` y, si cambia el nombre por defecto, `ECR_REPOSITORY`. La URL del remoto DVC no es un secreto: está versionada en `.dvc/config`. El rol confía en el environment `dev` y dispone únicamente de las operaciones necesarias sobre el bucket de estado, ECR y los recursos nombrados del servicio.

El workflow `Deploy API` se ejecuta manualmente desde GitHub Actions. Se mantiene en modo `workflow_dispatch` mientras Phase 6 esté pendiente para impedir despliegues fallidos o creación involuntaria de recursos al fusionar en `main`. Después de configurar y verificar AWS, DVC y el environment `dev`, el equipo puede habilitar un trigger automático protegido.

### Variante para AWS Academy `voclabs`

El rol temporal del laboratorio puede administrar S3, ECR, Lambda y API Gateway, pero no crear IAM/OIDC. Cargue `.env`; ese archivo ignorado por Git contiene los nombres reales del backend, del remoto y de `LabRole`:

    set -a
    source .env
    set +a
    aws sts get-caller-identity
    : "${TF_STATE_BUCKET:?Falta TF_STATE_BUCKET en .env}"
    : "${LAB_ROLE_ARN:?Falta LAB_ROLE_ARN en .env}"

    aws s3 cp infra/terraform/bootstrap/terraform.tfstate \
      "s3://$TF_STATE_BUCKET/online-shoppers/dev/bootstrap.tfstate"

    terraform -chdir=infra/terraform/foundation init -reconfigure \
      -backend-config="bucket=$TF_STATE_BUCKET" \
      -backend-config="key=$TF_FOUNDATION_STATE_KEY" \
      -backend-config="region=$CLOUD_AWS_REGION" \
      -backend-config='use_lockfile=true' \
      -backend-config='encrypt=true'

    terraform -chdir=infra/terraform/foundation apply \
      -var="owner=$CLOUD_OWNER" \
      -var="dvc_bucket_name=$DVC_S3_BUCKET" \
      -var="terraform_state_bucket_name=$TF_STATE_BUCKET" \
      -var='github_owner=aladelca' \
      -var='github_repository=maia_despliegue_soluciones_microproyecto' \
      -var='enable_deployment_resources=true' \
      -var='enable_github_oidc_resources=false'

Esta combinación administra DVC y ECR, pero devuelve `null` para el rol OIDC de GitHub Actions. En `voclabs`, guarde `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y `AWS_SESSION_TOKEN` como repository secrets de GitHub. El workflow pasa `LAMBDA_EXECUTION_ROLE_ARN` al servicio para reutilizar `LabRole` sin crear IAM. Los secrets deben actualizarse cada vez que expira o se reinicia la sesión del laboratorio.

El stack `bootstrap` usa estado local porque crea el propio backend. Después de su primer `apply`, guarde la copia indicada en el bucket versionado. Antes de modificar el bootstrap desde otra máquina, recupérela así:

    aws s3 cp \
      "s3://$TF_STATE_BUCKET/online-shoppers/dev/bootstrap.tfstate" \
      infra/terraform/bootstrap/terraform.tfstate

## 3. Imagen y service

El workflow `.github/workflows/deploy-api.yml` obtiene el modelo desde DVC/S3, construye la imagen `linux/amd64`, publica un tag igual al Git SHA y resuelve su digest. `service` exige una URI con `@sha256` y rechaza `latest`. En `voclabs` se ejecuta con repository secrets temporales; en una cuenta permanente se recomienda OIDC.

    gh workflow run deploy-api.yml --ref feature/implement-dvc-remote-on-amazon-s3
    gh run list --workflow deploy-api.yml --limit 5

Revise costos y el plan antes de apply. Después valide /health y /v1/predict.

## 4. Vercel

Conecte el repositorio GitHub desde el dashboard de Vercel, seleccione `web` como Root Directory y deje que Vercel detecte Next.js. Configure `NEXT_PUBLIC_API_BASE_URL` con la URL de API Gateway para Preview y Production. Cada push o pull request se construirá desde GitHub; el frontend no usa Docker. Actualice `allowed_origin` en Terraform con el dominio definitivo.

## Rollback

- API: reaplique service con el digest anterior.
- Frontend: promueva el deployment Vercel anterior.
- Modelo/datos: cambie al commit que referencia la versión DVC y ejecute dvc pull.
- Nunca destruya los buckets protegidos como parte de un rollback.
