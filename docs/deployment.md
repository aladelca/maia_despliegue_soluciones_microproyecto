# Instalación y despliegue

No se ejecutó infraestructura externa durante la implementación. El orden evita dependencias circulares.

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

Configure el remoto con docs/dvc-s3.md y ejecute dvc push.

Copie el output `github_deploy_role_arn` al secreto de entorno `AWS_DEPLOY_ROLE_ARN` de GitHub. Configure también las variables `AWS_REGION`, `TERRAFORM_STATE_BUCKET`, `OWNER`, `ALLOWED_ORIGIN` y, si cambia el nombre por defecto, `ECR_REPOSITORY`; configure el secreto `DVC_REMOTE_URL`. El rol confía en el environment `dev` y dispone únicamente de las operaciones necesarias sobre el bucket de estado, ECR y los recursos nombrados del servicio.

## 3. Imagen y service

Construya la imagen para linux/amd64, publique un tag igual al Git SHA y resuelva su digest. service exige una URI con @sha256 y rechaza latest.

    docker buildx build --platform linux/amd64 --provenance=false -f docker/api.Dockerfile -t <ecr>:<git-sha> .
    terraform -chdir=infra/terraform/service init \
      -backend-config=../environments/dev/service.tfbackend
    terraform -chdir=infra/terraform/service plan -var-file=../environments/dev/service.tfvars

Revise costos y el plan antes de apply. Después valide /health y /v1/predict.

## 4. Vercel

Conecte el repositorio GitHub desde el dashboard de Vercel, seleccione `web` como Root Directory y deje que Vercel detecte Next.js. Configure `NEXT_PUBLIC_API_BASE_URL` con la URL de API Gateway para Preview y Production. Cada push o pull request se construirá desde GitHub; el frontend no usa Docker. Actualice `allowed_origin` en Terraform con el dominio definitivo.

## Rollback

- API: reaplique service con el digest anterior.
- Frontend: promueva el deployment Vercel anterior.
- Modelo/datos: cambie al commit que referencia la versión DVC y ejecute dvc pull.
- Nunca destruya los buckets protegidos como parte de un rollback.
