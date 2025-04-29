FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY tools/ tools/
COPY agent.py .
COPY .env .

# Set Python environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=2

CMD ["python", "agent.py"]