FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
COPY requirements-ai.txt .
RUN pip install --no-cache-dir -r requirements.txt -r requirements-ai.txt

COPY . ./core

CMD ["python", "-m", "core.ai_runtime.model_service"]
