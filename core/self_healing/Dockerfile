FROM python:3.10-slim

WORKDIR /app

# Copy unified requirements from core
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

CMD ["python", "self_healing/main.py"]
