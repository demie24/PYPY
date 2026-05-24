FROM python:3.10-slim

WORKDIR /app

# Copy unified requirements from core
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy simulator files
COPY . .

CMD ["python", "digital_twin/main.py"]
