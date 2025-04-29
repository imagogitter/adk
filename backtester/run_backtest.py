"""Main script for running backtests with ADK strategy."""
import os
import sys
from datetime import datetime, timedelta, timezone

import backtrader as bt
import quantstats as qs
import pandas as pd
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import get_config

from influx_feed import InfluxDBData
from adk_strategy import ADKStrategy, BacktestCommissionScheme


def get_bt_timeframe(timeframe_str: str) -> tuple:
    """Convert string timeframe to backtrader constants."""
    timeframe_map = {
        '1m': bt.TimeFrame.Minutes,
        '5m': bt.TimeFrame.Minutes,
        '15m': bt.TimeFrame.Minutes,
        '30m': bt.TimeFrame.Minutes,
        '1h': bt.TimeFrame.Minutes,
        '4h': bt.TimeFrame.Minutes,
        '1d': bt.TimeFrame.Days,
        '1w': bt.TimeFrame.Weeks,
    }
    
    compression_map = {
        '1m': 1,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '1h': 60,
        '4h': 240,
        '1d': 1,
        '1w': 1,
    }
    
    if timeframe_str not in timeframe_map:
        raise ValueError(f"Unsupported timeframe: {timeframe_str}")
        
    return timeframe_map[timeframe_str], compression_map[timeframe_str]


def run_backtest(
    symbol: str,
    initial_cash: float = None,
    timeframe: str = "1h",
    start_date: datetime = None,
    end_date: datetime = None,
) -> dict:
    """Run backtest for a single symbol."""
    # Create reports directory
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    # Load configuration
    config = get_config()
    
    # Use provided values or defaults from config
    initial_cash = initial_cash or float(config['trading']['initial_capital'])
    
    # Use the actual data range from our InfluxDB
    if start_date is None:
        start_date = datetime(2025, 1, 28, tzinfo=timezone.utc)
    if end_date is None:
        end_date = datetime(2025, 4, 28, tzinfo=timezone.utc)
    
    # Initialize Backtrader cerebro engine
    cerebro = bt.Cerebro()
    
    # Get backtrader timeframe constants
    tf, comp = get_bt_timeframe(timeframe)
    
    # Set up InfluxDB data feed
    data = InfluxDBData(
        bucket=config['influxdb']['bucket'],
        org=config['influxdb']['org'],
        url=config['influxdb']['url'],
        token=config['influxdb']['token'],
        symbol=symbol,
        timeframe=timeframe,
        fromdate=start_date,
        todate=end_date,
    )
    
    # Add data feed to cerebro
    cerebro.adddata(data, name=symbol)
    
    # Add strategy with debug mode enabled
    cerebro.addstrategy(ADKStrategy,
        position_size=float(config['trading']['position_size']),
        max_positions=int(config['trading']['max_positions']),
        timeframe=timeframe,
        debug=True  # Enable debug output
    )
    
    # Set up broker with commission
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.addcommissioninfo(BacktestCommissionScheme())
    
    # Add analyzers with proper timeframe values
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=tf, compression=comp)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns", timeframe=tf, compression=comp)
    
    # Run backtest
    print(f"\nRunning backtest for {symbol}...")
    print(f"Initial cash: ${initial_cash:,.2f}")
    print(f"Date range: {start_date.isoformat()} to {end_date.isoformat()}")
    
    results = cerebro.run()
    strat = results[0]
    
    # Get analyzer results with safe defaults
    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    returns_analysis = strat.analyzers.returns.get_analysis()
    
    # Extract metrics with safe handling of None values
    metrics = {
        "symbol": symbol,
        "timeframe": timeframe,
        "initial_cash": initial_cash,
        "final_value": cerebro.broker.getvalue(),
        "return_pct": (
            (cerebro.broker.getvalue() - initial_cash) / initial_cash * 100
        ),
        "sharpe_ratio": sharpe_analysis.get('sharperatio', 0.0),
        "max_drawdown_pct": drawdown_analysis.get('max', {}).get('drawdown', 0.0),
        "trade_count": len(strat.trades),
        "trade_metrics": strat.analyzers.trades.get_analysis(),
    }
    
    # Generate quantstats report
    portfolio_returns = returns_analysis
    
    # Filter and convert timestamps, excluding non-numeric keys
    returns_data = [
        (k, v) for k, v in portfolio_returns.items()
        if isinstance(k, (int, float)) or (isinstance(k, str) and k.isdigit())
    ]
    
    if returns_data:
        returns_series = pd.Series(
            [v for _, v in returns_data],
            index=[pd.Timestamp.fromtimestamp(float(k)) for k, _ in returns_data]
        )
        
        report_path = os.path.join(reports_dir, f"{symbol.replace('/', '_')}_{timeframe}_report.html")
        qs.reports.html(
            returns=returns_series,
            output=report_path,
            title=f"ADK Strategy Backtest - {symbol} {timeframe}"
        )
        print(f"\nDetailed report saved to: {report_path}")
    
    # Print summary
    print("\nBacktest Results:")
    print(f"Final Portfolio Value: ${metrics['final_value']:,.2f}")
    print(f"Return: {metrics['return_pct']:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"Number of Trades: {metrics['trade_count']}")
    
    return metrics


if __name__ == "__main__":
    # Load configuration
    config = get_config()
    
    # Default test parameters with 2025 dates
    symbols = ["BTC/USDT", "ETH/USDT"]
    timeframes = ["1h", "4h"]
    start_date = datetime(2025, 1, 28, tzinfo=timezone.utc)
    end_date = datetime(2025, 4, 28, tzinfo=timezone.utc)
    
    # Store results for all combinations
    all_results = []
    
    # Create reports directory
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    for symbol in symbols:
        for timeframe in timeframes:
            try:
                metrics = run_backtest(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date
                )
                all_results.append(metrics)
            except Exception as e:
                print(f"Error testing {symbol} {timeframe}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
    
    # Save combined results
    if all_results:
        results_df = pd.DataFrame(all_results)
        results_df.to_csv(os.path.join(reports_dir, "backtest_results.csv"), index=False)
        print("\nCombined results saved to: reports/backtest_results.csv")