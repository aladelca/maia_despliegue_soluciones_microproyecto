# Guía de uso de la API de predicción

## Propósito

La API recibe las características observadas de una sesión de comercio electrónico y devuelve la probabilidad estimada de compra. El frontend Next.js consume este mismo contrato; también puede llamarse directamente desde curl, Python u otro cliente HTTP.

La inferencia procesa una sesión por petición. El endpoint no recibe el CSV de entrenamiento, no acepta archivos y no vuelve a entrenar el modelo.

## URL base

Para desarrollo local:

```text
http://localhost:8000
```

Después del despliegue, sustituya esa dirección por el output `api_base_url` de Terraform. Los paths y contratos permanecen iguales.

La instancia documentada de Entrega 2 responde en:

```text
https://nzm0y8hoja.execute-api.us-east-1.amazonaws.com
```

La documentación interactiva de FastAPI está disponible en:

```text
http://localhost:8000/docs
```

Desde Swagger UI puede expandir `POST /v1/predict`, seleccionar **Try it out**, editar el JSON y ejecutar la petición sin instalar otro cliente.

## Verificar que el modelo esté disponible

Antes de generar predicciones, consulte health:

```bash
curl --fail http://localhost:8000/health
```

Respuesta saludable:

```json
{
  "status": "ok",
  "model_version": "feature/implement-ec2-mlflow-experimentation-and-deploy-315cd8d3"
}
```

`status: "degraded"` significa que FastAPI inició, pero no pudo cargar o verificar el joblib. En local, confirme que existen `models/champion.joblib` y `models/model_metadata.json`. La versión concreta puede cambiar cuando se entrene y despliegue un nuevo champion.

## Consultar metadata del modelo

```bash
curl --fail http://localhost:8000/v1/model/metadata
```

Este endpoint devuelve la versión, el umbral, las variables esperadas, el nombre del champion,
feature set, uso de `PageValues`, tasa base, versión DVC, run/experimento MLflow y métricas de
validación y audit. Es útil para comprobar qué modelo atiende una instancia sin descargar el
artefacto binario. En el deployment actual, `mlflow_run_id` es
`315cd8d316ba47a899f6ba249cc721d9`.

## Generar una predicción con curl

```bash
curl --fail-with-body \
  --request POST http://localhost:8000/v1/predict \
  --header 'Content-Type: application/json' \
  --data '{
    "Administrative": 2,
    "Administrative_Duration": 35.5,
    "Informational": 1,
    "Informational_Duration": 12.0,
    "ProductRelated": 12,
    "ProductRelated_Duration": 420.0,
    "BounceRates": 0.01,
    "ExitRates": 0.03,
    "PageValues": 18.5,
    "SpecialDay": 0.0,
    "Month": "Nov",
    "OperatingSystems": 2,
    "Browser": 2,
    "Region": 1,
    "TrafficType": 3,
    "VisitorType": "Returning_Visitor",
    "Weekend": false
  }'
```

Ejemplo de respuesta:

```json
{
  "will_purchase": true,
  "purchase_probability": 0.884808,
  "threshold": 0.5673544537449113,
  "model_version": "feature/implement-ec2-mlflow-experimentation-and-deploy-315cd8d3"
}
```

Los valores son ilustrativos y pueden cambiar cuando se publique otra versión del modelo.

## Interpretar el resultado

| Campo | Significado |
| --- | --- |
| `purchase_probability` | Probabilidad estimada de que la sesión termine en compra, entre 0 y 1 |
| `threshold` | Punto de corte elegido con el conjunto de validación |
| `will_purchase` | `true` cuando la probabilidad es mayor o igual al umbral; de lo contrario, `false` |
| `model_version` | Identificador del artefacto que produjo la respuesta |

La probabilidad no es una garantía ni una explicación causal. El umbral no es necesariamente 0.5
porque fue optimizado por F1 sobre las predicciones out-of-fold de desarrollo. Para auditoría o
comparación, almacene siempre la probabilidad, el umbral y la versión, no solamente el booleano.

## Variables de entrada

El contrato público usa exactamente las 17 variables siguientes. Utilice los nombres con las mayúsculas mostradas y no envíe campos adicionales.

| Variable | Tipo y validación | Descripción |
| --- | --- | --- |
| `Administrative` | Entero ≥ 0 | Cantidad de páginas administrativas visitadas |
| `Administrative_Duration` | Número ≥ 0 | Tiempo dedicado a páginas administrativas |
| `Informational` | Entero ≥ 0 | Cantidad de páginas informativas visitadas |
| `Informational_Duration` | Número ≥ 0 | Tiempo dedicado a páginas informativas |
| `ProductRelated` | Entero ≥ 0 | Cantidad de páginas de producto visitadas |
| `ProductRelated_Duration` | Número ≥ 0 | Tiempo dedicado a páginas de producto |
| `BounceRates` | Número entre 0 y 1 | Tasa de rebote asociada a las páginas visitadas |
| `ExitRates` | Número entre 0 y 1 | Tasa de salida asociada a las páginas visitadas |
| `PageValues` | Número ≥ 0 | Valor de página calculado para la sesión |
| `SpecialDay` | Número entre 0 y 1 | Cercanía temporal a una fecha especial |
| `Month` | Categoría | `Feb`, `Mar`, `May`, `June`, `Jul`, `Aug`, `Sep`, `Oct`, `Nov` o `Dec` |
| `OperatingSystems` | Entero ≥ 1 | Código categórico del sistema operativo |
| `Browser` | Entero ≥ 1 | Código categórico del navegador |
| `Region` | Entero ≥ 1 | Código categórico de región |
| `TrafficType` | Entero ≥ 1 | Código categórico de la fuente de tráfico |
| `VisitorType` | Categoría | `New_Visitor`, `Returning_Visitor` u `Other` |
| `Weekend` | Booleano | `true` si la sesión ocurrió en fin de semana |

Las duraciones usan las unidades del dataset original. Los códigos categóricos deben conservar la codificación del sistema que origina la sesión. `PageValues` puede no estar disponible al comienzo de la navegación; la predicción documentada corresponde al momento en que todas las variables están disponibles.

## Ejemplo desde Python

El entorno de desarrollo incluye `httpx`:

```python
import httpx

session = {
    "Administrative": 2,
    "Administrative_Duration": 35.5,
    "Informational": 1,
    "Informational_Duration": 12.0,
    "ProductRelated": 12,
    "ProductRelated_Duration": 420.0,
    "BounceRates": 0.01,
    "ExitRates": 0.03,
    "PageValues": 18.5,
    "SpecialDay": 0.0,
    "Month": "Nov",
    "OperatingSystems": 2,
    "Browser": 2,
    "Region": 1,
    "TrafficType": 3,
    "VisitorType": "Returning_Visitor",
    "Weekend": False,
}

response = httpx.post(
    "http://localhost:8000/v1/predict",
    json=session,
    timeout=29.0,
)
response.raise_for_status()
prediction = response.json()

print(prediction["purchase_probability"])
print(prediction["will_purchase"])
print(prediction["model_version"])
```

## Errores frecuentes

### HTTP 422 — payload inválido

FastAPI devuelve 422 si falta una variable, sobra un campo, se envía un tipo incorrecto o un valor está fuera de rango. Revise especialmente:

- tasas mayores que 1 o menores que 0;
- conteos negativos;
- nombres como `month` en lugar de `Month`;
- categorías no contempladas por el contrato;
- strings `"true"` y `"false"` en lugar de booleanos JSON.

### HTTP 503 — modelo no disponible

El servicio no pudo cargar o validar el modelo. Consulte `/health`, revise las variables `MODEL_PATH` y `MODEL_METADATA_PATH` y confirme que el SHA-256 del joblib corresponde a la metadata.

### Error CORS desde el navegador

Las llamadas con curl o Python no usan CORS. Si el error aparece únicamente en el navegador, configure `ALLOWED_ORIGIN` con el origen exacto del frontend y vuelva a desplegar o reiniciar la API.

El origin no incluye path ni `/` final. Cada dominio nuevo de Vercel requiere actualizar la
variable Terraform/GitHub y volver a aplicar `service`. El navegador usa un timeout de 29 segundos
para dejar margen al cold start dentro del límite de 30 segundos de API Gateway.

### HTTP 405 — método incorrecto

`/v1/predict` acepta `POST`; abrir esa URL directamente en la barra del navegador envía un `GET` y no genera una predicción.

## Alcance y seguridad

La API actual es un prototipo académico sin autenticación. No debe exponerse para uso comercial sin autorización, rate limiting, monitoreo de abuso y una política de tratamiento de datos. No envíe identificadores personales: el contrato requiere solamente las variables agregadas de la sesión.
