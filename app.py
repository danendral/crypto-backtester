import streamlit as st
import pandas as pd
import plotly.express as px
import time
from data import get_ohlcv, fetch_binance_ohlcv
from backtest import run_backtest, strategy_ema_crossover, strategy_rsi_mean_reversion, strategy_combined

st.set_page_config(page_title="Crypto Backtester", layout="wide", page_icon="📈")

STRATEGIES = {
    "EMA Crossover": strategy_ema_crossover,
    "RSI Mean Reversion": strategy_rsi_mean_reversion,
    "Combined (EMA + RSI)": strategy_combined
}

st.sidebar.title("Navigation")
page = st.sidebar.radio("Select Page", ["Backtest Runner", "Trades Log", "Live Market Pulse"])

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
            st.plotly_chart(fig, width="stretch")

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
            
        st.dataframe(styled_df, width="stretch")
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
