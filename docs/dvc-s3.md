# DVC con Amazon S3

El CSV y `models/champion.joblib` están rastreados por DVC. Git conserva únicamente los archivos `.dvc`; el contenido vive bajo el prefijo `online-shoppers/` del bucket privado `maia-online-shoppers-dvc-712986489191-us-east-1`, administrado por Terraform desde `infra/terraform/foundation`.

## Configuración

El remoto compartido está versionado en `.dvc/config` y no contiene credenciales:

    uv run dvc remote list

No escriba access keys en .dvc/config. Use AWS SSO/perfiles localmente y OIDC en GitHub Actions.

Antes de operar contra el remoto, valide la cuenta y la región esperadas:

    aws sts get-caller-identity
    aws configure get region

## Flujo normal

    uv run dvc pull
    uv run dvc status
    uv run dvc add data/raw/online_shoppers_intention.csv
    uv run dvc add models/champion.joblib
    uv run dvc push

Para comprobar el remoto sin arriesgar la copia de trabajo, clone el repositorio en un directorio temporal y ejecute allí `uv run dvc pull`. No borre simultáneamente los archivos materializados, la caché local y el remoto.

El bucket bloquea todo acceso público, exige TLS, usa ownership `BucketOwnerEnforced`, cifra con SSE-S3 y conserva versiones. Las versiones no actuales expiran después de 90 días y las cargas multipart incompletas después de 7 días.
