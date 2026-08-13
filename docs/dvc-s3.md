# DVC con Amazon S3

El CSV y models/champion.joblib están rastreados por DVC. Git conserva únicamente los archivos .dvc; el contenido se publicará en un bucket S3 privado creado en infra/terraform/foundation.

## Configuración

Después de aplicar foundation, reemplace el placeholder versionado:

    DVC_BUCKET=$(terraform -chdir=infra/terraform/foundation output -raw dvc_bucket_name)
    uv run dvc remote add -f -d aws-s3 "s3://${DVC_BUCKET}/online-shoppers"

No escriba access keys en .dvc/config. Use AWS SSO/perfiles localmente y OIDC en GitHub Actions.

## Flujo normal

    uv run dvc pull
    uv run dvc status
    uv run dvc add data/raw/online_shoppers_intention.csv
    uv run dvc add models/champion.joblib
    uv run dvc push

El primer push queda pendiente hasta que exista el bucket. Para demostrar recuperación, elimine únicamente una copia materializada que pueda restaurarse y ejecute dvc pull; no borre la caché y el remoto a la vez.
