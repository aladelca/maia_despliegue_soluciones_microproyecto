# Manual de usuario

Abra el [dashboard público](https://maia-despliegue-soluciones-micropro.vercel.app). La navegación
lateral —horizontal en pantallas pequeñas— ofrece estas vistas:

- **Resumen:** KPIs de sesiones y conversión, patrones por mes, visitante y tráfico, y el formulario
  de inferencia rápida.
- **Análisis de datos:** exploración ampliada de los agregados descriptivos versionados.
- **Predicción:** metadata completa del champion y formulario con las 17 variables del contrato.
- **Historial:** últimas diez inferencias guardadas exclusivamente en el navegador mediante
  `localStorage`; no se envían a una base de datos.
- **Experimentación:** resultados de la campaña EC2/MLflow, protocolo de cinco folds, trazabilidad
  del champion y top cinco de los 66 candidatos.
- **Proyecto:** objetivo, arquitectura de despliegue y limitaciones de uso.

Para generar una predicción:

1. Complete los conteos y duraciones de páginas de la sesión.
2. Ingrese BounceRates, ExitRates y SpecialDay entre 0 y 1.
3. Seleccione mes, tipo de visitante y fin de semana; ingrese los códigos de sistema operativo,
   navegador, región y tráfico.
4. Pulse **Predecir compra**.

La pantalla muestra:

- El nombre del champion desplegado y su run ID de MLflow.
- La versión DVC del dataset, feature set y uso o no de `PageValues`.
- PR-AUC promedio de validación y PR-AUC del audit set.
- Compra probable o poco probable según el umbral del modelo.
- La probabilidad estimada para la sesión.
- Una comparación contra la tasa positiva obtenida dinámicamente desde la metadata del modelo.
- El umbral y la versión del modelo que generó la respuesta.

Si la metadata no puede cargarse, el formulario sigue habilitado y muestra una advertencia. Si una
predicción falla, revise los rangos e intente nuevamente. Si persiste, verifique que la API responda
en `/health` y que CORS permita el dominio exacto de Vercel.

La salida es una estimación predictiva basada en un dataset académico. No explica causalidad ni debe utilizarse como única base para tomar decisiones sobre personas.

## Procedencia de los datos del dashboard

- Los totales y las gráficas provienen de `reports/eda_summary.json`, generado desde el dataset UCI
  controlado con DVC.
- El ranking proviene de `reports/experiments/final_model_comparison.json`, resultado de la campaña
  real ejecutada en EC2 y registrada en MLflow.
- La tarjeta del champion consulta en vivo `GET /v1/model/metadata` en AWS.
- Cada resultado consulta en vivo `POST /v1/predict`; el frontend no ejecuta un modelo propio.

Para integrar otro cliente directamente con FastAPI, consulte la [guía de uso de la API](api-guide.md).
