#!/bin/bash

# Ensure secrets directory exists
mkdir -p secrets

# Create example env files if they don't exist
if [ ! -f secrets/.env.binance ]; then
    cat > secrets/.env.binance << EOL
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
EOL
fi

if [ ! -f secrets/.env.gcp ]; then
    cat > secrets/.env.gcp << EOL
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-credentials.json
EOL
fi

# Install dependencies
docker-compose pull

echo "Setup complete. Edit secrets/.env.binance and secrets/.env.gcp with your credentials."
