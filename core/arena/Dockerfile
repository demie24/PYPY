FROM python:3.10-slim

WORKDIR /app

# Copy requirements from root gateway since paho-mqtt and typing is all we need
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

CMD ["python", "arena/arena_coordinator.py"]
