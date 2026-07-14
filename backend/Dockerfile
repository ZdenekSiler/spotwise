FROM python:3.13-slim

# uv for fast, reproducible installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Precompile to .pyc at install time → cheaper cold starts on a low-CPU host.
ENV UV_COMPILE_BYTECODE=1

# Install deps first (layer caching): lockfile + manifest before source.
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY . .

ENV DB_PATH=/data/spotwise.db
EXPOSE 8000

# Single worker: SQLite + a shared-vCPU host — extra workers add write-lock contention, not throughput.
CMD ["uv", "run", "--no-dev", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
