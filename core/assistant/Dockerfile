FROM python:3.10-slim

WORKDIR /app

# Copy unified requirements from core
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code to /app/core
COPY . ./core

RUN mkdir -p /app/logs

ENV PYTHONPATH=/app

CMD ["python", "-m", "core.assistant.assistant_daemon"]
