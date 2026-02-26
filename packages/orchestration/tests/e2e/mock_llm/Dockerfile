FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask curl

# Copy server code
COPY server.py /app/

# Create responses directory
RUN mkdir -p /app/responses

# Expose port
EXPOSE 8080

# Run server
CMD ["python", "server.py"]
