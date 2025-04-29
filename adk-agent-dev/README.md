# ADK Trading Agent

## Overview

A trading agent built with ADK (Autonomous Decision Kit) that uses technical analysis to make trading decisions. The agent monitors cryptocurrency markets through CCXT and stores data in InfluxDB.

## Features

- Real-time market monitoring
- Technical analysis using multiple indicators
- Position management and trade execution
- Comprehensive logging and error handling
- Containerized deployment

## Prerequisites

- Docker and Docker Compose
- Binance US API credentials
- InfluxDB 2.x instance

## Quick Start

1. Copy environment variables template:
```bash
cp .env.example .env
```

2. Edit the .env file with your credentials and settings:
```
INFLUXDB_USERNAME=admin
INFLUXDB_PASSWORD=your_password
INFLUXDB_ORG=your_org
INFLUXDB_BUCKET=trading_data
INFLUXDB_TOKEN=your_token
BINANCEUS_API_KEY=your_key
BINANCEUS_API_SECRET=your_secret
```

3. Build and start the containers:
```bash
docker-compose up -d
```

4. Check the logs:
```bash
docker-compose logs -f trading-agent
```

## Development

### Project Structure
```
.
├── tools/                  # Core trading tools
│   ├── database_tool.py   # InfluxDB interactions
│   └── ccxt_info_tool.py  # Exchange interactions
├── tests/                 # Test suite
├── agent.py              # Main agent implementation
├── Dockerfile            # Container definition
└── docker-compose.yml    # Service orchestration
```

### Running Tests

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest tests/
```

### Configuration

The agent supports the following configuration through environment variables:

- `POSITION_SIZE`: Position size as percentage of capital (default: 0.01)
- `MAX_POSITIONS`: Maximum concurrent positions (default: 2)
- `UPDATE_INTERVAL`: Seconds between updates (default: 3600)

### Trading Strategy

The current implementation uses:
1. Moving average crossovers (SMA 20/50)
2. RSI (14-period)
3. MACD (12/26/9)
4. Bollinger Bands

Buy signals are generated when:
- Price > SMA20 > SMA50
- RSI < 70
- MACD > Signal line

Sell signals are generated when:
- Price < SMA20 < SMA50
- RSI > 30
- MACD < Signal line

## Monitoring

The agent logs all trades and analysis to InfluxDB. You can monitor its activity through:

1. Docker logs:
```bash
docker-compose logs -f trading-agent
```

2. InfluxDB Dashboard:
- Open http://localhost:8086
- Login with your credentials
- Check the "trading_data" bucket

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Security Notes

- Never commit .env files with real credentials
- Use environment variables for sensitive data
- Regularly rotate API keys
- Monitor system logs for unauthorized access
