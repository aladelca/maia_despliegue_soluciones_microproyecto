# Arquitectura de la solución

## Objetivo y criterios de diseño

La solución estima la probabilidad de que una sesión de comercio electrónico termine en compra. La arquitectura separa entrenamiento, almacenamiento de artefactos, inferencia y presentación para que cada parte pueda versionarse y desplegarse sin acoplar el frontend al modelo.

Las decisiones se tomaron con los siguientes criterios:

- mantener el alcance académico y operativo pequeño;
- conservar trazabilidad entre código, dataset, experimento, modelo e imagen desplegada;
- evitar servidores permanentes para una carga de demostración intermitente;
- impedir que el frontend cargue o ejecute el archivo joblib;
- usar credenciales temporales y recursos privados;
- automatizar AWS mediante Terraform;
- desplegar Next.js directamente desde GitHub en Vercel y usar Docker solamente en el backend.

## Vista general

```text
                         FLUJO DE ENTRENAMIENTO

 Git branch/tag ───────────────┐
                              │
 DVC pointer + objeto S3 ─────┼──> EC2 temporal (Docker)
                              │          │
 Terraform mlflow ────────────┘          ├──> MLflow + SQLite en EBS
                                         ├──> 66 candidatos × 5 folds
                                         ├──> artefactos/resultados en S3
                                         └──> champion.joblib + metadata
                                                        │
                                                   DVC pointer
                                                        │
                                                     S3 DVC


                         FLUJO DE DESPLIEGUE

 GitHub Actions ──credenciales temporales/OIDC──> AWS IAM
       │                                             │
       ├── dvc pull <────────────────────────────────┘
       ├── tests
       ├── Docker build: FastAPI + champion
       ├── push por Git SHA ───────────────> Amazon ECR
       └── Terraform apply ────────────────────────┐
                                                   v
                                      Lambda + API Gateway + CloudWatch


                          FLUJO DE INFERENCIA

 Usuario ──HTTPS──> Next.js en Vercel ──HTTPS──> API Gateway HTTP API
                                                       │
                                                       v
                                             Lambda: FastAPI + Mangum
                                                       │
                                                       v
                                            Pipeline sklearn en memoria
                                                       │
                                                       v
                              probabilidad + clase + umbral + versión
```

## Componentes y responsabilidades

| Componente | Responsabilidad | Lo que deliberadamente no hace |
| --- | --- | --- |
| Git/GitHub | Versionar código, notebooks, configuración, metadata y archivos `.dvc` | No almacena CSV, joblib, secretos ni estado Terraform |
| DVC + S3 | Versionar el contenido pesado del dataset y del modelo mediante hashes | No sirve inferencias ni expone objetos públicamente |
| Notebook canónico | Presentar protocolo, leaderboard y champion exportados por la campaña | No vuelve a entrenar ni reemplaza el orquestador en `src/` |
| EC2 temporal | Ejecutar contenedores de MLflow y experimentación con CPU y memoria delimitadas | No atiende inferencias ni permanece encendida después de la campaña |
| MLflow + EBS/S3 | Registrar los 66 candidatos, folds, artifacts y modelo registrado | No se expone públicamente ni funciona como servicio permanente multiusuario |
| Amazon ECR | Almacenar imágenes inmutables del backend | No ejecuta contenedores; esa responsabilidad pertenece a Lambda |
| AWS Lambda | Ejecutar la imagen que contiene FastAPI, dependencias y modelo champion | No entrena ni descarga el modelo desde S3 durante una petición |
| API Gateway | Proveer endpoint HTTPS, integración Lambda, CORS y logs de acceso | No implementa la lógica de predicción |
| FastAPI | Validar las 17 variables, invocar el pipeline y devolver un contrato estable | No expone el joblib ni permite cargar modelos suministrados por usuarios |
| Vercel | Construir y servir Next.js desde GitHub | No ejecuta el modelo y no usa un contenedor Docker del proyecto |
| Terraform | Declarar y reproducir los recursos AWS y sus permisos | No entrena modelos ni administra el proyecto Vercel |
| GitHub Actions | Validar, recuperar el artefacto exacto, construir la imagen y aplicar el servicio | No conserva access keys permanentes |

## Flujo de entrenamiento y trazabilidad

EC2 descarga la key content-addressed señalada por el pointer DVC, en lugar de depender de un
nombre mutable. El contenedor de experimentación llama funciones reutilizables de
`src/online_shoppers`, genera features dentro de cada fold y compara 66 candidatos pertenecientes
a nueve familias, con y sin `PageValues`. Todas las corridas quedan en el servidor MLflow de la
misma instancia y sus artefactos en S3.

Las sesiones duplicadas se mantienen en el mismo grupo. Un primer `StratifiedGroupKFold(5)` separa
desarrollo y audit; otro `StratifiedGroupKFold(5)` produce métricas y probabilidades OOF. La
selección usa PR-AUC CV, el umbral maximiza F1 OOF y el audit set se consulta una sola vez después
de elegir el champion. El resultado serializado es un `ModelBundle` que contiene:

- el `Pipeline` completo de scikit-learn;
- el preprocesamiento y orden esperado de variables;
- el clasificador;
- el umbral de decisión calculado en validación;
- la versión de esquema y la versión del modelo.

El joblib se acompaña de metadata JSON y un SHA-256. DVC versiona el binario y Git conserva el pointer. Esta cadena permite relacionar:

```text
commit Git -> hash DVC del dataset -> run/candidate MLflow -> champion run
           -> hash del joblib + pointer DVC -> imagen ECR por Git SHA
           -> digest desplegado en Lambda -> metadata mostrada en Vercel
```

La relación evita el escenario en que la API anuncie una versión, pero ejecute silenciosamente otro modelo.

### Por qué el modelo queda dentro de la imagen

El pipeline se copia en la imagen Docker durante CI, en lugar de descargarlo desde S3 en cada cold start. Esto ofrece cuatro ventajas:

- el código y el modelo forman una unidad desplegable e inmutable;
- Lambda no necesita permisos de lectura sobre el bucket DVC;
- un rollback consiste en restaurar un digest anterior de ECR;
- las peticiones no dependen de S3 después de iniciar la función.

El costo de esta decisión es que una nueva versión del modelo requiere reconstruir y desplegar la imagen. Para este proyecto es una propiedad deseable porque hace explícito cada cambio de modelo.

## Flujo de inferencia

1. El usuario llena el formulario en la única pantalla de Next.js.
2. El navegador valida la forma básica del payload y envía las 17 variables por HTTPS.
3. API Gateway termina HTTPS, aplica CORS para el dominio de Vercel y delega la ruta a FastAPI, que rechaza los métodos no definidos.
4. Mangum transforma el evento HTTP API v2 en una petición ASGI para FastAPI.
5. Pydantic rechaza campos faltantes, adicionales, infinitos o fuera de rango.
6. El servicio construye un DataFrame en el orden de entrenamiento y ejecuta `predict_proba`.
7. La API compara la probabilidad con el umbral versionado y devuelve probabilidad, clase, umbral y versión.
8. El frontend representa el resultado y lo compara visualmente con la tasa base del dataset.

La API carga el modelo una vez durante el ciclo de vida del proceso. Las invocaciones calientes
reutilizan el objeto en memoria, evitando deserializar el artifact de aproximadamente 2,1 MB en
cada petición.

## Justificación de las decisiones principales

### FastAPI sobre AWS Lambda

Lambda se eligió porque la aplicación tiene tráfico bajo e intermitente, las predicciones son síncronas y no existen jobs largos ni conexiones persistentes. El modelo puede cargarse en memoria dentro de los límites configurables de la función. Esto reduce la operación de servidores y permite escalar a cero cuando no hay uso.

FastAPI mantiene un contrato OpenAPI explícito, validación con Pydantic y una separación limpia entre transporte y servicio de predicción. Mangum permite ejecutar la misma aplicación ASGI en Lambda sin crear handlers diferentes para cada endpoint.

La principal desventaja es el cold start causado por Python, scikit-learn y la carga del modelo. El proyecto lo acepta porque prioriza simplicidad y costo variable sobre latencia constante. Si las mediciones muestran una latencia inaceptable o aparece tráfico sostenido, el mismo contenedor puede migrarse a ECS/Fargate o a otro runtime HTTP administrado.

### Imagen Lambda en ECR

El backend se empaqueta como imagen porque scikit-learn, pandas y el modelo son más fáciles de reproducir en un filesystem controlado que mediante un paquete ZIP ensamblado manualmente. ECR usa tags inmutables y el servicio recibe una URI por digest `sha256`, no `latest`.

ECR es el registro; no es el servidor de aplicación. Lambda obtiene y ejecuta la imagen. EC2 no se
usa para inferencia porque exigiría administrar sistema operativo, parches, disponibilidad, TLS y
capacidad aunque no hubiera tráfico; su uso queda limitado a la campaña temporal.

### API Gateway HTTP API

API Gateway aporta una URL HTTPS administrada, integración nativa con Lambda, configuración CORS y logs de acceso. Una HTTP API es suficiente porque el prototipo no necesita transformaciones complejas, API keys, cuotas por cliente ni las funciones adicionales de una REST API clásica.

La ruta `$default` delega el routing interno a FastAPI, de modo que el contrato vive en una sola capa. Esto simplifica añadir `/health`, `/v1/model/metadata` y `/v1/predict` sin duplicar cada ruta en Terraform.

### Next.js en Vercel mediante GitHub

Vercel se conecta directamente al repositorio y usa `web` como Root Directory. Los pull requests pueden producir previews y `main` puede promoverse a producción. El frontend no tiene Dockerfile porque la decisión del proyecto es aprovechar el build nativo de Next.js en Vercel.

Esta separación mantiene el frontend pequeño y estático, permite desplegarlo sin reconstruir la imagen de inferencia y evita ejecutar Python en Vercel. La única configuración compartida es `NEXT_PUBLIC_API_BASE_URL`; el navegador nunca recibe rutas S3, credenciales AWS ni ubicación del modelo.

### DVC sobre S3

Git no es apropiado para versionar directamente el CSV y un joblib grande. DVC conserva en Git archivos pequeños con el hash del contenido y usa S3 privado como almacenamiento remoto. Así, un checkout del repositorio más `dvc pull` reconstruye la versión de datos y modelo asociada al commit.

El bucket tiene bloqueo de acceso público, cifrado del lado del servidor, versionado y protección contra destrucción accidental. Las versiones no actuales expiran después del periodo definido para limitar acumulación, sin perder recuperación inmediata.

### MLflow en EC2 temporal

Un servidor MLflow en EC2 permite registrar todos los experimentos en un punto central durante la
campaña y usar Model Registry sin entrenar en el equipo local. SQLite se conserva en un volumen EBS
que no se elimina al terminar la instancia, mientras los artifacts y outputs también se copian a un
bucket S3 privado, cifrado y versionado.

La instancia `t3.medium` tiene swap acotado, autoapagado a cuatro horas y acceso al puerto 5000
limitado a un CIDR. Después de capturar o consultar resultados se detiene para no acumular costo.
El diseño no pretende ser un MLflow multiusuario de producción: para eso serían necesarios TLS,
autenticación y un backend de base de datos administrado.

### Terraform en cuatro raíces

La infraestructura se divide para resolver dependencias reales:

1. `bootstrap` crea el bucket de estado utilizando estado local inicial.
2. `foundation` usa ese backend y crea recursos duraderos: bucket DVC, ECR y, cuando la cuenta lo
   permite, rol OIDC.
3. `mlflow` crea S3, security group y el runner EC2 que ejecuta y conserva la campaña.
4. `service` se aplica solamente después de publicar una imagen y crea Lambda, API Gateway, IAM y CloudWatch.

Una sola raíz no puede crear limpiamente Lambda antes de que exista la imagen de ECR. Separar estado y ciclo de vida también permite actualizar o revertir el servicio sin poner en riesgo el bucket DVC.

## Seguridad y límites de confianza

### Identidades

- Los desarrolladores deben usar AWS SSO o perfiles locales.
- GitHub Actions intercambia un token OIDC por credenciales temporales en una cuenta permanente;
  AWS Academy usa sus credenciales de sesión como secrets renovables.
- La confianza del rol se restringe al repositorio, la rama principal o el environment configurado.
- El rol de despliegue se limita al repositorio ECR, objetos DVC, estado y recursos nombrados del servicio.
- El rol runtime de Lambda solo necesita permisos básicos de logs; no accede a DVC.

### Datos y artefactos

- S3 y ECR permanecen privados.
- El bucket MLflow bloquea acceso público, exige TLS, cifra objetos y conserva versiones.
- El UI de MLflow sólo acepta tráfico desde el CIDR configurado y la instancia queda detenida al
  terminar la campaña.
- El joblib solo se carga desde el pipeline controlado; cargar pickle/joblib externo permitiría ejecutar código arbitrario.
- El SHA-256 de metadata se verifica antes de usar el modelo.
- `.gitignore` excluye CSV, joblib, estado Terraform, archivos `.env`, bases MLflow y PDF del curso.

### Superficie HTTP

- Pydantic prohíbe campos adicionales y valida rangos.
- CORS acepta únicamente el origen Vercel configurado.
- La API no implementa autenticación de usuario porque no almacena datos personales ni ejecuta acciones comerciales; antes de exponerla para uso real se debe añadir autorización, rate limiting y protección de abuso.
- Los mensajes de error no devuelven stack traces ni rutas locales.

## Observabilidad y operación

FastAPI emite logs JSON con request ID, método, ruta, status, duración y versión del modelo. API Gateway registra request ID, route key, status y latencia. CloudWatch conserva logs durante un periodo configurable y define alarmas para errores Lambda y respuestas 5XX.

Los endpoints cumplen propósitos distintos:

- `/health` indica si el artefacto fue cargado y expone su versión;
- `/v1/model/metadata` permite comprobar champion y métricas sin revelar el binario;
- `/v1/predict` atiende la inferencia validada.

Para diagnosticar un incidente se debe correlacionar el request ID de API Gateway con el log de FastAPI y confirmar el `model_version`. Una respuesta degradada en health evita presentar como saludable una función que inició sin modelo válido.

## Escalabilidad, disponibilidad y costo

La arquitectura escala cada plano de manera independiente:

- Vercel distribuye los assets y el frontend;
- API Gateway absorbe las conexiones HTTP;
- Lambda crea concurrencia según las invocaciones;
- cada proceso Lambda conserva su propia copia del modelo en memoria;
- S3 y ECR están fuera del camino de una invocación caliente.

El diseño evita servidores de inferencia y bases de datos permanentemente encendidos. EC2 se usa
sólo durante la campaña y se detiene después; sus principales costos son las horas activas, EBS y
el bucket MLflow. En serving, los generadores de costo son almacenamiento/versiones en S3 y ECR,
invocaciones y duración de Lambda, API Gateway, logs y cualquier plan contratado en Vercel.

No se configura concurrencia provisionada porque eliminaría parte del ahorro para una demo. Si el cold start importa más que el costo, se puede habilitar después de medir. La solución es regional y no ofrece recuperación multi-región; esa complejidad no se justifica para el microproyecto.

## Alternativas consideradas

| Alternativa | Ventaja | Razón para no elegirla ahora |
| --- | --- | --- |
| Streamlit | Construcción muy rápida de una interfaz de datos | Acopla más la experiencia al runtime Python y no corresponde a la pantalla Next.js solicitada |
| Frontend Docker en Vercel | Unifica el concepto de contenedor | Añade complejidad sin beneficio para una sola pantalla; el proyecto exige integración GitHub → Vercel |
| EC2 permanente para el API | Control total y latencia predecible | Requiere servidor encendido, parches, TLS, monitoreo y capacidad manual; EC2 se reserva sólo para entrenamiento acotado |
| ECS/Fargate | Mejor latencia estable para contenedores HTTP | Mayor costo y operación base para tráfico intermitente; queda como plan de migración |
| Descargar el modelo desde S3 en runtime | Permite cambiar el modelo sin reconstruir imagen | Debilita la inmutabilidad, amplía IAM y añade dependencia de red al arranque |
| Servir el joblib desde el frontend | Evita una API | Expone el artefacto, no es compatible con scikit-learn en navegador y elimina validación centralizada |
| Entrenamiento administrado en AWS | Automatiza experimentos y escalamiento | El dataset y los modelos caben en una corrida local; no compensa el costo y complejidad inicial |

## Riesgos y evolución

- `PageValues` aporta gran capacidad predictiva, pero puede no estar disponible temprano en la sesión. Se mantienen métricas de la variante sin esa variable para decidir el momento de scoring.
- El cold start debe medirse con la imagen real. Una migración a ECS/Fargate conserva FastAPI y el contenedor.
- MLflow usa HTTP y SQLite detrás de un CIDR restringido. Si permanece encendido o incorpora más
  usuarios, debe añadirse TLS, autenticación y una base administrada.
- Reiniciar la EC2 asigna una IP pública distinta; Terraform actualiza el output, mientras EBS/S3
  conservan las corridas.
- La API pública de demostración carece de autenticación, WAF y cuotas por consumidor. Son requisitos previos para un entorno comercial.
- Solo existe un entorno `dev` documentado. Producción debería usar estados, dominios, roles y políticas de retención separados.
- El frontend y la API se despliegan independientemente; cambios incompatibles requieren versionar el contrato bajo una nueva ruta, por ejemplo `/v2`.

## Resumen de la decisión

La arquitectura optimiza trazabilidad y simplicidad operativa: DVC/S3 identifica datos y modelos,
EC2 ejecuta una campaña acotada, MLflow conserva cada candidato y registra el champion, Docker
congela FastAPI junto con ese artefacto, ECR almacena la imagen, Lambda la ejecuta, API Gateway
expone HTTPS y Vercel sirve una pantalla conectada a la metadata real. Terraform reproduce los
cuatro ciclos de infraestructura y las credenciales permanecen fuera del repositorio.
