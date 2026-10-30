# ==============================================================================
# Dockerfile for YottaFlex AI Learning Recommendation Web Application
# ==============================================================================
FROM python:3.12-slim

# Prevent Python from writing .pyc files & buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and schema
COPY . .

# Pre-generate small baseline database so the container is ready immediately
RUN python scripts/generate_data.py --scale small --export-all

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start production ASGI web server
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
