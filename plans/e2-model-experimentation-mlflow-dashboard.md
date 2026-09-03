# Entrega 2: experimentación, MLflow y tablero

## Source Request

Crear un plan de implementación centrado en código para cumplir los entregables técnicos de
`maia_pds_proy_e2.pdf`: mejorar modelos y feature engineering, incluir nuevos algoritmos y una
red neuronal cuando aporte valor, registrar todos los experimentos en MLflow, completar el tablero
y conservar las fuentes y evidencias técnicas. Se excluyen tanto el reporte académico de máximo
10 páginas como el reporte de trabajo en equipo.

## Completion Snapshot

- Campaña `full` ejecutada en EC2: 66 candidatos × 5 folds, 68 runs MLflow terminales y 0 fallos.
- Champion: CatBoost engineered con `PageValues`, PR-AUC CV `0.7562 ± 0.0225` y audit `0.7368`.
- MLflow Registry: versión `1`, alias `champion`; artefactos remotos en S3 y modelo desplegable en DVC.
- Inferencia: imagen `linux/amd64` inmutable en ECR y Lambda/API Gateway actualizada exitosamente.
- Tablero: preview Vercel conectado por CORS al API; prueba E2E real aprobada y evidencia capturada.

## Goals

- Convertir los notebooks experimentales actuales en un flujo único, reproducible y probado que
  registre en MLflow cada candidato, búsqueda de hiperparámetros y decisión de promoción.
- Evaluar baselines, modelos lineales, árboles/boosters, ensambles y una red neuronal tabular con un
  protocolo group-aware que evite que sesiones duplicadas aparezcan en particiones distintas.
- Comparar de forma explícita variantes con y sin `PageValues`, feature engineering sin fuga de
  información y estrategias apropiadas para el desbalance de `Revenue`.
- Seleccionar y empaquetar un único champion mediante validación cruzada, calibración y un test
  sellado que se consulta una sola vez; no promover un modelo sólo por ser más complejo.
- Centralizar MLflow en una instancia AWS EC2 declarada con Terraform, con backend persistente y
  artefactos en S3, para que todos los integrantes registren sus corridas en el mismo servidor.
- Registrar el champion en MLflow Model Registry y mantener trazabilidad entre run de MLflow,
  commit Git, hash DVC del dataset, artefacto joblib, imagen Docker y versión atendida por la API.
- Completar el tablero Next.js con predicción vía API, metadata dinámica del champion y
  visualizaciones descriptivas relevantes para la pregunta de negocio.
- Desplegar la API ganadora en AWS Lambda/API Gateway y mantener el frontend nativo en Vercel,
  conforme a la restricción posterior del usuario de no ejecutar el frontend en EC2.
- Producir evidencia técnica verificable de MLflow en EC2, funcionamiento del tablero y aportes Git
  sin fabricar commits ni resultados.

## Non-Goals

- Escribir o maquetar el reporte académico de máximo 10 páginas.
- Escribir el reporte de trabajo en equipo de máximo una página.
- Hacer inferencia causal, atribución de campañas, personalización por usuario o predicción de valor
  monetario; el dataset sólo permite clasificación de intención de compra por sesión.
- Implementar reentrenamiento automático, feature store, streaming, Kubernetes, autenticación de
  usuarios finales o una plataforma MLflow de alta disponibilidad.
- Sustituir FastAPI, Next.js, DVC/S3, Terraform, Lambda/API Gateway o el contrato `/v1/predict` sin
  una necesidad demostrada por el champion.
- Promover obligatoriamente una red neuronal. Debe competir bajo el mismo protocolo y sólo puede
  ganar si mejora las métricas y mantiene tamaño, latencia y serialización aceptables.
- Versionar `mlflow.db`, `mlruns/`, el CSV o el joblib directamente en Git; los artefactos pesados
  siguen en S3/MLflow/DVC.

## Assumptions

- El dataset canónico sigue siendo UCI Online Shoppers Purchasing Intention: 12.330 sesiones, 17
  variables predictoras y `Revenue` como target, validado por `src/online_shoppers/data.py`.
- La API pública conserva los 17 campos actuales. Un champion sin `PageValues` puede ignorar ese
  campo internamente sin romper el request existente.
- `F1` sigue siendo la métrica de decisión de umbral por continuidad con `params.yaml`; para ordenar
  modelos se usará también PR-AUC promedio de validación cruzada, apropiado para la clase positiva
  minoritaria. La regla final y sus desempates quedarán declarados en configuración, no en notebooks.
- La red neuronal challenger usa PyTorch con tres arquitecturas acotadas por feature set. La campaña
  se ejecuta en Linux EC2, por lo que usa CPU; MPS sólo se selecciona al ejecutar en hardware Apple.
  El wrapper exporta pesos NumPy y preserva el pipeline joblib/FastAPI sin Torch en inferencia.
- El remoto DVC S3 existente es la fuente del CSV y del champion. Se añadirá un bucket S3 separado
  para artefactos MLflow para no mezclar ciclos de vida ni permisos.
- La instancia EC2 de MLflow puede detenerse después de recolectar soportes, pero no terminarse; su
  volumen EBS y los artefactos S3 deben persistir, conforme al PDF.
- `mlflow_allowed_cidr`, tipo de instancia, AMI y región son variables Terraform. VocLabs permitió
  `t3.medium` en `us-east-1`; se añadió swap acotado porque la política negó instancias mayores.
- Los nombres/autores observados en `git shortlog --all` representan a los integrantes; cada persona
  debe realizar al menos un commit sustantivo propio de esta implementación.

## Open Questions Resolved During Implementation

- MLflow quedó restringido al CIDR de trabajo; el puerto 5000 nunca se abrió a `0.0.0.0/0`.
- La campaña usó una EC2 `t3.medium` permitida por VocLabs, con 4 GiB de swap y apagado automático.
- El frontend permanece en Vercel; sólo MLflow/experimentación se ejecutaron en EC2 y la inferencia
  ganadora se desplegó en la Lambda/API Gateway existente.

## Current Repo Context

- `src/online_shoppers/training.py` ya entrena dummy, regresión logística y random forest, compara
  con/sin `PageValues`, registra seis candidatos y un champion en MLflow, y escribe un `ModelBundle`.
- `notebooks/03_model_experiments.ipynb` agrega feature engineering, ExtraTrees, Gradient Boosting,
  HistGradientBoosting, CatBoost, stacking y blending. Su resumen versionado contiene 38 candidatos;
  el mejor experimental es `stacking_trees__engineered_full`, pero no fue promovido al artefacto.
- `notebooks/04_advanced_experiments.ipynb` agrega XGBoost, LightGBM, CatBoost, focal loss,
  `RandomizedSearchCV` de cinco folds y calibración. El propio notebook advierte que el conjunto de
  test pudo mirarse más de una vez a lo largo de la serie, por lo que hace falta un protocolo nuevo.
- El `mlflow.db` local contiene 80 runs finalizados en tres experimentos: 7 runs base y 73 avanzados.
  Todos tienen parámetros, métricas y tags, pero el almacén está ignorado por Git, no es compartido,
  no existe MLflow en EC2 y el Model Registry tiene cero modelos/versiones.
- Los helpers avanzados de features, candidatos y logging están duplicados dentro de los notebooks
  03/04. La lógica canónica de `src/` todavía sólo sabe producir el random forest base.
- `models/model_metadata.json` y `reports/model_metrics.json` describen el champion base
  `random_forest__with_page_values` (F1 test aproximado 0,6735), no el mejor resultado de las rondas
  experimentales. El joblib se versiona correctamente mediante `models/champion.joblib.dvc`.
- `src/online_shoppers/api/` ya expone `/health`, `/v1/model/metadata` y `/v1/predict`, valida el
  payload y verifica el SHA-256 del joblib. El contrato OpenAPI está versionado en
  `contracts/openapi.json`.
- `web/` implementa el mockup de una sola pantalla, consume `/v1/predict` y cubre estados de carga,
  éxito y error. La tasa base 15,5 % está hardcodeada y aún no muestra metadata dinámica ni otros
  patrones descriptivos del dataset.
- `compose.yaml` construye solamente FastAPI. El frontend compila de forma nativa en Vercel y no
  tiene Dockerfile, aunque la descripción general del PDF exige despliegue mediante contenedores.
- Terraform se divide en `bootstrap`, `foundation` y `service`. No hay recursos para MLflow/EC2 ni
  bucket de artefactos MLflow.
- CI valida Python, web, Terraform y sintaxis de Compose. La línea base observada es: 47 pruebas
  Python aprobadas, 4 pruebas web aprobadas, lint/build web aprobados, Ruff y mypy de `src tests`
  aprobados. `ruff check .` falla con 52 hallazgos en notebooks y `uv run mypy` sin rutas falla por
  faltar `src/online_shoppers/py.typed`.
- `docs/evidence/README.md` sólo contiene un checklist: no hay capturas MLflow/EC2 ni del tablero.
- El worktree tiene cuatro copias no versionadas con sufijo ` 2` y contenido idéntico a archivos
  canónicos: `providers 2.tf`, `model_metrics 2.json`, `artifacts 2.py` y `features 2.py`.

### Cobertura técnica de los entregables del PDF

| Entregable técnico | Estado actual | Definición de terminado |
| --- | --- | --- |
| Modelos desarrollados y evaluados | Hay muchos candidatos, pero repartidos entre notebooks y sin protocolo final limpio | Campaña canónica group-aware, métricas CV y test final, champion reproducible y empaquetado |
| Experimentos soportados en MLflow | 80 runs locales ignorados; cero Model Registry | Todos los trials/candidatos de la campaña final en MLflow EC2, artefactos S3 y champion registrado |
| Tablero según maqueta | Predicción funcional; información descriptiva mínima y tasa fija | Predicción API, metadata real, visualizaciones relevantes, estados accesibles y pruebas |
| Fuentes de modelos | Existen, pero helpers avanzados están en notebooks | Features, búsqueda, evaluación, tracking y promoción en módulos `src/` probados |
| Fuentes del tablero | Existen y compilan | Fuentes actualizadas, Dockerfile web y Compose full-stack reproducible |
| Repositorio y aportes | Hay commits de varios autores | Worktree limpio, CI verde y commits sustantivos atribuibles a cada integrante |
| Pantallazos MLflow en EC2 | No existen | Evidencia con usuario/IP EC2, misma IP en MLflow, runs/metrics/artifacts y champion |

## Backend/API Integration

- Mantener `POST /v1/predict` sin cambios incompatibles y seguir sirviendo la inferencia desde el
  `ModelBundle`; cualquier candidato debe implementar `predict_proba` dentro de un pipeline
  serializable.
- Ampliar de forma backward-compatible `GET /v1/model/metadata` con:
  `mlflow_run_id`, `mlflow_experiment`, `feature_set`, `include_page_values`, `baseline_rate`,
  `data_version`, métricas CV y métricas finales. No exponer URI S3, credenciales ni paths internos.
- Actualizar `MetadataResponse`, pruebas de servicio/endpoints y `contracts/openapi.json` en el mismo
  cambio para impedir drift entre API y frontend.
- El frontend seguirá llamando `/v1/predict`; además consultará `/v1/model/metadata` para eliminar
  constantes duplicadas y mostrar qué modelo produjo la decisión.
- No se agrega una base de datos de aplicación ni endpoints de entrenamiento. El entrenamiento se
  ejecuta por CLI/notebook y el artefacto se incorpora a la imagen de inferencia como hoy.

## Data Model And Persistence

- No hay migraciones de datos de negocio.
- Añadir un identificador de grupo determinista calculado con las 17 features para mantener sesiones
  idénticas en la misma partición. El identificador se usa sólo durante entrenamiento y no entra al
  modelo ni a la API.
- Crear un manifiesto versionado del protocolo bajo `reports/experiments/` con seed, hashes de grupos,
  tamaños/proporciones de folds, DVC hash del dataset y hash de configuración; no incluir filas ni
  labels del test.
- Persistir metadata del champion en `models/model_metadata.json` y métricas consolidadas en
  `reports/model_metrics.json`. El binario continúa en `models/champion.joblib` bajo DVC/S3.
- MLflow usará SQLite en un volumen EBS persistente de EC2 para metadata y un bucket S3 privado para
  artifacts. El bucket tendrá cifrado, versionado, bloqueo público, lifecycle y `prevent_destroy`.
- Registrar el modelo final en Model Registry con una versión enlazada al run ganador y alias
  `champion`. El joblib/DVC sigue siendo el artefacto de despliegue de la API; Registry es la fuente de
  trazabilidad y no se consulta durante una inferencia.

## Implementation Tasks

1. [x] Sanear la línea base y fijar criterios de aceptación antes de experimentar.
   - Files: `params.yaml`, `.gitignore`, `pyproject.toml`, `docs/evidence/README.md`
   - Tests first: añadir una prueba de configuración que rechace folds, seeds, métrica primaria o
     presupuesto de búsqueda inválidos.
   - Notes: verificar nuevamente que las cuatro copias con sufijo ` 2` sean idénticas y retirarlas de
     forma segura; no borrar archivos divergentes del usuario. Agregar `src/online_shoppers/py.typed`
     o ajustar el comando general de mypy. Declarar perfiles `smoke` y `full`, seed, holdout, cinco
     folds, primary/secondary metrics, presupuesto de tuning, modelos habilitados y regla de
     promoción. No modificar métricas luego de observar el nuevo test.

2. [x] Implementar particionado reproducible y group-aware para eliminar fuga por duplicados.
   - Files: `src/online_shoppers/data.py`, `src/online_shoppers/modeling.py`,
     `tests/unit/test_data.py`, `tests/unit/test_modeling.py`
   - Tests first: comprobar que grupos con features idénticas nunca cruzan development/test ni folds,
     que las particiones son deterministas, disjuntas, estratificadas y que cada fold contiene ambas
     clases.
   - Notes: usar hash estable de las 17 features como group id. Reservar un nuevo audit holdout antes
     de comparar candidatos y usar `StratifiedGroupKFold` dentro de development. Generar el manifiesto
     del protocolo sin publicar índices/labels que incentiven tuning contra test.

3. [x] Extraer el feature engineering de los notebooks a transformers de producción.
   - Files: `src/online_shoppers/features.py`, `tests/unit/test_features.py`, `params.yaml`
   - Tests first: entradas con ceros, duraciones extremas, categorías desconocidas y variantes sin
     `PageValues` no producen NaN/infinito; el bucketing de categorías raras se aprende sólo con el
     fold de entrenamiento; nombres y orden de columnas son estables después de joblib round-trip.
   - Notes: incluir `total_duration`, `total_pageviews`, duración promedio por página, shares de
     duración, gap bounce/exit, engagement, `log1p` de duraciones y conteos sesgados, indicador de día
     especial, periodo de temporada alta, tráfico agrupado e interacciones justificadas. Mantener
     conjuntos `base_with_page_values`, `base_without_page_values`, `engineered_with_page_values` y
     `engineered_without_page_values`. Nunca usar `Revenue` ni estadísticas globales para crear una
     feature.

4. [x] Crear un catálogo único de candidatos y espacios de búsqueda.
   - Files: `src/online_shoppers/experiments.py`, `src/online_shoppers/modeling.py`, `params.yaml`,
     `tests/unit/test_experiments.py`, `pyproject.toml`, `uv.lock`
   - Tests first: cada candidato se construye desde configuración, respeta seed, ofrece
     `predict_proba`, acepta el feature set indicado y expone parámetros serializables.
   - Notes: conservar Dummy y Logistic Regression como baselines; comparar RandomForest, ExtraTrees,
     HistGradientBoosting, CatBoost, XGBoost y LightGBM. Añadir `MLPClassifier` con escalamiento,
     early stopping, `hidden_layer_sizes`, `alpha`, learning rate y máximo de épocas acotados. Probar
     class weights/`scale_pos_weight` en modelos compatibles. Limitar stacking/blending a finalistas
     para evitar un barrido combinatorio. No usar SMOTE fuera del pipeline ni antes de los folds.

5. [x] Fortalecer la capa MLflow para que ninguna evaluación quede sólo en memoria/JSON.
   - Files: `src/online_shoppers/tracking.py`, `src/online_shoppers/experiments.py`,
     `tests/unit/test_tracking.py`, `tests/integration/test_experiment_tracking.py`, `.env.example`
   - Tests first: campaña padre y runs hijos registran estado, params, métricas por fold, media/std,
     OOF metrics, tags e inputs; un error deja run `FAILED`; al finalizar, el número de configuraciones
     ejecutadas coincide con los runs terminales esperados.
   - Notes: registrar `git_sha`, DVC data hash, config hash, author, source, feature set, modelo,
     versiones de librerías, duración y seed. Usar `mlflow.log_input` para el dataset sin subir el CSV.
     Loggear curvas PR/ROC/calibración, matriz de confusión, tabla por fold, feature schema y resumen
     JSON. Cada trial de tuning debe ser un nested run; cada candidato final registra su modelo y
     signature/input example. Evitar depender de una lista `RUN_LOG` como fuente de verdad: consultar
     MLflow para ranking y reanudación. Soportar SQLite local para tests y URI HTTP remota para la
     campaña; el perfil `full` debe fallar si se exige remoto y recibe un URI local.

6. [x] Implementar el protocolo canónico de selección y promoción.
   - Files: `src/online_shoppers/experiments.py`, `src/online_shoppers/training.py`,
     `src/online_shoppers/promotion.py`, `tests/unit/test_experiments.py`,
     `tests/integration/test_training.py`, `tests/integration/test_model_smoke.py`
   - Tests first: selección por regla configurada y desempate determinista; umbral calculado sólo con
     probabilidades OOF; test se evalúa exactamente una vez después de congelar el ganador; un
     challenger peor no reemplaza el champion; artefacto promovido carga y predice.
   - Notes: hacer búsqueda acotada en development con cinco folds y PR-AUC/F1. Comparar calibración
     sigmoid/isotonic sólo dentro de development y conservarla si reduce Brier/ECE sin degradar más
     del margen configurado las métricas de negocio. Incluir bootstrap CI o variabilidad entre folds
     para no promover por una diferencia irrelevante. Exigir límites de tamaño y latencia. Refit del
     ganador sobre development, consulta única del audit test y escritura atómica de joblib, metadata
     y métricas. Metadata debe contener run/experiment ID, CV mean/std, test, feature set, DVC/config
     hashes y checksum del artefacto.

7. [x] Añadir una CLI reproducible y un notebook canónico de cierre.
   - Files: `src/online_shoppers/cli.py`, `src/online_shoppers/__main__.py`,
     `notebooks/05_model_selection_mlflow.ipynb`, `notebooks/03_model_experiments.ipynb`,
     `notebooks/04_advanced_experiments.ipynb`, `README.md`
   - Tests first: prueba CLI `smoke` con dataset sintético y MLflow temporal; salida distinta de cero
     ante tracking URI inaccesible/config inválida.
   - Notes: el notebook 05 será la entrada canónica y llamará módulos de `src/`; debe mostrar diseño,
     ranking CV, comparación con/sin PageValues, curvas, calibración, coste/umbral, conclusiones y
     enlace/run ID de MLflow. Los notebooks 03/04 quedan marcados como exploración histórica y no
     vuelven a promover ni mirar test. Ejecutar desde CLI permite corridas idénticas sin estado de
     Jupyter y facilita que cada integrante contribuya con runs atribuibles.

8. [x] Provisionar MLflow en EC2 y sus artefactos S3 mediante Terraform.
   - Files: `infra/terraform/foundation/storage.tf`, `infra/terraform/foundation/iam.tf`,
     `infra/terraform/foundation/variables.tf`, `infra/terraform/foundation/outputs.tf`,
     `infra/terraform/mlflow/backend.tf`, `infra/terraform/mlflow/providers.tf`,
     `infra/terraform/mlflow/versions.tf`, `infra/terraform/mlflow/variables.tf`,
     `infra/terraform/mlflow/main.tf`, `infra/terraform/mlflow/iam.tf`,
     `infra/terraform/mlflow/outputs.tf`, `infra/terraform/environments/dev/mlflow.example.tfvars`,
     `infra/terraform/environments/dev/mlflow.example.tfbackend`, `.github/workflows/ci.yml`
   - Tests first: `terraform fmt`, `init -backend=false` y `validate`; revisar con `terraform plan`
     que no destruya buckets/estados existentes y que el role sólo acceda al prefijo MLflow.
   - Notes: crear bucket privado de artifacts, instance profile mínimo, security group restringido al
     CIDR suministrado, EC2 con EBS cifrado y `delete_on_termination = false` o snapshot/documentación
     equivalente. Bootstrap con user-data/systemd y contenedor MLflow fijado por versión; SQLite y
     logs viven en volumen persistente, artifacts en `s3://.../artifacts`. Exponer IP pública e
     instance ID como outputs no sensibles. Aplicar `prevent_destroy` a datos persistentes. Añadir
     health check, rotación de logs y comandos start/stop; no confirmar secretos ni tfstate.

9. [x] Ejecutar la campaña final contra MLflow EC2 y registrar/promover el champion.
   - Files: `reports/experiments/protocol_manifest.json`,
     `reports/experiments/final_model_comparison.json`, `reports/model_metrics.json`,
     `models/model_metadata.json`, `models/champion.joblib.dvc`
   - Tests first: ejecutar primero el perfil `smoke` remoto y verificar desde `MlflowClient` que
     params, métricas, artifacts e inputs se leen; sólo después lanzar `full`.
   - Notes: arrancar EC2, exportar `MLFLOW_TRACKING_URI=http://<ip>:5000`, ejecutar una sola campaña
     canónica y verificar que no existan candidatos en el resumen sin run ID. Registrar el ganador en
     Model Registry y asignar alias `champion`; exportar el mismo modelo a `ModelBundle`, ejecutar
     smoke de API, luego `dvc add models/champion.joblib` y `dvc push`. No copiar manualmente los 80
     runs locales ni fabricar historia: los runs de entrega deben ser ejecuciones reales contra EC2.

10. [x] Enriquecer metadata de inferencia sin romper `/v1/predict`.
    - Files: `src/online_shoppers/api/schemas.py`, `src/online_shoppers/api/service.py`,
      `tests/unit/api/test_schemas.py`, `tests/unit/api/test_service.py`,
      `tests/integration/api/test_endpoints.py`, `contracts/openapi.json`
    - Tests first: metadata nueva se valida, no filtra URIs/paths, el artefacto con features
      engineered predice, un champion sin PageValues mantiene el request de 17 campos y el snapshot
      OpenAPI sólo cambia en los campos añadidos.
    - Notes: obtener todos los valores del metadata firmado del artefacto, no de constantes de código.
      Mantener respuesta anterior compatible. Exponer baseline, feature set, disponibilidad de
      PageValues, run ID y métricas CV/test necesarias para el tablero.

11. [x] Completar el tablero con metadata real del champion y resultado contextualizado.
    - Files: `web/src/lib/schemas.ts`, `web/src/lib/api.ts`, `web/src/app/page.tsx`,
      `web/src/app/styles.css`, `web/src/components/PredictionForm.tsx`,
      `web/src/components/PredictionResult.tsx`, `web/src/components/ModelSummary.tsx`,
      `web/src/components/BusinessInsights.tsx`, `web/src/data/dashboard-insights.json`,
      pruebas bajo `web/src/**/*.test.tsx`
    - Tests first: carga/éxito/error de metadata, predicción accesible, baseline dinámico, render de
      insights, responsive básico y mensajes distintos para validación local, API 422 y servicio 503.
    - Notes: conservar el flujo y los estados del mockup. Añadir tarjetas/gráficas compactas para
      conversión por mes, tipo de visitante y tráfico usando agregados versionados generados por
      `reporting.py`; mostrar F1/PR-AUC, versión/run del champion y advertencia con/sin PageValues.
      Reemplazar códigos poco interpretables por labels/ayudas cuando el dataset permita mapearlos,
      sin inventar semántica para códigos UCI. Usar HTML/CSS/SVG accesible y evitar una dependencia de
      charts si no es necesaria.

12. [x] Desplegar el tablero en Vercel y validar el producto distribuido.
    - Files: `web/src/lib/api.ts`, configuración temporal de Vercel y variables CORS de Terraform.
    - Tests first: build de producción y smoke del flujo navegador → Vercel → API Gateway → Lambda.
    - Notes: el frontend no se ejecuta en EC2 ni Lambda. El preview temporal debe reclamarse en la
      cuenta del equipo para hacerlo persistente; el origen exacto quedó permitido por API Gateway.

13. [x] Elevar pruebas de reproducibilidad al nuevo alcance.
    - Files: `.github/workflows/ci.yml`, `pyproject.toml`, pruebas Python/web y notebooks modificados
    - Tests first: todo cambio funcional comienza con su prueba fallida correspondiente.
    - Notes: lint/format de notebooks canónicos, mypy, pytest con cobertura de módulos de
      experimentación, tests web, build web, Terraform de la nueva raíz MLflow, Compose full-stack y
      un experimento sintético `smoke` con MLflow SQLite. La campaña full, AWS apply y DVC push no se
      ejecutan en PR CI sin credenciales; deben tener comandos manuales documentados y verificadores
      read-only. Resolver los 52 hallazgos Ruff actuales en notebooks tocados.

14. [ ] Recolectar soportes técnicos y cerrar trazabilidad Git de la entrega.
    - Files: `docs/evidence/README.md`, `docs/evidence/e2/.gitkeep` y capturas finales bajo
      `docs/evidence/e2/` si la política del curso permite versionarlas
    - Tests first: checklist automatizable que falle si falta URL/run ID/champion, si la API reporta
      otra versión o si hay archivos esperados no versionados.
    - Notes: capturar una terminal EC2 con usuario (`whoami`), hostname/IP pública e instance ID; en
      la misma toma o secuencia mostrar MLflow servido por esa IP. Capturar lista de runs, comparación
      de parámetros/métricas, artifacts del champion y Model Registry. Capturar tablero generando una
      predicción y mostrando insights. Ejecutar `git shortlog -sne --all` y conservar PRs/commits
      reales por integrante. Revisar que las imágenes no muestren claves, cookies, tokens o datos de
      state. Finalmente detener EC2 con `aws ec2 stop-instances`; no terminarla ni ejecutar destroy.

## Tests And Scenarios

- Unit tests:
  - group ids y folds deterministas/disjuntos con duplicados y targets conflictivos;
  - transformers sin leakage, NaN/infinito y con feature sets con/sin `PageValues`;
  - catálogo de modelos, MLP serializable, métricas, thresholds, calibración y promoción;
  - MLflow nested runs, tags, dataset input, artifacts, estados `FINISHED`/`FAILED` y reanudación;
  - metadata/artifact checksum y compatibilidad API.
- Integration tests:
  - campaña `smoke` sintética registra todos los candidatos esperados en un MLflow temporal;
  - campaña pequeña produce joblib, metadata, resumen y registry version coherentes;
  - joblib promovido carga desde DVC/materializado y atiende `/health`, metadata y predicción;
  - Terraform valida las cuatro raíces y Compose resuelve API + web.
- UI/E2E scenarios:
  - metadata cargando, disponible y caída con fallback explícito;
  - formulario válido produce probabilidad, clase, baseline, threshold, modelo y run;
  - validación local, HTTP 422, timeout y HTTP 503 son distinguibles y recuperables;
  - insights se leen y comprenden en móvil/escritorio, con navegación por teclado y etiquetas;
  - el navegador consume la API configurada, no intenta cargar joblib ni S3.
- Regression scenarios:
  - payload actual de 17 campos y OpenAPI continúan válidos;
  - champion sin `PageValues` acepta el mismo payload;
  - categorías desconocidas no rompen inferencia;
  - hash o schema de artefacto inválido degrada `/health` y no carga pickle no confiable;
  - DVC pointer, metadata, MLflow run y modelo dentro de Docker describen la misma versión.
- Acceptance thresholds:
  - no exigir una mejora artificial sobre el F1 test histórico; el nuevo champion debe superar al
    baseline bajo la regla CV congelada o conservar el modelo más simple;
  - reportar media y desviación por fold de PR-AUC, ROC-AUC, precision, recall, F1 y Brier;
  - cero configuraciones ejecutadas sin run terminal y run ID en el resumen final;
  - una sola evaluación del nuevo audit test por campaña final;
  - p95 de inferencia local y tamaño del artefacto dentro de límites fijados en `params.yaml`.

## Validation Commands

```bash
# Línea base Python
uv sync --all-groups --locked
uv run ruff format --check src tests notebooks/05_model_selection_mlflow.ipynb
uv run ruff check src tests notebooks/05_model_selection_mlflow.ipynb
uv run mypy src tests
uv run pytest -q

# Experimento reproducible local de prueba
uv run python -m online_shoppers experiment --profile smoke \
  --tracking-uri sqlite:////tmp/online-shoppers-smoke-mlflow.db

# Infraestructura MLflow (usar backend/tfvars reales no versionados al desplegar)
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/mlflow init -backend=false
terraform -chdir=infra/terraform/mlflow validate
terraform -chdir=infra/terraform/mlflow plan -var-file=../environments/dev/mlflow.tfvars

# Campaña final remota; MLFLOW_TRACKING_URI debe apuntar a la IP EC2
test -n "$MLFLOW_TRACKING_URI"
uv run python -m online_shoppers experiment --profile full \
  --tracking-uri "$MLFLOW_TRACKING_URI"
uv run python -m online_shoppers verify-experiment \
  --tracking-uri "$MLFLOW_TRACKING_URI" --require-registry-alias champion

# Artefacto y API
uv run dvc status
uv run dvc push models/champion.joblib.dvc
docker compose config
docker compose build
docker compose up -d
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/v1/model/metadata
curl --fail http://localhost:3000

# Frontend
pnpm --dir web lint
pnpm --dir web typecheck
pnpm --dir web test
pnpm --dir web build

# Trazabilidad final
git status --short
git shortlog -sne --all
```

Los comandos AWS/Terraform/DVC remotos requieren credenciales temporales y aprobación normal del
entorno. No deben incorporarse access keys, tfstate ni valores sensibles al repositorio.

## Risks And Rollback

- Risk: los notebooks anteriores ya consultaron el test histórico y sus métricas están sesgadas por
  selección repetida.
  Mitigation: crear un nuevo audit holdout group-aware con seed congelado antes de la nueva campaña y
  prohibir su acceso desde tuning/notebooks.
  Rollback: si el protocolo no puede garantizarse, conservar el champion actual y reportar sólo CV
  para challengers; no afirmar mejora final.
- Risk: duplicados de features pueden inflar métricas si cruzan folds.
  Mitigation: hashes de grupo y assertions de disjunción en todas las particiones.
  Rollback: mantener el modelo anterior mientras se recalculan resultados group-aware.
- Risk: MLP/boosters o ensambles aumentan tiempo, memoria, imagen y cold start sin mejora estable.
  Mitigation: perfiles/budgets acotados, early stopping y criterios de tamaño/latencia.
  Rollback: promover el candidato más simple dentro del margen estadístico, incluso Logistic/HistGB.
- Risk: el feature engineering manual se comporte distinto entre entrenamiento e inferencia.
  Mitigation: transformer dentro del pipeline, tests round-trip y un único schema de features.
  Rollback: volver al pipeline base versionado por DVC.
- Risk: MLflow público sin autenticación exponga metadata o permita escritura.
  Mitigation: security group por CIDR, IAM de instancia mínimo, bucket privado y EC2 detenida fuera de
  las ventanas de trabajo/evidencia.
  Rollback: cerrar ingress/detener EC2; los artifacts permanecen en S3 y EBS.
- Risk: VocLabs termine recursos o invalide IP pública al detener/reiniciar EC2.
  Mitigation: usar Elastic IP sólo si está permitido, documentar instance ID y tomar evidencias antes
  de detener; no depender de la IP para la trazabilidad almacenada.
  Rollback: levantar una nueva instancia desde snapshot/EBS y apuntar al mismo bucket artifact.
- Risk: ampliar metadata rompa frontend o snapshot OpenAPI.
  Mitigation: sólo campos adicionales, schemas compartidos y pruebas de contrato.
  Rollback: servir los campos nuevos como opcionales y desplegar el digest anterior de API/web.
- Risk: actualizar el pointer DVC o imagen despliegue un modelo incorrecto.
  Mitigation: comparar checksum, run ID, DVC hash y metadata antes de build/deploy.
  Rollback: volver al commit/pointer DVC y digest ECR anterior; nunca sobrescribir tags inmutables.

## Handoff Notes

- Implementar en una rama nueva desde `main` y preservar cambios ajenos. Las copias no versionadas
  con sufijo ` 2` son idénticas en la inspección actual, pero deben verificarse de nuevo antes de
  retirarlas.
- Empezar cada tarea funcional por sus pruebas. No lanzar la campaña `full` ni tocar el nuevo test
  hasta que particionado, tracking, serialización y perfil `smoke` estén verdes.
- `notebooks/05_model_selection_mlflow.ipynb` es la única narrativa canónica nueva. La lógica debe
  vivir en `src/`; no volver a copiar helpers grandes entre notebooks.
- Cada experimento significa una ejecución real registrada. No crear runs manuales para rellenar
  evidencia, no importar el SQLite local como si hubiera corrido en EC2 y no editar métricas.
- Cada integrante debe reclamar un work package y hacer commits propios con autoría correcta. Los
  merge commits no sustituyen evidencia de implementación sustantiva.
- La entrega técnica queda lista cuando: CI está verde, el worktree no tiene copias accidentales, el
  champion registrado coincide con joblib/DVC/API, el tablero funciona en Compose, los runs están
  visibles por la IP EC2 y las capturas requeridas existen sin secretos.
- Tras recopilar evidencias, detener la instancia MLflow y comprobar estado `stopped`. No ejecutar
  `terraform destroy`, no terminar EC2 y no eliminar su EBS/bucket hasta recibir autorización del
  curso.
