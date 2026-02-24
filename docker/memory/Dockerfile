FROM python:3.13-slim-bookworm

WORKDIR /app

# Install build dependencies for psycopg binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY memory_service/ ./memory_service/

EXPOSE 18791

CMD ["uvicorn", "memory_service.main:app", "--host", "0.0.0.0", "--port", "18791", "--workers", "1"]
