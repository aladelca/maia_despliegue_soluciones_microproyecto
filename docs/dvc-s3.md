# DVC con Amazon S3

El CSV y `models/champion.joblib` están rastreados por DVC. Git conserva únicamente los archivos `.dvc`; el contenido vive bajo el prefijo `online-shoppers/` del bucket privado `maia-online-shoppers-dvc-712986489191-us-east-1`, administrado por Terraform desde `infra/terraform/foundation`.

## Configuración

El remoto compartido está versionado en `.dvc/config` y no contiene credenciales:

    uv run dvc remote list

No escriba access keys en `.dvc/config`. Use AWS SSO/perfiles localmente. En
GitHub Actions, prefiera OIDC para cuentas permanentes; `voclabs` usa los tres
repository secrets temporales documentados en el README.

Antes de operar contra el remoto, valide la cuenta y la región esperadas:

    aws sts get-caller-identity
    aws configure get region

## Flujo normal

    uv run dvc pull
    uv run dvc status
    uv run dvc add data/raw/online_shoppers_intention.csv
    uv run dvc add models/champion.joblib
    uv run dvc push

## Promoción desde la campaña EC2

La campaña lee el dataset por su key content-addressed y copia su salida a un bucket MLflow
separado. Después de seleccionar el champion, descargue `models/champion.joblib`, copie la metadata
y los reportes del mismo prefijo de campaña, y publique el binario:

    uv run dvc add models/champion.joblib
    uv run dvc push models/champion.joblib.dvc
    uv run dvc status

El pointer `.dvc`, `models/model_metadata.json` y los reportes deben entrar en el mismo commit. El
joblib permanece ignorado por Git. Antes de desplegar, confirme que el SHA-256 del archivo coincide
con `metadata["sha256"]`; el README incluye el comando reproducible.

El bucket DVC almacena las versiones promovidas del dataset/modelo. El bucket MLflow almacena
artifacts de runs y copias de outputs; no deben confundirse ni usar el mismo state Terraform.

Para comprobar el remoto sin arriesgar la copia de trabajo, clone el repositorio en un directorio temporal y ejecute allí `uv run dvc pull`. No borre simultáneamente los archivos materializados, la caché local y el remoto.

El bucket bloquea todo acceso público, exige TLS, usa ownership `BucketOwnerEnforced`, cifra con SSE-S3 y conserva versiones. Las versiones no actuales expiran después de 90 días y las cargas multipart incompletas después de 7 días.
