# EDA ampliado orientado a la pregunta de negocio

## Propósito

Este documento resume el análisis exploratorio orientado a responder:

> ¿Qué sesiones presentan mayor probabilidad de finalizar en una compra?

El análisis está implementado en `notebooks/09_eda_business_purchase_probability.ipynb`. El
notebook conserva las tablas, las figuras y las conclusiones junto al código que las genera.

## Alcance

El análisis se concentra en:

- balance de `Revenue`;
- conversión por `VisitorType`, mes y fin de semana;
- profundidad y duración de navegación frente a `Revenue`;
- relación de `BounceRates` y `ExitRates` con la conversión;
- relación de `PageValues` con la conversión;
- perfiles descriptivos que combinan señales relevantes;
- implicaciones para selección de métricas, transformaciones y disponibilidad de variables.

## Hallazgos principales

| Hallazgo | Evidencia observada | Implicación |
| --- | ---: | --- |
| Desbalance de clase | 1.908 compras de 12.330 sesiones (15,47 %) | Evaluar con PR-AUC, precision, recall y F1; no depender de accuracy. |
| Tipo de visitante | Nuevos: 24,91 %; recurrentes: 13,93 % | Usar `VisitorType` como contexto, no como regla aislada. |
| Estacionalidad | Noviembre: 25,35 %; febrero: 1,63 % | Validar `Month` fuera de muestra y considerar tamaños de grupo. |
| Fin de semana | 17,40 % frente a 14,89 % entre semana | Señal complementaria de efecto moderado. |
| Navegación profunda | Duración alta en producto: 23,56 % | Conservar conteos/duraciones y transformar variables sesgadas. |
| Bajo abandono | `ExitRates` hasta 1 %: 27,22 %; mayor de 10 %: 0,54 % | Permitir relaciones no lineales y comprobar disponibilidad al predecir. |
| `PageValues` | Cero: 3,85 %; positivo: 56,34 % | Comparar modelos con y sin esta variable por riesgo de indisponibilidad o leakage. |

Los intervalos de confianza de Wilson incluidos en el notebook permiten reconocer la incertidumbre
de los grupos pequeños. Los resultados son asociaciones descriptivas y no prueban causalidad.

## Respuesta sintética a la pregunta de negocio

Las sesiones con mayor probabilidad observada de compra combinan valor de página positivo, bajo
abandono y navegación profunda. El segmento con `PageValues > 0` y `ExitRates <= 2,5 %` convierte
al 61,26 % en 2.021 sesiones, frente a una línea base de 15,47 %. Sin depender de `PageValues`, las
sesiones con duración alta en páginas de producto y `ExitRates <= 2,5 %` convierten al 28,81 %.
En contraste, las sesiones con `PageValues = 0` y `ExitRates > 5 %` convierten solo al 1,76 %.

Estos segmentos resumen patrones del conjunto de datos; no son reglas operativas ni sustituyen la
predicción individual del modelo.

## Implicaciones para el modelamiento

1. Mantener evaluación estratificada y métricas sensibles a la clase positiva.
2. Conservar variables de navegación y abandono como continuas para no perder información.
3. Considerar transformaciones logarítmicas para conteos y duraciones con asimetría alta.
4. Permitir interacciones y relaciones no lineales entre profundidad, abandono y contexto.
5. Comparar variantes con y sin `PageValues`; verificar que cada variable exista en el momento real
   del scoring y aprender transformaciones únicamente dentro de validación cruzada.

## Artefactos reproducibles

- `reports/eda_business_summary.json`: cifras compactas para informe o tablero.
- `reports/figures/eda_business_conversion_context.png`: clase objetivo, visitante, mes y fin de semana.
- `reports/figures/eda_business_navigation_behavior.png`: niveles de actividad de navegación.
- `reports/figures/eda_business_abandonment.png`: bandas de rebote y salida.
- `reports/figures/eda_business_page_values.png`: distribución y gradiente de `PageValues`.

Para regenerarlos desde la raíz del repositorio:

```bash
uv run jupyter nbconvert \
  --to notebook \
  --execute \
  --inplace notebooks/09_eda_business_purchase_probability.ipynb
```

## Cambios respecto a la primera entrega

La definición del problema, la pregunta de negocio, el alcance y el conjunto de datos se mantienen
sin cambios. A partir de la retroalimentación de la primera entrega, se amplió el análisis
exploratorio para identificar las características asociadas con la conversión y fortalecer su
relación con la pregunta de negocio. La nueva exploración estudia el desbalance de la variable
objetivo, el contexto comercial, la profundidad de navegación, las señales de abandono y
`PageValues`, e incorpora conclusiones que justifican decisiones de métricas, variables y
validación del modelo.
