FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for scipy/numba/gfortran compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    liblapack-dev \
    libblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy unified requirements from core
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy simulator files
COPY . .

CMD ["python", "digital_twin/main.py"]

