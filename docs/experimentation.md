# Experimentación reproducible con EC2 y MLflow

## Alcance

La campaña implementada entrena exclusivamente en EC2 y usa un servidor MLflow levantado en la
misma instancia. Su objetivo es comparar alternativas amplias con un protocolo único, conservar
cada intento —incluidos sus parámetros, folds y artefactos— y producir un champion que pueda
relacionarse con el commit, el hash DVC y la imagen servida por Lambda.

La lógica está en `src/online_shoppers/experimentation.py`, el entry point reproducible es
`python -m online_shoppers experiment` y `notebook/online-shoppers-ec2-large.ipynb` presenta los
resultados exportados. El notebook no vuelve a entrenar modelos al documentar la campaña.

## Protocolo de evaluación

1. Se validan las 12.330 filas y las 17 variables de entrada.
2. Las filas con las mismas variables crudas reciben el mismo `session_group`.
3. El primer fold de un `StratifiedGroupKFold(5)` se reserva como audit set sellado.
4. Cada candidato genera predicciones out-of-fold sobre desarrollo mediante otro
   `StratifiedGroupKFold(5)`.
5. La selección usa `cv_pr_auc_mean`; F1 OOF y la desviación de PR-AUC resuelven empates.
6. El umbral del candidato se calcula maximizando F1 únicamente sobre sus predicciones OOF.
7. Sólo el champion se vuelve a ajustar con todo desarrollo y se evalúa una vez en audit.

La agrupación evita que sesiones duplicadas crucen train, validación o audit. Los transformadores
que aprenden estado —por ejemplo, categorías de tráfico frecuentes, escalado y one-hot encoding—
se ajustan dentro de cada pipeline/fold.

## Catálogo de candidatos

El perfil `full` ejecuta 33 configuraciones para cada uno de dos feature sets, con y sin
`PageValues`, para un total de 66 candidatos.

| Familia | Configuraciones por feature set | Papel en la comparación |
| --- | ---: | --- |
| Dummy prior | 1 | Piso no predictivo |
| Regresión logística | 3 | Baseline lineal balanceado |
| Random Forest | 4 | Bagging con pesos balanceados |
| Extra Trees | 4 | Árboles aleatorizados |
| HistGradientBoosting | 4 | Booster nativo de scikit-learn |
| CatBoost | 6 | Booster principal; profundidad, learning rate y L2 |
| XGBoost | 4 | Challenger de boosting |
| LightGBM | 4 | Challenger de boosting |
| MLP PyTorch | 3 | Red neuronal densa con early stopping |

El feature engineering agrega, entre otras señales:

- duración y páginas totales;
- duración media por página y shares de duración;
- diferencia entre exit y bounce rate;
- interacción de duración de producto con permanencia;
- transformaciones `log1p` para conteos y duraciones sesgadas;
- periodo estacional, presencia de día especial y tráfico infrecuente;
- interacción entre visitante recurrente y fin de semana.

## Estructura de tracking

MLflow conserva 68 runs terminales:

```text
campaign parent
├── 66 candidate child runs
└── 1 champion child run
    └── modelo registrado: online-shoppers-purchase-intention@champion
```

Cada candidato registra familia, feature set, hiperparámetros, commit, versión DVC, duración,
métricas agregadas, métricas OOF y `fold_metrics.json`. El run champion agrega el pipeline
serializado, metadata, métricas de audit, signature e input example. El parent conserva el
protocolo y la comparación completa.

El backend MLflow es SQLite sobre el EBS persistente de EC2. Los artefactos y una copia de todos
los outputs de la campaña se guardan en S3 privado, cifrado y versionado. Por eso detener la
instancia no elimina los runs.

## Resultado promovido

| Campo | Valor |
| --- | --- |
| Experimento | `online-shoppers-ec2-large-experiment` |
| Parent run | `f05ac6087e2b4e7e9a5f1a842d019159` |
| Champion run | `315cd8d316ba47a899f6ba249cc721d9` |
| Champion | `catboost__engineered_with_page_values__depth_8_lr_0.03_l2_5` |
| Dataset | `md5:cc6ec1db03b4f10f8de52c56ff48b085` |
| PR-AUC CV | `0.7562165276 ± 0.0224940549` |
| PR-AUC audit | `0.7368047815` |
| F1 audit | `0.6635838150` |
| SHA-256 joblib | `9fbb9d174c69da5ba632498ba0b53f02382d0aa12f530bc2420241a1d39640e2` |

Los resultados versionados están en:

- `reports/experiments/protocol_manifest.json`;
- `reports/experiments/final_model_comparison.json`;
- `reports/model_metrics.json`;
- `models/model_metadata.json`;
- `models/champion.joblib.dvc`.

## Validación local rápida

El perfil `smoke` comprueba carga de datos, tracking, pipelines, registro y generación de outputs
con dos candidatos y dos folds. No sustituye la campaña EC2.

```bash
uv sync --all-groups --locked
uv run dvc pull data/raw/online_shoppers_intention.csv.dvc
uv run python -m online_shoppers experiment \
  --profile smoke \
  --tracking-uri sqlite:///mlflow.db \
  --data-path data/raw/online_shoppers_intention.csv \
  --output-root /tmp/online-shoppers-smoke \
  --experiment-name online-shoppers-smoke
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
```

Abra <http://127.0.0.1:5000>. Para reproducir el perfil `full` sobre EC2, siga desde el paso 5 de
la sección [Reproducir la solución completa](../README.md#reproducir-la-solución-completa).

## Operación y límites

- La instancia se autoapaga después de cuatro horas y también debe detenerse manualmente al
  terminar; no se debe terminar porque EBS contiene el backend SQLite.
- Reiniciar la misma EC2 recupera MLflow, pero no vuelve a ejecutar su `user_data`. Una nueva
  campaña debe usar un runner/state aislado o lanzarse explícitamente mediante SSM.
- El security group limita MLflow a un solo CIDR. El servidor usa HTTP sin autenticación de
  aplicación, por lo que no es apropiado para exposición pública o uso multiusuario persistente.
- El experimento es determinista hasta donde lo permiten las bibliotecas, pero hardware y versiones
  distintas pueden producir variaciones pequeñas. Commit, versiones de Python/sklearn y hash DVC
  quedan registrados para auditarlas.
- Nunca se selecciona un modelo por su resultado en audit; hacerlo invalidaría la estimación final.
