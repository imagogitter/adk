FROM python:3.9-slim

WORKDIR /app

# Copy only requirements first for better caching
COPY adk-live-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY utils /app/utils

# Copy live agent code
COPY adk-live-agent /app/adk-live-agent

# Copy .env file if it exists
COPY .env* /app/

# Set working directory to adk-live-agent
WORKDIR /app/adk-live-agent

CMD ["python", "main.py"]
