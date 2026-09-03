# Evidencia técnica de Entrega 2

## Resultado desplegado

- API Gateway: <https://nzm0y8hoja.execute-api.us-east-1.amazonaws.com>
- Frontend Vercel: <https://temporary-quick-indigo-ntrfzf9.vercel.app>
- Pull request: <https://github.com/aladelca/maia_despliegue_soluciones_microproyecto/pull/6>
- Lambda: `online-shoppers-ml-dev-api`
- Imagen ECR inmutable: `sha256:6c7fcdd5b57655951e82cea1f9d5df9b4e5435a649b78f96841a0157830a8044`
- Commit ejecutado por la campaña: `cb1a3433c1b509c695147cd56c81d325e77ca436`
- Dataset DVC: `md5:cc6ec1db03b4f10f8de52c56ff48b085`

El deployment de Vercel se creó en modo temporal y fue validado extremo a extremo. Debe reclamarse
desde la cuenta del equipo para conservarlo después de la ventana temporal del preview.

## Campaña EC2 y MLflow

- EC2: `i-086475cc1eb969d17`, `t3.medium`, `us-east-1`; estado final `stopped`.
- Experimento: `online-shoppers-ec2-large-experiment` (ID `1`).
- Parent run: `f05ac6087e2b4e7e9a5f1a842d019159`.
- Runs terminales: 68 (`66` candidatos, `1` parent y `1` champion), todos `FINISHED`.
- Fallos de candidatos: `0`.
- Champion run: `315cd8d316ba47a899f6ba249cc721d9`.
- Registry: `online-shoppers-purchase-intention`, versión `1`, alias `champion`, estado `READY`.
- Artefactos MLflow: bucket S3 privado, cifrado, versionado y con bloqueo de acceso público.

La instancia se detuvo después de las capturas para evitar costo, sin terminarla ni borrar EBS/S3.
Al reiniciarla, Terraform conserva el backend y MLflow vuelve a exponer los mismos runs.

## Champion

- Configuración: `catboost__engineered_with_page_values__depth_8_lr_0.03_l2_5`.
- Selección: mayor PR-AUC promedio en cinco folds `StratifiedGroupKFold`.
- PR-AUC CV: `0.7562165276 ± 0.0224940549`.
- F1 OOF: `0.6904691649`.
- Brier OOF: `0.0842858338`.
- PR-AUC audit: `0.7368047815`.
- F1 audit: `0.6635838150`.
- Umbral seleccionado sólo con predicciones OOF: `0.5673544537`.
- Checksum SHA-256 del joblib: `9fbb9d174c69da5ba632498ba0b53f02382d0aa12f530bc2420241a1d39640e2`.
- Pointer DVC: `md5:66c2259aa408a8a7cf07546dc64247d5`.

## Validaciones ejecutadas

- `58` tests Python aprobados; Ruff del alcance nuevo y mypy sin hallazgos.
- `6` tests web aprobados; ESLint, TypeScript y build de producción aprobados.
- Notebook canónico ejecutado con `nbconvert` sobre los resultados reales.
- Terraform MLflow y service validados; los applies fueron sólo adiciones o actualizaciones in-place,
  sin destrucciones.
- `/health`, `/v1/model/metadata` y `/v1/predict` respondieron `200` con el champion correcto.
- Preflight CORS devolvió el origen exacto de Vercel.
- CloudWatch registró el smoke test sin errores; la inferencia caliente fue sub-segundo.
- Prueba real con navegador Vercel → API Gateway → Lambda → CatBoost aprobada.

## Capturas

- `mlflow-ec2-running.png`: campaña remota con parámetros de protocolo y child runs.
- `mlflow-ec2-champion.png`: métricas, tags, run ID y modelo del champion.
- `mlflow-model-registry.png`: versión `1` con alias `champion`.
- `vercel-api-prediction.png`: metadata de MLflow y predicción real servidas desde AWS.

Las capturas y este documento no contienen claves, tokens, cookies ni contenido de Terraform state.
