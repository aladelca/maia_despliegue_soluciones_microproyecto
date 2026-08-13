# Online Shoppers Purchasing Intention: plan de implementación

## Goal

- Construir un prototipo funcional que estime la probabilidad de que una sesión de comercio electrónico termine en compra.
- Cumplir el enunciado del microproyecto: modelos supervisados empaquetados, API de inferencia, tablero que consuma la API, visualizaciones relevantes y despliegue con Docker.
- Versionar el dataset y el modelo con DVC sobre Amazon S3.
- Crear todos los recursos AWS con Terraform.
- Desplegar FastAPI como imagen de contenedor en AWS Lambda, publicada en Amazon ECR y expuesta por API Gateway; desplegar el tablero Next.js en Vercel.

## Request Snapshot

- User request: revisar maia_pds_proy_s2.pdf y maia_pds_proy.pdf, identificar requisitos de código, proponer arquitectura AWS con DVC/S3, FastAPI, Terraform y frontend mínimo en Vercel, crear el plan e implementarlo localmente.
- Owner or issue: None
- Plan file: plans/20260812-2220-online-shoppers-ml-product.md
- Fecha de referencia: 2026-08-12

## Current State

- El repositorio no tiene commits ni código; contiene maia_pds_proy_s2.pdf y maia_pds_proy.pdf como documentos locales ignorados por Git.
- No existen pyproject.toml, package.json, configuración DVC, notebooks, tests, Dockerfiles, CI/CD ni Terraform.
- La rama actual es main y el remoto configurado ya no está disponible; antes de colaborar se debe crear o corregir el repositorio remoto.
- El alcance inmediato y el alcance final no son iguales:
  - Entrega 1, al final de semana 3: problema y contexto, pregunta de negocio, alcance, dataset, repositorio Git, repositorio DVC, exploración, mockup, reporte y evidencias.
  - Producto final: modelos supervisados empaquetados, API de inferencia, tablero que use la API y despliegue mediante contenedores Docker.

## Inspected Evidence

- maia_pds_proy_s2.pdf: enunciado local de tres páginas.
- maia_pds_proy.pdf: enunciado completo de cinco páginas con cronograma de ocho semanas y requisitos de las tres entregas.
- UCI Online Shoppers Purchasing Intention Dataset: 12,330 sesiones, 17 variables predictoras, Revenue como etiqueta y 15.5% de sesiones positivas.
- Archivo oficial online_shoppers_intention.csv: 18 columnas incluyendo la etiqueta.
- Documentación de DVC para remotos Amazon S3.
- Documentación vigente de AWS Lambda, ECR, API Gateway, ECS Express Mode y del cambio de disponibilidad de App Runner.
- Documentación vigente de Terraform para backend S3 con bloqueo nativo.
- Documentación de Vercel para despliegue de Dockerfiles, publicada el 2026-06-30.

## Business Definition

### Problema

Una tienda en línea recibe muchas sesiones que no terminan en compra. Se necesita identificar sesiones con mayor propensión de conversión para priorizar intervenciones comerciales o de experiencia.

### Pregunta de negocio recomendada

¿Cuál es la probabilidad de que una sesión de navegación termine generando ingresos, dadas las señales observadas de navegación, contexto, visitante y adquisición?

### Usuario del prototipo

- Analista de comercio electrónico o marketing digital.
- Necesita explorar patrones de conversión, evaluar una sesión y entender qué variables influyen en la predicción.

### Decisión soportada

- Priorizar sesiones con alta probabilidad para acciones definidas por el negocio.
- El modelo es predictivo, no causal: no demuestra que una promoción o intervención produzca una compra.

### Limitación crítica

- Cada fila contiene agregados de una sesión. El dataset no tiene eventos con timestamps internos, ID de usuario, valor monetario de la compra ni historial longitudinal.
- Se debe definir la predicción como una fotografía de la sesión con los valores disponibles al momento de evaluación; no afirmar que el prototipo valida inferencia en tiempo real.
- PageValues está fuertemente relacionado con la transacción y puede no estar disponible en todos los momentos operativos. El notebook debe comparar un modelo con todas las variables contra un modelo operativo sin PageValues y documentar el riesgo de fuga o disponibilidad.

## Dataset Contract

### Fuente y licencia

- Fuente: UCI Machine Learning Repository, dataset 468.
- Archivo: online_shoppers_intention.csv, aproximadamente 1 MB.
- Licencia: CC BY 4.0; incluir atribución a Sakar y Kastro y el DOI 10.24432/C5F88Q.
- Filas esperadas en la versión inicial: 12,330.
- Clase positiva Revenue=True: 1,908; clase negativa: 10,422.

### Features

| Grupo | Variables |
| --- | --- |
| Conteos | Administrative, Informational, ProductRelated |
| Duraciones | Administrative_Duration, Informational_Duration, ProductRelated_Duration |
| Métricas de navegación | BounceRates, ExitRates, PageValues, SpecialDay |
| Contexto temporal | Month, Weekend |
| Categóricas codificadas | OperatingSystems, Browser, Region, TrafficType |
| Visitante | VisitorType |
| Target | Revenue |

### Reglas mínimas de validación

- Exigir exactamente las 18 columnas en datos de entrenamiento y 17 features en inferencia.
- Revenue y Weekend deben normalizarse a booleanos.
- Conteos y duraciones no pueden ser negativos.
- BounceRates, ExitRates y SpecialDay deben estar entre 0 y 1.
- Month y VisitorType deben pertenecer a categorías conocidas en entrenamiento; el pipeline debe manejar categorías nuevas sin romper inferencia.
- Fallar con un mensaje accionable si faltan columnas, hay duplicados exactos inesperados, tipos inválidos o target con una sola clase.
- Registrar distribución de clases y cualquier desviación respecto de las 12,330 filas originales.

## Requirements Extracted from the PDF

### Requisitos obligatorios de código para la Entrega 1

1. Crear y usar un repositorio Git con commits atribuibles a cada integrante.
2. Inicializar DVC y configurar un repositorio remoto; en este proyecto será S3.
3. Descargar y versionar el dataset, conservando en Git solo el archivo .dvc y en S3 el contenido.
4. Crear un notebook reproducible de exploración:
   - dimensiones, tipos y calidad;
   - distribución de Revenue;
   - distribuciones numéricas;
   - conversión por Month, VisitorType, Weekend y TrafficType;
   - relaciones entre BounceRates, ExitRates, PageValues y Revenue;
   - conclusiones conectadas con la pregunta de negocio.
5. Crear el mockup del tablero con sus vistas y flujo de predicción.
6. Documentar comandos, enlaces y capturas que demuestren Git, DVC y S3.

### Requisitos de código para el prototipo final

1. Entrenar y comparar más de un modelo supervisado.
2. Empaquetar preprocesamiento y modelo como una sola unidad serializada.
3. Servir inferencias mediante una API FastAPI con validación estricta.
4. Crear un tablero Next.js que consuma la API, no que cargue el pickle.
5. Mostrar visualizaciones descriptivas y métricas predictivas en los notebooks/reporte; en la aplicación basta una visualización mínima del resultado frente a la tasa base.
6. Containerizar API y frontend.
7. Desplegar la API y el modelo en AWS y el frontend en Vercel.
8. Automatizar infraestructura AWS con Terraform.
9. Incluir pruebas, documentación y soportes de despliegue.

### Cronograma mínimo del enunciado completo

| Semana | Resultado técnico mínimo |
| --- | --- |
| 1 | Equipo, alternativas de problema, pregunta de negocio, disponibilidad de datos y documentación |
| 2 | Problema y alcance definidos, enfoque descriptivo/predictivo y mockup inicial |
| 3 | Git y DVC establecidos, EDA versionada, mockup iterado y documentación |
| 4 | Primeras versiones de modelos, experimentos registrados en MLflow y avance del tablero |
| 5 | Nuevas versiones, comparación/selección con MLflow y tablero desarrollado |
| 6 | Nuevos experimentos, modelo empaquetado, primera API y tablero desplegados |
| 7 | Nueva versión integrada y desplegada de modelo, API y tablero |
| 8 | Versión final empaquetada/desplegada, documentación y entregables finales |

### Entrega 2 — fin de semana 5

- Reporte y soportes de modelos desarrollados.
- Experimentos y resultados registrados en MLflow.
- Pantalla de predicción implementada según el mockup.
- Repositorio Git con contribuciones visibles de todos los integrantes.
- Reporte de trabajo en equipo.

### Entrega 3 — inicio de semana 8

- Repositorio Git con modelos, pipelines de entrenamiento/procesamiento, frontend y artefactos de empaquetado/despliegue.
- Datos versionados en DVC.
- Modelos y experimentos soportados en MLflow.
- Modelo empaquetado y desplegado mediante API.
- Artefactos Docker para frontend, API y modelo.
- Manual de usuario y manual de instalación.
- Reporte de trabajo en equipo.
- Video público de síntesis, relevancia, modelos, solución, resultados y conclusiones, con duración máxima de 10 minutos.
- Cada reporte debe tener máximo 10 páginas y debe incluir soportes; la contribución individual se evidencia con commits, reporte de equipo y sustentación.

## Architecture Decision

### Arquitectura recomendada: Lambda + API Gateway + Vercel

    GitHub
      |-- CI Python: Ruff, mypy, pytest
      |-- dvc pull del modelo exacto desde S3
      |-- docker build de API y push por digest
      v
    Amazon ECR  --->  AWS Lambda (FastAPI + Mangum + modelo incluido)
                               |
                        API Gateway HTTP API
                               |
                         HTTPS /v1/predict
                               |
                    Next.js container en Vercel

    Notebook de entrenamiento
      |-- dataset y modelo versionados con DVC
      v
    Amazon S3 privado

    Terraform
      |-- bucket DVC
      |-- bucket de estado
      |-- ECR
      |-- IAM/OIDC
      |-- Lambda
      |-- API Gateway
      |-- CloudWatch
      v
    AWS

### Por qué esta opción

- El modelo tabular será pequeño y la carga esperada es esporádica; Lambda evita mantener un servidor encendido.
- Lambda acepta imágenes de contenedor y ECR es el registro correcto para almacenarlas.
- El modelo se incorpora a una imagen inmutable después de dvc pull. La inferencia no depende de descargar S3 ni de ejecutar DVC en cada arranque.
- API Gateway ofrece una URL HTTPS, CORS y logs de acceso.
- Vercel encaja con Next.js y permite previews; en 2026 también admite despliegue desde Dockerfile.
- Terraform deja reproducibles los objetos AWS y sus políticas.

### Alternativas

| Opción | Ventajas | Desventajas | Decisión |
| --- | --- | --- | --- |
| Lambda + API Gateway | Bajo costo para demo, escala a cero, imagen en ECR | Cold start y adaptación ASGI con Mangum | Recomendada |
| ECS Express Mode/Fargate | Contenedor HTTP convencional, HTTPS, ALB, auto scaling y observabilidad gestionados | Mantiene al menos una tarea y un ALB; mayor costo base | Plan B si la latencia de Lambda resulta inaceptable |
| EC2 + Docker Compose | Fácil de visualizar y control total | Parches, servidor, TLS, seguridad, disponibilidad y costo fijo | No recomendada |
| Todo en Vercel | Menor complejidad de despliegue | Reduce la demostración de arquitectura AWS y separa el cómputo del stack solicitado | Alternativa, no base |
| App Runner | Experiencia sencilla | Cerrado a nuevos clientes; AWS recomienda ECS Express Mode | Descartada |

### Decisiones resueltas

- API: FastAPI.
- Frontend: Next.js + TypeScript, no Streamlit.
- Interfaz: una sola pantalla de predicción; no habrá dashboard multipágina.
- Gestión de AWS: Terraform.
- DVC remote: S3 privado.
- Registro de imágenes: ECR, no EC2 ni Lambda.
- Runtime de inferencia: Lambda con imagen.
- Entrenamiento: ejecución bajo demanda desde notebook.
- Serialización: joblib, que internamente usa pickle; solo se cargan artefactos producidos por el equipo.
- Despliegue frontend: Vercel mediante Dockerfile.

## Scope

### In scope

- EDA y entrenamiento reproducible desde notebooks.
- Funciones Python reutilizables llamadas por los notebooks para evitar lógica crítica escondida en celdas.
- DummyClassifier como baseline, LogisticRegression y RandomForest como candidatos mínimos.
- Split estratificado train/validation/test con semilla fija.
- Selección por PR-AUC; reportar además ROC-AUC, precision, recall, F1, matriz de confusión, Brier score y curva de calibración.
- Selección y documentación del umbral de clasificación.
- Comparación con/sin PageValues.
- Artefacto único con ColumnTransformer, codificación y clasificador.
- Versionado DVC de datos y modelo sobre S3.
- Registro local reproducible de parámetros, métricas y artefactos de cada experimento con MLflow.
- FastAPI, Lambda, API Gateway, ECR, CloudWatch e IAM.
- Pantalla única Next.js con formulario, probabilidad predicha, decisión, umbral y comparación contra la tasa base de conversión.
- Docker local y de despliegue.
- CI/CD con GitHub Actions y autenticación OIDC a AWS.
- Terraform separado en bootstrap, foundation y service para resolver dependencias.

### Out of scope

- Entrenamiento en Lambda, SageMaker, EC2 o un job programado.
- Retraining automático, feature store, servidor MLflow administrado, base de datos de producto y streaming.
- Autenticación de usuarios finales en la primera versión.
- Predicción causal, recomendación personalizada o estimación de valor monetario.
- Batch scoring por CSV en la primera versión.
- Multi-región, alta disponibilidad empresarial y Kubernetes.
- Uso de Streamlit.
- Páginas separadas de EDA, desempeño, administración o navegación compleja en el frontend.

## API Contract

### Endpoints

| Method | Path | Contract |
| --- | --- | --- |
| GET | /health | 200 con status y version; no datos sensibles |
| GET | /v1/model/metadata | Nombre, versión, DVC/Git revision, fecha, features y métricas públicas |
| POST | /v1/predict | Recibe una SessionFeatures y retorna probabilidad, clase, umbral y model_version |

### Request

- Los nombres deben coincidir con las 17 features de UCI.
- Pydantic debe rechazar campos faltantes, extras, NaN, infinito, conteos negativos y tasas fuera de rango con 422.
- Las variables categóricas numéricas se reciben como enteros positivos; categorías no vistas deben ser tratadas por el pipeline con handle_unknown.
- No registrar payloads completos de usuarios; solo request ID, latencia, código y versión del modelo.

### Response

    {
      "will_purchase": true,
      "purchase_probability": 0.73,
      "threshold": 0.42,
      "model_version": "git-sha-or-semver"
    }

### Errors

- 422 para entrada inválida.
- 503 si el artefacto no puede cargarse al iniciar.
- 500 genérico para error no controlado, sin stack trace o secretos en la respuesta.
- API Gateway limita tamaño y tasa; no se implementa endpoint batch inicialmente.

## Model Artifact Contract

- models/champion.joblib contiene un objeto serializado con:
  - pipeline completo de preprocesamiento y clasificación;
  - lista y orden de features;
  - umbral elegido;
  - versión de esquema.
- models/model_metadata.json contiene:
  - commit Git y hash SHA-256 del joblib;
  - hash DVC o referencia del artefacto;
  - versión de dataset;
  - fecha UTC;
  - métricas train/validation/test;
  - modelo ganador y parámetros;
  - presencia o exclusión de PageValues;
  - versiones de Python, scikit-learn y joblib.
- La API verifica esquema, features y hash al arrancar.
- Nunca aceptar o cargar pickles enviados por clientes. Los pickles permiten ejecución de código si la fuente no es confiable.
- El joblib y su archivo .dvc se generan una vez desde notebooks/02_model_training.ipynb y se publican con dvc push.
- CI ejecuta dvc pull antes del docker build y copia el artefacto dentro de la imagen. Lambda no necesita permisos de lectura al bucket DVC.

## File Plan

### Raíz, Python y DVC

| Path | Action | Details |
| --- | --- | --- |
| README.md | create | Problema, arquitectura, setup, DVC, entrenamiento, pruebas, Docker, Terraform, despliegue y evidencias |
| pyproject.toml | create | Python 3.12; dependencias runtime, grupos ml/dev; configuración Ruff, mypy y pytest |
| uv.lock | create | Lock reproducible generado por uv |
| .gitignore | create | Ignorar datos/modelos materializados, .dvc/config.local, .env, Terraform local y caches |
| .dockerignore | create | Excluir notebooks, datos, credenciales, Terraform, Git y caches salvo modelo requerido |
| .env.example | create | API_BASE_URL y variables no secretas; sin credenciales AWS |
| params.yaml | create | Seed, split, modelos, grids mínimos y criterios de umbral |
| .dvc/config | create | Remote default aws-s3 con URL del bucket/prefijo producido por Terraform |
| .dvcignore | create | Excluir temporales y outputs no versionables |
| data/raw/online_shoppers_intention.csv.dvc | create | Puntero DVC al CSV oficial en S3 |
| models/champion.joblib.dvc | create | Puntero DVC al pipeline ganador |
| models/model_metadata.json | create | Contrato pequeño del artefacto, auditable en Git |
| reports/eda_summary.json | create | Agregados reproducibles para soportar el reporte, sin dataset completo |
| reports/model_metrics.json | create | Métricas del champion y baseline |
| reports/figures/.gitkeep | create | Directorio para figuras seleccionadas del reporte |

### Notebooks y módulos ML

| Path | Action | Details |
| --- | --- | --- |
| notebooks/01_eda.ipynb | create | Carga local tras dvc pull, validación, visualizaciones y conclusiones de negocio |
| notebooks/02_model_training.ipynb | create | Split, comparación, calibración, umbral, evaluación final y export joblib/metadata |
| src/online_shoppers/__init__.py | create | Paquete y versión |
| src/online_shoppers/data.py | create | Carga, normalización booleana y validación del contrato tabular |
| src/online_shoppers/features.py | create | Listas de features y construcción del ColumnTransformer |
| src/online_shoppers/modeling.py | create | Pipelines candidatos, métricas, selección de umbral y evaluación |
| src/online_shoppers/artifacts.py | create | Escritura/carga segura del bundle propio, metadata y verificación SHA-256 |
| src/online_shoppers/reporting.py | create | Generación de eda_summary.json, model_metrics.json y figuras |
| src/online_shoppers/tracking.py | create | Abstracción mínima para registrar runs, parámetros, métricas y artefactos en MLflow local |

### FastAPI

| Path | Action | Details |
| --- | --- | --- |
| src/online_shoppers/api/__init__.py | create | Paquete API |
| src/online_shoppers/api/main.py | create | Instancia FastAPI, lifespan, rutas, handlers y CORS |
| src/online_shoppers/api/schemas.py | create | SessionFeatures, PredictionResponse, MetadataResponse y validadores Pydantic |
| src/online_shoppers/api/service.py | create | Carga única del modelo y predict_proba con orden de columnas garantizado |
| src/online_shoppers/api/lambda_handler.py | create | Adaptador Mangum handler para API Gateway payload v2 |
| docker/api.Dockerfile | create | Build multi-stage sobre imagen AWS Lambda Python 3.12, dependencias runtime y modelo |

### Pantalla de predicción Next.js

| Path | Action | Details |
| --- | --- | --- |
| web/package.json | create | Next.js, React, cliente HTTP y Zod; sin librería de dashboard innecesaria |
| web/pnpm-lock.yaml | create | Dependencias frontend bloqueadas |
| web/tsconfig.json | create | TypeScript estricto |
| web/next.config.ts | create | Build standalone y configuración segura |
| web/Dockerfile.vercel | create | Imagen multi-stage que escucha PORT y ejecuta Next.js standalone |
| web/src/app/layout.tsx | create | Layout, metadata y estilos |
| web/src/app/page.tsx | create | Única pantalla: encabezado breve, formulario, resultado y nota de alcance |
| web/src/components/PredictionForm.tsx | create | Formulario accesible, defaults y errores |
| web/src/components/PredictionResult.tsx | create | Clase, porcentaje, umbral y barra CSS comparada con la tasa base de 15.5% |
| web/src/lib/api.ts | create | Cliente tipado a FastAPI con timeout y errores |
| web/src/lib/schemas.ts | create | Esquemas Zod alineados con OpenAPI |
| web/.env.example | create | NEXT_PUBLIC_API_BASE_URL |

### Docker local

| Path | Action | Details |
| --- | --- | --- |
| docker/api.local.Dockerfile | create | Imagen HTTP local con Uvicorn para probar FastAPI sin emulador Lambda |
| compose.yaml | create | API local y frontend, healthchecks, puertos y variables |

### Terraform

| Path | Action | Details |
| --- | --- | --- |
| infra/terraform/bootstrap/versions.tf | create | Versiones mínimas Terraform y AWS provider |
| infra/terraform/bootstrap/providers.tf | create | Provider AWS, región y tags |
| infra/terraform/bootstrap/variables.tf | create | Región, project_name y account/environment |
| infra/terraform/bootstrap/main.tf | create | Bucket de estado cifrado, versionado y privado |
| infra/terraform/bootstrap/outputs.tf | create | Nombre del bucket para backend parcial |
| infra/terraform/foundation/backend.tf | create | Backend S3 con key propia y use_lockfile=true |
| infra/terraform/foundation/versions.tf | create | Restricciones de versiones |
| infra/terraform/foundation/providers.tf | create | AWS provider y default_tags |
| infra/terraform/foundation/variables.tf | create | Bucket DVC, ECR, GitHub owner/repo y entorno |
| infra/terraform/foundation/storage.tf | create | Bucket DVC: versionado, cifrado, bloqueo público y lifecycle |
| infra/terraform/foundation/ecr.tf | create | Repositorio privado, scan_on_push, tags inmutables y lifecycle |
| infra/terraform/foundation/github_oidc.tf | create | Provider OIDC y rol CI limitado al repo/branch |
| infra/terraform/foundation/outputs.tf | create | URL ECR, bucket DVC y ARN del rol CI |
| infra/terraform/service/backend.tf | create | Estado S3 separado con use_lockfile=true |
| infra/terraform/service/versions.tf | create | Restricciones Terraform/provider |
| infra/terraform/service/providers.tf | create | AWS provider y tags |
| infra/terraform/service/variables.tf | create | Image URI por digest, memory, timeout, CORS origin y log retention |
| infra/terraform/service/iam.tf | create | Rol runtime mínimo: logs; sin acceso DVC |
| infra/terraform/service/lambda.tf | create | Lambda package_type Image, arquitectura, límites y env vars |
| infra/terraform/service/api_gateway.tf | create | HTTP API, integración Lambda payload 2.0, stage, CORS e invoke permission |
| infra/terraform/service/observability.tf | create | Log groups, retención, métricas y alarmas 5XX/error |
| infra/terraform/service/outputs.tf | create | Base URL y nombre/ARN de función |
| infra/terraform/environments/dev/*.example.tfbackend | create | Ejemplos sin secretos para claves de foundation/service |
| infra/terraform/environments/dev/*.example.tfvars | create | Valores de ejemplo; nombres globales quedan fuera de Git real |

### CI/CD, contracts y evidencia

| Path | Action | Details |
| --- | --- | --- |
| .github/workflows/ci.yml | create | Python format/lint/types/tests, frontend lint/types/tests, Docker build y Terraform fmt/validate |
| .github/workflows/deploy-api.yml | create | OIDC, dvc pull, buildx Lambda, push ECR por SHA/digest y Terraform service apply |
| contracts/openapi.json | create | Snapshot generado por FastAPI para documentar y probar el contrato |
| docs/architecture.md | create | Diagrama, decisiones, seguridad, costos y alternativas |
| docs/dvc-s3.md | create | Bootstrap, dvc remote add, dvc add/push/pull y credenciales por perfil/OIDC |
| docs/deployment.md | create | Orden bootstrap/foundation/image/service/Vercel y rollback |
| docs/mockup.md | create | Wireframe de una sola pantalla de predicción y sus estados vacío/loading/success/error |
| docs/user-guide.md | create | Manual de usuario de la pantalla y explicación del resultado |
| docs/installation-guide.md | create | Manual reproducible de instalación local, DVC, MLflow, Docker y despliegue |
| docs/video-outline.md | create | Guion de menos de 10 minutos para problema, modelos, demo, resultados y conclusiones |
| docs/evidence/README.md | create | Checklist de capturas y enlaces de Git, DVC, S3, ECR, Lambda, API y Vercel |

## Data and Contract Changes

- Nuevo contrato CSV con 18 columnas y target Revenue.
- Nuevo contrato API versionado bajo /v1.
- Nuevas variables:
  - NEXT_PUBLIC_API_BASE_URL para frontend.
  - MODEL_PATH y MODEL_METADATA_PATH con defaults internos al contenedor.
  - ALLOWED_ORIGIN para CORS.
  - MLFLOW_TRACKING_URI con default local file:./mlruns.
- No almacenar AWS_ACCESS_KEY_ID ni AWS_SECRET_ACCESS_KEY en archivos, Terraform, DVC o GitHub.
- Usar AWS profile/SSO local y GitHub OIDC en CI.
- Buckets y ECR privados; acceso por mínimo privilegio.
- Terraform recibe image_uri por digest, no latest, para que el despliegue sea reproducible.

## Implementation Steps

### Phase 0 — Repositorio y decisiones

1. Crear el repositorio remoto y realizar un commit inicial atribuible.
2. Añadir README, licencia/atribución del dataset, pyproject, lockfiles e ignores.
3. Documentar la pregunta de negocio, scoring moment, audiencia, métrica primaria y limitaciones.

### Phase 1 — Terraform bootstrap, DVC y Entrega 1

1. Implementar infra/terraform/bootstrap y crear el bucket de estado con Terraform local.
2. Migrar foundation y service a backend S3 con use_lockfile; no usar DynamoDB porque el locking de DynamoDB está deprecado.
3. Aplicar foundation para crear bucket DVC, ECR y rol GitHub OIDC.
4. Ejecutar dvc init y:

       uv run dvc remote add -d aws-s3 s3://<bucket-dvc>/online-shoppers
       uv run dvc add data/raw/online_shoppers_intention.csv
       uv run dvc push

5. Crear 01_eda.ipynb y reports/eda_summary.json.
6. Crear mockup en docs/mockup.md antes de implementar el frontend.
7. Guardar evidencias: historial de commits, .dvc/config sin secretos, bucket/prefijo S3, dvc push/pull y notebook ejecutado.

### Phase 2 — Entrenamiento único desde notebook

1. Implementar data.py, features.py, modeling.py, artifacts.py y sus tests.
2. En 02_model_training.ipynb:
   - cargar el CSV materializado por dvc pull;
   - fijar seed;
   - separar test estratificado antes de explorar hiperparámetros;
   - ajustar transformadores únicamente con train;
   - comparar Dummy, LogisticRegression y RandomForest;
   - registrar cada candidato y cada variante con/sin PageValues como run de MLflow;
   - manejar desbalance con class_weight antes de considerar resampling;
   - elegir champion con validation PR-AUC y criterios de negocio;
   - evaluar test una sola vez;
   - comparar versión completa y sin PageValues;
   - calibrar probabilidades si la curva/Brier lo justifican;
   - elegir umbral y documentarlo;
   - exportar pipeline, metadata, métricas y agregados.
   - registrar el champion y sus artefactos finales en MLflow.
3. Publicar el modelo:

       uv run dvc add models/champion.joblib
       uv run dvc push
       git add models/champion.joblib.dvc models/model_metadata.json

4. Probar una restauración limpia con git clone equivalente + dvc pull.

### Phase 3 — API FastAPI

1. Definir esquemas Pydantic y OpenAPI antes de la implementación del servicio.
2. Implementar carga única en lifespan/cold start y validación del hash del modelo.
3. Implementar health, metadata y predict.
4. Probar entradas válidas, límites, categorías nuevas, campos extra/faltantes y fallo de artefacto.
5. Generar contracts/openapi.json y verificarlo en CI.
6. Construir imagen local Uvicorn y Lambda; hacer smoke test de ambas.

### Phase 4 — Infraestructura y despliegue API

1. Ejecutar foundation primero para obtener ECR y DVC.
2. CI hace dvc pull del champion, construye para linux/amd64 con provenance deshabilitada y publica tag de commit.
3. Resolver y pasar a Terraform el digest sha256 de ECR.
4. Aplicar service para Lambda, API Gateway, IAM y CloudWatch.
5. Ejecutar smoke test HTTPS contra /health, /v1/model/metadata y /v1/predict.
6. Configurar CORS inicialmente para el dominio preview durante pruebas y restringirlo al dominio de producción al cerrar.

### Phase 5 — Pantalla única Next.js y Vercel

1. Implementar una única ruta / con formulario y cliente tipado en estados vacío, loading, success y error.
2. Mostrar clase predicha, porcentaje, umbral y una barra CSS que compare la probabilidad con la tasa base; no añadir gráficas ni navegación adicional.
3. Añadir una nota corta aclarando que el resultado es predictivo y no causal.
4. Construir y probar web/Dockerfile.vercel localmente.
5. Desplegar en Vercel y configurar NEXT_PUBLIC_API_BASE_URL.
6. Actualizar CORS de API Gateway mediante Terraform con el dominio final.

### Phase 6 — Integración, reporte y soportes

1. Probar el flujo browser -> Vercel -> API Gateway -> Lambda -> respuesta.
2. Ejecutar validaciones completas.
3. Capturar pruebas de Git, DVC/S3, Terraform plan/apply, ECR, Lambda, API Gateway, logs y Vercel.
4. Mantener el reporte principal dentro de 10 páginas y el reporte de equipo dentro de 1 página.
5. Mostrar contribución individual mediante commits y asignación de tareas.
6. Completar manual de usuario, manual de instalación y guion del video final de máximo 10 minutos.

## Implementation Status

- [ ] Phase 0 — Repositorio, configuración y decisiones documentadas.
- [ ] Phase 1 — Terraform local, DVC, dataset, EDA y mockup.
- [ ] Phase 2 — Modelado, MLflow, artefacto champion y métricas.
- [ ] Phase 3 — FastAPI, contrato OpenAPI y contenedores API.
- [ ] Phase 4 — Terraform de foundation/service y automatización de despliegue, sin aplicar recursos externos.
- [ ] Phase 5 — Pantalla única Next.js, pruebas y contenedor Vercel.
- [ ] Phase 6 — Integración local, documentación, manuales, evidencias y validación completa.

## Tests

### Python unit

- tests/unit/test_data.py:
  - schema correcto;
  - normalización de TRUE/FALSE;
  - columnas faltantes/extra;
  - rangos, nulos y target inválido.
- tests/unit/test_features.py:
  - salida con orden estable;
  - fit solo sobre train;
  - categoría desconocida no rompe inferencia.
- tests/unit/test_modeling.py:
  - métricas para datos sintéticos;
  - umbral determinista;
  - baseline y selección del champion.
- tests/unit/test_artifacts.py:
  - round trip del artefacto propio;
  - hash válido/inválido;
  - versión de esquema incompatible.
- tests/unit/test_tracking.py:
  - creación de runs en un tracking URI temporal;
  - parámetros, métricas y artefactos esperados;
  - cierre del run incluso ante error controlado.
- tests/unit/api/test_schemas.py:
  - payload válido;
  - negativos, tasas fuera de rango, NaN/inf, faltantes y extras.
- tests/unit/api/test_service.py:
  - orden de features;
  - probability y threshold;
  - error controlado si falta modelo.

### API integration

- tests/integration/api/test_endpoints.py con TestClient:
  - 200 en health y metadata;
  - 200 y contrato exacto en predict;
  - 422 para entrada inválida;
  - no filtrar stack trace ni paths.
- tests/integration/api/test_lambda_handler.py:
  - evento API Gateway HTTP API payload 2.0;
  - CORS y status mapping.
- tests/integration/test_model_smoke.py:
  - cargar el joblib real tras dvc pull;
  - inferir varias filas y verificar probabilidades en [0,1].

### Frontend

- web/src/**/*.test.tsx con Vitest/Testing Library:
  - validación del formulario;
  - loading/error/success;
  - render de clase, probabilidad, umbral y comparación con tasa base.
- web/e2e/prediction.spec.ts con Playwright:
  - API mock para CI;
  - smoke opcional contra URL desplegada.
- Verificar navegación por teclado, labels, contraste y mensajes de error.

### Infrastructure

- terraform fmt -check -recursive.
- terraform validate para bootstrap, foundation y service.
- tflint sobre cada root.
- terraform plan sin cambios inesperados tras apply.
- Verificar políticas IAM con mínimo privilegio, buckets sin acceso público y CORS restringido.

### Docker and deployment

- Build de docker/api.local.Dockerfile.
- Build de docker/api.Dockerfile para linux/amd64 con --provenance=false.
- Build de web/Dockerfile.vercel.
- docker compose config y smoke de health/predict.
- Smoke HTTPS posterior al despliegue.

## Validation Commands

Desde la raíz:

    uv sync --all-groups
    uv run ruff format --check src tests
    uv run ruff check src tests
    uv run mypy src tests
    uv run pytest -q

    uv run dvc status
    uv run dvc pull
    uv run mlflow experiments search

    corepack enable
    pnpm --dir web install --frozen-lockfile
    pnpm --dir web lint
    pnpm --dir web typecheck
    pnpm --dir web test
    pnpm --dir web build

    terraform -chdir=infra/terraform/bootstrap fmt -check
    terraform -chdir=infra/terraform/bootstrap init -backend=false
    terraform -chdir=infra/terraform/bootstrap validate
    terraform -chdir=infra/terraform/foundation fmt -check
    terraform -chdir=infra/terraform/foundation init -backend=false
    terraform -chdir=infra/terraform/foundation validate
    terraform -chdir=infra/terraform/service fmt -check
    terraform -chdir=infra/terraform/service init -backend=false
    terraform -chdir=infra/terraform/service validate
    tflint --chdir=infra/terraform/bootstrap
    tflint --chdir=infra/terraform/foundation
    tflint --chdir=infra/terraform/service

    docker build -f docker/api.local.Dockerfile -t shoppers-api:local .
    docker buildx build --platform linux/amd64 --provenance=false -f docker/api.Dockerfile -t shoppers-api:lambda .
    docker build -f web/Dockerfile.vercel -t shoppers-web:local web
    docker compose config
    docker compose up --build

## Deployment and Rollback

- El orden obligatorio es bootstrap -> foundation -> dvc push/model -> image push -> service -> Vercel -> CORS final.
- Cada imagen API se etiqueta con Git SHA y se despliega por digest.
- Rollback API: reaplicar service con el digest anterior; el modelo queda ligado a esa imagen.
- Rollback frontend: promoción/rollback de un deployment anterior en Vercel.
- Rollback de datos/modelo: checkout del commit Git que contiene el .dvc correspondiente y dvc pull.
- No destruir buckets con datos o estado en un rollback; habilitar prevent_destroy para estado y DVC en entornos compartidos.

## Observability and Cost Controls

- Logs JSON con request ID, ruta, status, duración y model_version.
- CloudWatch alarm para Lambda Errors y API Gateway 5XX.
- Retención corta de logs en dev, parametrizada en Terraform.
- Lambda memory/timeout se ajustan después de medir cold start e inferencia.
- ECR lifecycle conserva un número pequeño de imágenes; no eliminar el digest activo.
- S3 lifecycle limpia versiones no actuales después del periodo acordado, conservando recuperación suficiente.
- Etiquetas obligatorias: Project, Environment, ManagedBy=Terraform, Owner.
- Documentar costos esperados antes de apply y destruir el entorno de demo cuando ya no se necesite, salvo buckets protegidos.

## Risks and Mitigations

- Desbalance 84.5/15.5 -> usar PR-AUC y métricas por clase; accuracy no será métrica principal.
- PageValues puede inducir fuga operacional -> comparar modelo sin esta variable y declarar scoring moment.
- Pickle/joblib ejecuta código al cargar -> solo artefactos del pipeline controlado, hash y bucket privado.
- Divergencia entre notebook y API -> serializar pipeline completo y probar el artefacto real.
- Experimentos sin soporte verificable -> registrar cada corrida con MLflow y documentar cómo abrir la UI local.
- Drift entre FastAPI y TypeScript -> snapshot OpenAPI y esquemas Zod probados.
- Cold start Lambda con scikit-learn -> imagen mínima, carga global, medición y plan B ECS Express.
- CORS abierto durante demos -> parametrizar y restringir al dominio Vercel final.
- Credenciales filtradas -> AWS SSO/profile local, GitHub OIDC y ninguna clave estática en Git.
- Terraform no puede crear Lambda antes de existir la imagen -> separar foundation y service.
- Terraform bootstrap circular -> bootstrap usa estado local únicamente para crear el bucket; luego los otros roots usan S3.
- DVC usa claves content-addressed no amigables -> la aplicación no lee el bucket directamente; CI materializa con dvc pull.
- Dependencia de una característica reciente de Vercel Docker -> validar un hello deployment temprano; si falla, usar despliegue Next.js nativo manteniendo Docker local.

## Open Questions

- Confirmar con el docente si “el despliegue debe hacerse empleando contenedores Docker” exige containerizar y desplegar también el tablero. El plan ya containeriza ambos para cubrir la interpretación estricta.
- Definir con el equipo el costo de error más importante: falso negativo frente a falso positivo. Mientras se define, seleccionar umbral con una regla explícita que garantice recall mínimo y maximice precision.
- Definir nombre de la cuenta/organización GitHub, región AWS, dominio Vercel y presupuesto antes de terraform apply.

## Acceptance Criteria

### Entrega 1

- El repositorio Git tiene commits trazables por integrante.
- dvc pull restaura el CSV desde un bucket S3 privado creado con Terraform.
- 01_eda.ipynb se ejecuta desde cero y contiene conclusiones ligadas al negocio.
- Existe mockup de una sola pantalla de predicción con estados vacío, loading, success y error.
- El reporte incluye problema, pregunta, alcance, dataset, EDA, mockup, enlaces y capturas.

### Entrega 2

- MLflow permite inspeccionar runs de baseline, candidatos, variantes y champion con parámetros, métricas y artefactos.
- La pantalla única coincide con el mockup y consume el contrato FastAPI mediante un mock o API local.
- El repositorio y reporte evidencian contribuciones individuales.

### Prototipo final

- 02_model_training.ipynb produce el champion y metadata con seed fijo.
- Al menos tres pipelines, incluyendo baseline, se comparan sin tocar test hasta el final.
- El modelo con y sin PageValues se evalúa y la decisión queda justificada.
- dvc pull restaura exactamente el champion usado para construir la imagen.
- POST /v1/predict valida las 17 features y devuelve probabilidad, clase, umbral y versión.
- La imagen Lambda se almacena en ECR y Terraform crea Lambda/API Gateway/CloudWatch/IAM.
- La pantalla Next.js desplegada en Vercel consume la API y muestra la predicción, probabilidad, umbral y comparación con la tasa base.
- API y frontend tienen Dockerfiles funcionales.
- CI, Ruff, mypy, pytest, frontend checks, Terraform validate y builds Docker quedan en verde.
- No hay datasets, modelos binarios, estados Terraform ni credenciales dentro de Git.
- Existen manual de usuario, manual de instalación y guion de video de menos de 10 minutos.

## Definition of Done

- Código, notebooks, infraestructura, documentación y pruebas implementados.
- Dataset y modelo publicados y recuperables mediante DVC/S3.
- API y dashboard desplegados y conectados.
- Terraform reproduce los objetos AWS sin pasos manuales fuera del bootstrap documentado.
- Evidencias y contribución individual documentadas.
- Plan actualizado si cambia el alcance.

## Research Sources

- UCI dataset: https://archive.ics.uci.edu/dataset/468/online%20shoppers%20purchasing%20intention%20dataset
- UCI DOI and license: https://doi.org/10.24432/C5F88Q
- DVC Amazon S3 remote: https://dvc.org/doc/user-guide/data-management/remote-storage/amazon-s3
- Amazon ECR: https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html
- AWS Lambda Python container images: https://docs.aws.amazon.com/lambda/latest/dg/python-image.html
- API Gateway HTTP APIs: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html
- AWS Fargate or Lambda decision guide: https://docs.aws.amazon.com/decision-guides/latest/fargate-or-lambda/fargate-or-lambda.html
- ECS Express Mode resources: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-work.html
- App Runner availability change: https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html
- Terraform S3 backend and native locking: https://developer.hashicorp.com/terraform/language/backend/s3
- Terraform aws_lambda_function: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function
- Vercel Dockerfile deployment, 2026-06-30: https://vercel.com/blog/dockerfile-on-vercel
