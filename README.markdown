# Autonomous Trading Platform

A robust, ADK-based autonomous trading system for Binance.us, leveraging InfluxDB, ccxt, pandas-ta, Google ADK, Optuna, Backtrader, Dash, Docker Compose, and a Flask/FastAPI internal API for control.

## Overview

This project aims to develop, test, and deploy an autonomous trading platform capable of fetching market data, computing technical indicators, making trading decisions using Google ADK agents, backtesting strategies, and executing live trades with a user-friendly Dash web interface.

## Technologies

- **Database:** InfluxDB v2/v3
- **Exchange Interaction:** ccxt
- **Feature Engineering:** pandas-ta
- **Agent Logic:** Google Agent Development Kit (ADK)
- **Hyperparameter Optimization:** Optuna
- **Backtesting:** Backtrader
- **Web UI:** Dash
- **API:** Flask/FastAPI (internal control)
- **Orchestration:** Docker Compose
- **Secrets:** `.env` files

## Project Structure

- `/data-pipeline`: Scripts for fetching and storing market data.
- `/feature-eng`: Feature engineering with pandas-ta.
- `/adk-agent-dev`: Development of ADK agent and tools.
- `/backtester`: Backtesting with Backtrader.
- `/adk-live-agent`: Live trading agent with execution tools.
- `/web-ui`: Dash-based web interface.
- `/docker`: Docker Compose configurations.
- `/secrets`: Environment variable files (not tracked).
- `/scripts`: Utility scripts.

## Getting Started

1. **Prerequisites:**
   - Docker and Docker Compose
   - Python 3.11
   - (Optional) NVIDIA drivers and `nvidia-container-toolkit` for GPU support
   - Google Cloud SDK (for ADK)

2. **Setup:**
   ```bash
   git clone <repository-url>
   cd autonomous-trading-platform
   cp secrets/.env.example secrets/.env.binance
   cp secrets/.env.gcp.example secrets/.env.gcp
   # Edit .env files with your credentials
   ./scripts/setup.sh
   ```

3. **Run Development Environment:**
   ```bash
   docker-compose up --build
   ```

4. **Access Web UI:**
   - Open `http://localhost:8050` in your browser.

## Development Phases

See the detailed plan in the project documentation or the original plan for phase-by-phase instructions.

## Contributing

- Follow PEP 8 and use type hints.
- Write clear docstrings.
- Commit changes to feature branches and submit pull requests.

## License

MIT License
