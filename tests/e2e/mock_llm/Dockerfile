FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir flask

COPY server.py /app/

EXPOSE 8080

CMD ["python", "server.py"]
