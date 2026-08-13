FROM public.ecr.aws/lambda/python:3.12

COPY requirements-api.txt ${LAMBDA_TASK_ROOT}/requirements-api.txt
RUN pip install --no-cache-dir --requirement ${LAMBDA_TASK_ROOT}/requirements-api.txt

COPY src/online_shoppers ${LAMBDA_TASK_ROOT}/online_shoppers
COPY models/champion.joblib ${LAMBDA_TASK_ROOT}/models/champion.joblib
COPY models/model_metadata.json ${LAMBDA_TASK_ROOT}/models/model_metadata.json

ENV MODEL_PATH=${LAMBDA_TASK_ROOT}/models/champion.joblib \
    MODEL_METADATA_PATH=${LAMBDA_TASK_ROOT}/models/model_metadata.json

CMD ["online_shoppers.api.lambda_handler.handler"]
