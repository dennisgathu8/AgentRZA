# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage 2: Runtime Environment
FROM python:3.12-slim AS runtime

# Create non-root user for security (Zero-Trust Principle: Least Privilege)
RUN useradd -m -s /bin/bash xg-agent

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /home/xg-agent/.local
ENV PATH=/home/xg-agent/.local/bin:$PATH

# Copy application code
COPY --chown=xg-agent:xg-agent . .

# Create necessary directories and ensure correct permissions
RUN mkdir -p data/db logs data/raw \
    && chown -R xg-agent:xg-agent /app

USER xg-agent

# Set python path
ENV PYTHONPATH=/app

# Default command (overridden by docker-compose)
CMD ["python", "main.py", "--date", "today"]
