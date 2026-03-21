# Crypto Backtesting Engine

Welcome to the Crypto Backtesting Engine! This project provides a robust, local framework for testing cryptocurrency trading strategies against historical market data from Binance.

## Overview
Before deploying a trading bot with real capital, traders use **backtesting** to simulate how a specific set of rules (a "strategy") would have performed in the past. This engine downloads historical data, applies your trading rules precisely step-by-step, and outputs a detailed performance report.

## Key Concepts

### What is OHLCV?
When looking at financial charts, time is broken down into periods (e.g., 1 hour, 1 day) represented by "candles". **OHLCV** stands for:
- **O (Open):** The price at the exact start of the time period.
- **H (High):** The highest price reached during the period.
- **L (Low):** The lowest price during the period.
- **C (Close):** The final price at the exact end of the period.
- **V (Volume):** The total amount of the asset traded during that time.

This format gives our engine everything it needs to accurately simulate whether a trade would have hit a target profit or a stop-loss during that specific hour or day.

### Indicators
We use a library called `pandas-ta` to calculate mathematical indicators based on the OHLCV prices:
- **EMA (Exponential Moving Average):** Shows the average price over a set number of candles, giving more weight to recent prices. Used to detect trends.
- **RSI (Relative Strength Index):** Measures how fast prices are changing to see if an asset is "overbought" (due for a drop) or "oversold" (due for a bounce).
- **ATR (Average True Range):** Measures market volatility. We use this to dynamically set our Stop Loss and Take Profit distances.

## Project Structure
- **`data.py` (Data Layer):** Connects to the Binance API to fetch historical OHLCV data. It caches this data in a local SQLite database (`crypto_backtest.db`) so we don't abusively ping Binance's servers while testing. It also calculates the indicators mentioned above.
- **`backtest.py` (Simulation Engine):** Contains the actual trading strategies. It walks through the data candle-by-candle, entering and exiting simulated trades, calculating fees, and evaluating metrics like Win Rate and Net Profit.
- **`app.py` (Dashboard - *Upcoming*):** A visual web interface built with Streamlit to easily configure backtests and view interactive charts.

## Installation & Usage

1. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Test the Data Layer (Fetch & Cache):**
   ```bash
   python data.py
   ```

3. **Run the Backtesting Simulation:**
   ```bash
   python backtest.py
   ```
