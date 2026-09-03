# Manual de usuario

1. Abra la URL de la aplicación.
2. Complete los conteos y duraciones de páginas de la sesión.
3. Ingrese BounceRates, ExitRates y SpecialDay entre 0 y 1.
4. Seleccione mes, tipo de visitante y fin de semana; ingrese los códigos de sistema operativo, navegador, región y tráfico.
5. Pulse Predecir compra.

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

Para integrar otro cliente directamente con FastAPI, consulte la [guía de uso de la API](api-guide.md).
