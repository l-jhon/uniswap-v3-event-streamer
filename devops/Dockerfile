# syntax=docker/dockerfile:1

FROM --platform=linux/amd64 python:3.12-slim

ENV APP_DIR=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/var/cache/uv

WORKDIR $APP_DIR

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    librdkafka-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv and use it to install dependencies
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

# Create and activate venv, then sync dependencies
RUN uv venv && \
    . .venv/bin/activate && \
    uv sync --frozen

# Copy project code
COPY src/ ./src/
COPY main.py ./

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app $APP_DIR

USER app

# Activate the venv by default
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Final command
CMD ["python", "main.py"]
