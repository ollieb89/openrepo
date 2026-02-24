FROM python:3.13-slim-bookworm

WORKDIR /app

# Install build dependencies:
# - libpq-dev: for psycopg3 binary
# - build-essential + libc6-dev: C stdlib headers needed by Rust/maturin linker
# - curl: to download rustup
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    libc6-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain (required by memu-py which uses maturin/pyo3)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY memory_service/ ./memory_service/

EXPOSE 18791

CMD ["uvicorn", "memory_service.main:app", "--host", "0.0.0.0", "--port", "18791", "--workers", "1"]
