FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements-api.txt ./requirements-api.txt
RUN pip install --no-cache-dir --requirement requirements-api.txt
COPY src/online_shoppers ./online_shoppers
COPY models/champion.joblib ./models/champion.joblib
COPY models/model_metadata.json ./models/model_metadata.json

EXPOSE 8000
CMD ["uvicorn", "online_shoppers.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
