import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
import os
import re
from data import get_ohlcv, fetch_binance_ohlcv
from backtest import run_backtest, strategy_ema_crossover, strategy_rsi_mean_reversion, strategy_combined

st.set_page_config(page_title="Crypto Backtester", layout="wide", page_icon="📈")

STRATEGIES = {
    "EMA Crossover": strategy_ema_crossover,
    "RSI Mean Reversion": strategy_rsi_mean_reversion,
    "Combined (EMA + RSI)": strategy_combined
}

st.sidebar.title("Navigation")
page = st.sidebar.radio("Select Page", ["Backtest Runner", "Trades Log", "Live Market Pulse", "AI Strategy Builder"])

# API Key config
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("Anthropic API Key", type="password", help="Required for AI Strategy Builder")

if page == "Backtest Runner":
    st.title("Backtest Runner")
    st.markdown("Test your algorithms against historical data.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        symbol = st.selectbox("Symbol", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"])
    with col2:
        interval = st.selectbox("Interval", ["1h", "4h", "1d"])
    with col3:
        strategy_name = st.selectbox("Strategy", list(STRATEGIES.keys()))
        
    limit = st.slider("Lookback Candles (Limit)", min_value=100, max_value=5000, value=1000, step=100)
    
    if st.button("Run Simulation"):
        with st.spinner(f"Fetching {limit} candles for {symbol}..."):
            df = get_ohlcv(symbol, interval, limit)
            
        with st.spinner("Simulating trades..."):
            strategy_func = STRATEGIES[strategy_name]
            trades_df, metrics, equity_curve = run_backtest(df, strategy_func)
            
            st.session_state['trades_df'] = trades_df # Save for trades log
            
            st.subheader("Performance Metrics")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Trades", metrics['Total Trades'])
            m2.metric("Win Rate", f"{metrics['Win Rate']:.2%}")
            m3.metric("Profit Factor", f"{metrics['Profit Factor']:.2f}")
            m4.metric("Sharpe Ratio", f"{metrics['Sharpe Ratio']:.2f}")
            m5.metric("Max Drawdown", f"{metrics['Max Drawdown']:.2%}")
            
            st.subheader("Equity Curve")
            fig = px.line(equity_curve, title=f"Equity Curve: {strategy_name} on {symbol} ({interval})")
            fig.update_layout(xaxis_title="Time", yaxis_title="Account Balance ($)", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

elif page == "Trades Log":
    st.title("Trades Log")
    st.markdown("Detailed breakdown of all executed positions from the latest simulation.")
    
    if 'trades_df' in st.session_state and not st.session_state['trades_df'].empty:
        df = st.session_state['trades_df']
        
        def highlight_pnl(val):
            color = 'lightgreen' if val == 'WIN' else 'lightcoral'
            return f'background-color: {color}; color: black'
            
        # handle compatibility between pandas versions
        if hasattr(df.style, 'map'):
            styled_df = df.style.map(highlight_pnl, subset=['result'])
        else:
            styled_df = df.style.applymap(highlight_pnl, subset=['result'])
            
        st.dataframe(styled_df, use_container_width=True)
    elif 'trades_df' in st.session_state and st.session_state['trades_df'].empty:
        st.warning("No trades were executed in this dataset.")
    else:
        st.info("No trades to display! Go to the 'Backtest Runner' to run a simulation first.")

elif page == "Live Market Pulse":
    st.title("Live Market Pulse")
    st.markdown("Real-time indicator tracking for active symbols.")
    
    symbol = st.selectbox("Market Symbol", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"])
    
    if st.button("Refresh Now"):
        st.rerun()
        
    with st.spinner("Connecting to Binance Data Vision API..."):
        # Fetch latest 100 1-hour candles bypassing local cache strictly for live feed
        df = fetch_binance_ohlcv(symbol, "1h", limit=100)
        
        # Calculate indicators
        df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        delta = df['close'].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        df['RSI_14'] = 100 - (100 / (1 + gain / loss))
        
        latest_candle = df.iloc[-1]
        current_price = latest_candle['close']
        
        ema20 = latest_candle['EMA_20'] if not pd.isna(latest_candle['EMA_20']) else 0.0
        ema50 = latest_candle['EMA_50'] if not pd.isna(latest_candle['EMA_50']) else 0.0
        rsi = latest_candle['RSI_14'] if not pd.isna(latest_candle['RSI_14']) else 0.0
        
        st.metric(f"Current {symbol} Price", f"${current_price:,.2f}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("EMA 20", f"${ema20:,.2f}")
        col2.metric("EMA 50", f"${ema50:,.2f}")
        col3.metric("RSI (14)", f"{rsi:.1f}")
        
        st.subheader("Current Market Regime:")
        if ema20 > ema50:
            st.success("🟢 BULL TREND (EMA 20 > EMA 50)")
        elif ema20 < ema50:
            st.error("🔴 BEAR TREND (EMA 20 < EMA 50)")
        else:
            st.warning("⚪ NEUTRAL")

elif page == "AI Strategy Builder":
    st.title("AI Strategy Builder")
    st.markdown("Describe a trading strategy in plain English and let AI generate the code for you.")

    if not api_key:
        st.warning("Please enter your Anthropic API Key in the sidebar to use this feature.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    with col1:
        ai_symbol = st.selectbox("Symbol", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"], key="ai_symbol")
    with col2:
        ai_interval = st.selectbox("Interval", ["1h", "4h", "1d"], key="ai_interval")
    with col3:
        ai_limit = st.slider("Lookback Candles", min_value=100, max_value=5000, value=1000, step=100, key="ai_limit")

    user_description = st.text_area(
        "Describe your strategy",
        placeholder="e.g. Go long when RSI drops below 25 and EMA 20 is above EMA 50. Go short when RSI rises above 75 and EMA 20 is below EMA 50.",
        height=120
    )

    SYSTEM_PROMPT = """You are a quantitative trading strategy code generator. You write Python functions for a crypto backtesting engine.

The input DataFrame has these columns: timestamp, open, high, low, close, volume, EMA_20, EMA_50, RSI_14, ATRr_14

You must return a function with this exact signature:
    def ai_strategy(df):
        # your logic
        return df

The function must:
- Accept a pandas DataFrame and return it with a new 'signal' column
- signal = 1 means LONG entry, signal = -1 means SHORT entry, signal = 0 means no action
- Use df = df.copy() at the start
- Only use pandas (as pd) and numpy (as np) — no imports allowed

Here are two example strategies for reference:

def strategy_ema_crossover(df):
    df = df.copy()
    df['ema_trend'] = np.where(df['EMA_20'] > df['EMA_50'], 1, -1)
    df['signal'] = 0
    df.loc[(df['ema_trend'] == 1) & (df['ema_trend'].shift(1) == -1), 'signal'] = 1
    df.loc[(df['ema_trend'] == -1) & (df['ema_trend'].shift(1) == 1), 'signal'] = -1
    return df

def strategy_rsi_mean_reversion(df):
    df = df.copy()
    df['signal'] = 0
    df.loc[(df['RSI_14'] < 30) & (df['RSI_14'].shift(1) >= 30), 'signal'] = 1
    df.loc[(df['RSI_14'] > 70) & (df['RSI_14'].shift(1) <= 70), 'signal'] = -1
    return df

Output ONLY the Python function. No explanation, no markdown fences, no comments outside the function."""

    if st.button("Generate Strategy"):
        if not user_description.strip():
            st.error("Please describe a strategy first.")
        else:
            with st.spinner("Generating strategy with Claude..."):
                try:
                    from anthropic import Anthropic
                    client = Anthropic(api_key=api_key)
                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=1024,
                        system=SYSTEM_PROMPT,
                        messages=[{"role": "user", "content": user_description}]
                    )
                    generated = response.content[0].text.strip()
                    # Strip markdown fences if present
                    generated = re.sub(r'^```(?:python)?\n?', '', generated)
                    generated = re.sub(r'\n?```$', '', generated)
                    st.session_state['generated_code'] = generated.strip()
                except Exception as e:
                    st.error(f"Failed to generate strategy: {e}")

    if 'generated_code' in st.session_state:
        st.subheader("Generated Strategy Code")
        edited_code = st.text_area(
            "Review and edit if needed",
            value=st.session_state['generated_code'],
            height=300,
            key="code_editor"
        )

        if st.button("Run Backtest"):
            with st.spinner(f"Fetching {ai_limit} candles for {ai_symbol}..."):
                df = get_ohlcv(ai_symbol, ai_interval, ai_limit)

            with st.spinner("Running backtest..."):
                try:
                    # Sandboxed execution
                    allowed_globals = {"__builtins__": {}, "pd": pd, "np": np}
                    local_ns = {}
                    exec(edited_code, allowed_globals, local_ns)
                    strategy_func = next((v for v in local_ns.values() if callable(v)), None)
                    if strategy_func is None:
                        st.error("No function found in the generated code.")
                        st.stop()

                    trades_df, metrics, equity_curve = run_backtest(df, strategy_func)
                    st.session_state['trades_df'] = trades_df

                    st.subheader("Performance Metrics")
                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.metric("Total Trades", metrics['Total Trades'])
                    m2.metric("Win Rate", f"{metrics['Win Rate']:.2%}")
                    m3.metric("Profit Factor", f"{metrics['Profit Factor']:.2f}")
                    m4.metric("Sharpe Ratio", f"{metrics['Sharpe Ratio']:.2f}")
                    m5.metric("Max Drawdown", f"{metrics['Max Drawdown']:.2%}")

                    st.subheader("Equity Curve")
                    fig = px.line(equity_curve, title=f"Equity Curve: AI Strategy on {ai_symbol} ({ai_interval})")
                    fig.update_layout(xaxis_title="Time", yaxis_title="Account Balance ($)", showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

                except Exception as e:
                    st.error(f"Strategy execution failed: {e}")
