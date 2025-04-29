FROM python:3.9-slim

WORKDIR /app

# Install git
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY backtester/requirements.txt .
RUN pip install -r requirements.txt

# Copy shared utilities
COPY utils /app/utils

# Copy backtester code
COPY backtester /app/backtester

# Copy .env file if it exists
COPY .env* /app/

# Set working directory to backtester
WORKDIR /app/backtester

CMD ["python", "run_backtest.py"]
