FROM python:3.10-slim

WORKDIR /app

# Copy and install requirements
COPY core/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY core/ai_detection /app/ai_detection
COPY core/shared /app/shared 2>/dev/null || true

# Run application
CMD ["python", "ai_detection/detector.py"]
