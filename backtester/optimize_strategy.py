"""Hyperparameter optimization script using Optuna."""
import os
import sys
from datetime import datetime, timezone
import json
import logging

import optuna
from optuna.trial import Trial
import backtrader as bt
from dotenv import load_dotenv

from run_backtest import run_backtest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def objective(trial: Trial) -> float:
    """Optuna objective function for optimizing strategy parameters."""
    # Parameter space
    params = {
        'rsi_period': trial.suggest_int('rsi_period', 10, 30),
        'rsi_overbought': trial.suggest_int('rsi_overbought', 60, 80),
        'rsi_oversold': trial.suggest_int('rsi_oversold', 20, 40),
        'sma_period': trial.suggest_int('sma_period', 20, 200),
        'atr_period': trial.suggest_int('atr_period', 10, 30),
        'risk_pct': trial.suggest_float('risk_pct', 0.01, 0.03),
        'trail_pct': trial.suggest_float('trail_pct', 0.01, 0.04),
        'position_size': trial.suggest_float('position_size', 0.01, 0.05),
        'max_positions': trial.suggest_int('max_positions', 1, 3)
    }
    
    try:
        # Run backtest with trial parameters
        metrics = run_backtest(
            symbol="BTC/USDT",  # Primary optimization on BTC
            timeframe="1h",     # Primary timeframe
            initial_cash=10000,
            start_date=datetime(2025, 1, 28, tzinfo=timezone.utc),
            end_date=datetime(2025, 4, 28, tzinfo=timezone.utc),
            strategy_params=params
        )
        
        # Calculate objective value (can be adjusted based on preferences)
        sharpe_ratio = metrics['sharpe_ratio']
        return_pct = metrics['return_pct']
        max_dd = abs(metrics['max_drawdown_pct'])
        
        # Penalize strategies with too few trades
        if metrics['trade_count'] < 10:
            return float('-inf')
        
        # Custom objective: balance Sharpe ratio and returns while considering drawdown
        objective_value = (sharpe_ratio * 0.4) + (return_pct * 0.4) - (max_dd * 0.2)
        
        # Store additional metrics for analysis
        trial.set_user_attr('return_pct', return_pct)
        trial.set_user_attr('sharpe_ratio', sharpe_ratio)
        trial.set_user_attr('max_drawdown', max_dd)
        trial.set_user_attr('trade_count', metrics['trade_count'])
        
        return objective_value
        
    except Exception as e:
        logger.error(f"Trial failed: {e}")
        return float('-inf')

def run_optimization(n_trials: int = 100) -> None:
    """Run the optimization study."""
    load_dotenv()
    
    # Create study
    study = optuna.create_study(
        direction='maximize',
        pruner=optuna.pruners.MedianPruner(),
        sampler=optuna.samplers.TPESampler(seed=42)
    )
    
    # Run optimization
    logger.info(f"Starting optimization with {n_trials} trials...")
    study.optimize(objective, n_trials=n_trials)
    
    # Get best trial and parameters
    best_trial = study.best_trial
    best_params = best_trial.params
    
    # Print optimization results
    logger.info("\nOptimization Results:")
    logger.info(f"Best objective value: {best_trial.value:.4f}")
    logger.info("\nBest parameters:")
    for param, value in best_params.items():
        logger.info(f"{param}: {value}")
    
    # Print additional metrics
    logger.info("\nBest trial metrics:")
    logger.info(f"Return: {best_trial.user_attrs['return_pct']:.2f}%")
    logger.info(f"Sharpe Ratio: {best_trial.user_attrs['sharpe_ratio']:.2f}")
    logger.info(f"Max Drawdown: {best_trial.user_attrs['max_drawdown']:.2f}%")
    logger.info(f"Trade Count: {best_trial.user_attrs['trade_count']}")
    
    # Save best parameters
    params_file = "reports/best_parameters.json"
    os.makedirs("reports", exist_ok=True)
    with open(params_file, 'w') as f:
        json.dump(best_params, f, indent=4)
    logger.info(f"\nBest parameters saved to: {params_file}")
    
    # Create optimization history plot
    try:
        optimization_history_plot = optuna.visualization.plot_optimization_history(study)
        optimization_history_plot.write_html("reports/optimization_history.html")
        logger.info("Optimization history plot saved to: reports/optimization_history.html")
    except Exception as e:
        logger.error(f"Failed to create optimization plot: {e}")

if __name__ == "__main__":
    run_optimization(n_trials=int(os.getenv("OPTUNA_TRIALS", "100")))