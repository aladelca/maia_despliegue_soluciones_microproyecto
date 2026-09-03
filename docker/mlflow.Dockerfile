FROM ghcr.io/mlflow/mlflow:v3.15.1

RUN pip install --no-cache-dir boto3==1.42.62

ENTRYPOINT ["mlflow"]
