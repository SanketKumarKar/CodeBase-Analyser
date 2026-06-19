# ==============================================================================
# Backend Dockerfile — Python 3.12 slim
# Tree-sitter compiles on Linux so JS/TS parsing works correctly.
# ==============================================================================

FROM python:3.12-slim AS base

# System deps: git (for repo cloning), curl (healthcheck), build tools (tree-sitter)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies (separate layer for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create temp dir for repo cloning
RUN mkdir -p /tmp/repos

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /tmp/repos
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:socket_app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
