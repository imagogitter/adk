#!/bin/bash
set -e

# Create state directory if it doesn't exist
mkdir -p /app/state

# Wait for dependencies to be ready
echo 'Waiting for InfluxDB...'
for i in {1..30}; do
    if curl -s '$INFLUXDB_URL/health' > /dev/null; then
        break
    fi
    sleep 1
done

echo 'Waiting for Prometheus...'
for i in {1..30}; do
    if curl -s 'http://prometheus:9090/-/healthy' > /dev/null; then
        break
    fi
    sleep 1
done

# Start the live trading agent
echo 'Starting live trading agent...'
exec python -m live_agent
