# GEMINI.md — Crypto Backtesting Engine + Streamlit Dashboard

## Project Overview

A crypto backtesting framework where the user selects a symbol, strategy, and timeframe — runs it on historical OHLCV data from Binance — and gets a full performance report visualised in a Streamlit dashboard.

**Owner background:** Python + SQL developer, has done basic financial data analysis, has ML experience (non-finance). Uses AI to help build.

**Total budget:** ~15–18 hours across 4 weeks.

**Phase 1 goal:** Working local app + clean GitHub repo with README.
**Phase 2 (later):** Deploy via Streamlit Community Cloud (free, connects to GitHub).

---

## Tech Stack

| Layer | Tool | Notes |
|---|---|---|
| Language | Python 3.10+ | Primary language |
| Data source | Binance public REST API | No API key needed for OHLCV |
| Storage | CSV or SQLite | SQLite preferred (good SQL practice) |
| Indicators | pandas-ta or ta-lib | pandas-ta is easier to install |
| Backtesting logic | Custom (no framework) | Build from scratch — that's the point |
| Dashboard | Streamlit | Simple, Python-native |
| Charts | Plotly | Works natively in Streamlit |
| Versioning | GitHub | README + screenshots |

---

## Project Structure

```
crypto-backtester/
├── data.py            # Binance fetch + indicator computation
├── backtest.py        # Strategy logic + trade simulation + metrics
├── app.py             # Streamlit UI
├── requirements.txt
└── README.md
```

Do not over-engineer. One file per layer. No classes unless they genuinely simplify things.

---

## Week-by-Week Plan

### Week 1 — Data Layer (~3–4 hrs)
**File:** `data.py`

Goals:
- Fetch OHLCV candles from Binance public REST API
- Support configurable symbol (e.g. BTCUSDT) and interval (e.g. 15m, 1h, 1d)
- Store result to SQLite or CSV for reuse (avoid re-fetching)
- Compute indicators on top of the OHLCV DataFrame:
  - EMA20, EMA50 (for trend following)
  - RSI 14 (for mean reversion)
  - ATR 14 (for SL/TP sizing)

Binance endpoint (no key needed):
```
GET https://api.binance.com/api/v3/klines
Params: symbol=BTCUSDT, interval=1h, limit=500
Returns: [open_time, open, high, low, close, volume, ...]
```

Deliverable: `get_ohlcv(symbol, interval, limit)` returns a clean pandas DataFrame with OHLCV + indicators.

---

### Week 2 — Backtesting Engine (~5–6 hrs)
**File:** `backtest.py`

Goals:
- Implement 2–3 strategies as separate functions
- Simulate trades: entry → SL/TP → close
- Compute performance metrics

**Strategies to implement:**

| Strategy | Entry Signal | Exit |
|---|---|---|
| EMA Crossover | EMA20 crosses above EMA50 = LONG; crosses below = SHORT | SL/TP |
| RSI Mean Reversion | RSI < 30 = LONG; RSI > 70 = SHORT | SL/TP |
| Combined | EMA signal + RSI confirmation required | SL/TP |

**SL/TP rules (mirrors PRD):**
- SL = 1.5 × ATR below entry
- TP = 3.0 × ATR above entry
- Risk:Reward = 1:2

**Trade simulation logic:**
1. Iterate candle by candle (no look-ahead)
2. On signal: record entry price, direction, SL price, TP price
3. On subsequent candles: check if low hit SL or high hit TP
4. Close trade, record PnL
5. Only one open position at a time (no pyramiding)

**Metrics to compute:**

| Metric | Formula |
|---|---|
| Win Rate | winning_trades / total_trades |
| Profit Factor | sum(wins) / abs(sum(losses)) |
| Sharpe Ratio | mean(daily_returns) / std(daily_returns) * sqrt(252) |
| Max Drawdown | max peak-to-trough drop in equity curve |
| Total Trades | count of closed trades |

Deliverable: `run_backtest(df, strategy)` returns:
- `trades_df` — one row per trade (entry, exit, direction, pnl, result)
- `metrics` — dict with Win Rate, Profit Factor, Sharpe, Max Drawdown, Total Trades
- `equity_curve` — Series of cumulative PnL over time

---

### Week 3 — Streamlit Dashboard (~4–5 hrs)
**File:** `app.py`

**Page 1 — Backtest Runner**
- Sidebar inputs: symbol, interval, strategy, date range
- On run: call `get_ohlcv()` → `run_backtest()` → display results
- Show: metrics table, equity curve (Plotly line chart), candlestick chart with entry/exit markers

**Page 2 — Trades Log**
- Table of all trades from the backtest
- Columns: date, symbol, direction, entry, exit, SL, TP, PnL, result (WIN/LOSS)
- Colour-coded rows (green = win, red = loss)

**Page 3 — Live Prices**
- Poll Binance `/api/v3/ticker/price` (no key needed) for a list of symbols
- Show current price + EMA/RSI values computed from latest candles
- Simple signal label: LONG / SHORT / NEUTRAL based on EMA crossover state
- Auto-refresh via `st.rerun()` with a sleep interval

Deliverable: `streamlit run app.py` shows the full app locally.

---

### Week 4 — Polish + GitHub (~3 hrs)

- Clean up code, add docstrings to all functions
- `requirements.txt` with pinned versions
- `README.md` with:
  - Project description (1 paragraph)
  - Screenshot of the dashboard
  - How to install and run
  - Sample backtest results (table + equity curve image)
  - Explanation of each strategy
- Optional stretch: compare BTC vs ETH results side by side in the dashboard

---

## Performance Metrics Reference

These mirror the PRD's backtesting validation criteria:

| Metric | Minimum acceptable (PRD reference) | What it means |
|---|---|---|
| Win Rate | ≥ 50% | More winning trades than losing |
| Profit Factor | ≥ 1.2 | Gross profit / gross loss |
| Sharpe Ratio | > 1.0 | Good risk-adjusted return |
| Max Drawdown | < 20% | Worst equity decline from peak |

If a strategy fails these thresholds during backtest, it should be flagged as "not viable" — consistent with how the PRD's bot validates before going live.

---

## Key Coding Rules

- **No look-ahead bias** — when iterating candles, never use future data to make a past decision. Shift signals by 1 candle before acting.
- **One position at a time** — do not open a new trade if one is already open.
- **Fees** — include a 0.1% fee per side (0.2% round-trip) in PnL calculations to be realistic.
- **Vectorised where possible** — use pandas operations over row-by-row loops for indicator computation. Only loop for trade simulation.
- **No hardcoded symbols** — everything should be parameterised.
- **Reproducible** — same inputs should always produce same outputs. No randomness unless seeded.

---

## Binance API Reference (Free, No Auth)

All endpoints below work without an API key.

```
# Historical OHLCV
GET https://api.binance.com/api/v3/klines
Params: symbol (e.g. BTCUSDT), interval (1m/5m/15m/1h/4h/1d), limit (max 1000)

# Current price (all symbols)
GET https://api.binance.com/api/v3/ticker/price

# 24hr stats
GET https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT
```

Rate limits (free, unauthenticated): 1200 requests/minute — more than enough for this project.

Suggested symbols to support: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT

---

## Future Phases (Do Not Build Now)

These are noted so Gemini understands the direction — do not implement unless explicitly asked.

- **Phase 2:** Deploy to Streamlit Community Cloud (free, GitHub-connected)
- **Phase 3:** Add ML signal layer — train a simple classifier (logistic regression or LSTM) on the same features, compare signal quality vs rule-based strategies
- **Phase 4:** Add RL agent (Q-learning) to learn position sizing or entry timing
- **Phase 5:** Add risk manager module — correlation filter, dynamic position sizing, portfolio-level drawdown circuit breaker
- **Phase 6:** Live paper trading mode — poll prices in real-time, apply strategy, log simulated trades

---

## Context: Original PRD Summary

The PRD this project is stepping toward is an AI-powered crypto futures trading bot with:
- LSTM + Transformer ensemble for price prediction
- Q-Learning RL agent (5184 state space, 3 actions: LONG/SHORT/WAIT)
- Multi-strategy voting system (EMA trend 30%, RSI mean reversion 20%, whale trap 30%, scalper 20%)
- 7-layer trade filter (confidence score, market regime, whale trap, smart money, correlation, max risk)
- Dynamic risk sizing based on ATR and market regime
- WebSocket real-time price feed
- Flask dashboard with mobile UI
- Telegram notifications
- Circuit breaker at 20% drawdown

This project (backtesting engine) covers the strategy validation and metrics layer — roughly 35–40% of the full PRD. It establishes the foundation that all future phases build on.
