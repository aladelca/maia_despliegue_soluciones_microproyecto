# Manual de usuario

1. Abra la URL de la aplicación.
2. Complete los conteos y duraciones de páginas de la sesión.
3. Ingrese BounceRates, ExitRates y SpecialDay entre 0 y 1.
4. Seleccione mes, tipo de visitante y fin de semana; ingrese los códigos de sistema operativo, navegador, región y tráfico.
5. Pulse Predecir compra.

La pantalla muestra:

- Compra probable o poco probable según el umbral del modelo.
- La probabilidad estimada para la sesión.
- Una comparación contra la tasa positiva del dataset, 15.5%.
- El umbral y la versión del modelo que generó la respuesta.

Si aparece un error, revise los rangos e intente nuevamente. Si persiste, verifique que la API responda en /health.

La salida es una estimación predictiva basada en un dataset académico. No explica causalidad ni debe utilizarse como única base para tomar decisiones sobre personas.
