FROM python:3.10-slim

WORKDIR /app

# Copy requirements first (leverage Docker layer caching)
COPY requirements.txt .
COPY requirements-ai.txt .
RUN pip install --no-cache-dir -r requirements.txt -r requirements-ai.txt

# Copy source code
COPY . .

CMD ["python", "strategy/strategic_coordinator.py"]
