FROM python:3.13-slim

WORKDIR /app

# Install common dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set Python to not write bytecode and not buffer output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/bash -m appuser

# Set the working directory permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser
