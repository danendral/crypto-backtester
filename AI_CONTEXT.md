# Crypto Backtester - AI Context & Hand-off

This file serves as a memory checkpoint for the AI acting as the developer on the `crypto-backtester` project.

## Current Project Status: End of Week 2

We have successfully built the **Data Layer** and the **Backtesting Engine** which constitute Week 1 and Week 2 of the `GEMINI.md` roadmap. 

### What is Completed:
1. **`requirements.txt`**: Added `pandas`, `requests`, `pandas-ta`, and `plotly`.
2. **`data.py` (Week 1)**:
   - Fetches OHLCV data using the unrestricted `https://data-api.binance.vision/api/v3/klines` endpoint (bypassing region blocks).
   - Utilizes a local SQLite database (`crypto_backtest.db`) to cache data seamlessly, minimizing network fetch delays.
   - Calculates requisite technical indicators `EMA_20`, `EMA_50`, `RSI_14`, and `ATRr_14` automatically upon pulling data.
3. **`backtest.py` (Week 2)**:
   - Contains binary strategy trigger generators for generic crossover logic without lookahead bias.
   - `run_backtest()` houses a strict candle-by-candle simulation loop tracking Entry logic versus Exit logic on identical candles to ensure accurate SL/TP triggers.
   - Outputs robust analysis parameters strictly adhering to the PRD: Win Rate, Profit Factor, Sharpe Ratio, and Max Drawdown.
4. **Git Repository Setup**:
   - Master branch pushed to `git@github.com:danendral/crypto-backtester.git`.
   - `.gitignore` configured properly to exclude cache and DB artifacts.

## Next Target: Week 3 (Streamlit Dashboard)

When beginning a new session, the AI should immediately look toward the **Week 3** deliverables specified in `GEMINI.md`. This will involve creating an `app.py` script bridging `data.py` and `backtest.py` onto a local web application utilizing Streamlit components and Plotly graphing features.
