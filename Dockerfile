FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy all source files first (needed for editable install)
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install -e .[dev]

# Copy remaining files
COPY tests/ ./tests/

# Create directories for volumes
RUN mkdir -p /app/cache /app/output

# Set entrypoint
ENTRYPOINT ["wheel-backtest"]
CMD ["--help"]
