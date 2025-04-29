FROM python:3.9-slim

WORKDIR /app

# Copy only requirements first for better caching
COPY web-ui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY utils /app/utils

# Copy web-ui code
COPY web-ui /app/web-ui

# Copy .env file if it exists
COPY .env* /app/

# Set working directory to web-ui
WORKDIR /app/web-ui

EXPOSE 8050

CMD ["python", "app.py"]