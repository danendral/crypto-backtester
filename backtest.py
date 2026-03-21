import pandas as pd
import numpy as np

def strategy_ema_crossover(df):
    """
    LONG when EMA20 crosses above EMA50.
    SHORT when EMA20 crosses below EMA50.
    """
    df = df.copy()
    df['ema_trend'] = np.where(df['EMA_20'] > df['EMA_50'], 1, -1)
    df['signal'] = 0
    # Entry on crossover changes
    df.loc[(df['ema_trend'] == 1) & (df['ema_trend'].shift(1) == -1), 'signal'] = 1
    df.loc[(df['ema_trend'] == -1) & (df['ema_trend'].shift(1) == 1), 'signal'] = -1
    return df

def strategy_rsi_mean_reversion(df):
    """
    LONG when RSI drops below 30.
    SHORT when RSI goes above 70.
    """
    df = df.copy()
    df['signal'] = 0
    df.loc[(df['RSI_14'] < 30) & (df['RSI_14'].shift(1) >= 30), 'signal'] = 1
    df.loc[(df['RSI_14'] > 70) & (df['RSI_14'].shift(1) <= 70), 'signal'] = -1
    return df

def strategy_combined(df):
    """
    EMA signal + RSI confirmation.
    """
    df = strategy_ema_crossover(df)
    # Filter signals that don't match our RSI rules
    # E.g. don't go long if it's already overbought (RSI > 70)
    df.loc[(df['signal'] == 1) & (df['RSI_14'] >= 70), 'signal'] = 0
    df.loc[(df['signal'] == -1) & (df['RSI_14'] <= 30), 'signal'] = 0
    return df


def compute_metrics(trades_df, equity_curve):
    """Computes Win Rate, Profit Factor, Sharpe Ratio, Max Drawdown."""
    if trades_df.empty:
        return {
            'Total Trades': 0,
            'Win Rate': 0.0,
            'Profit Factor': 0.0,
            'Sharpe Ratio': 0.0,
            'Max Drawdown': 0.0
        }
        
    total_trades = len(trades_df)
    winning_trades = len(trades_df[trades_df['pnl'] > 0])
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
    
    gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
    gross_loss = abs(trades_df[trades_df['pnl'] <= 0]['pnl'].sum())
    
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
    
    # Equity curve is daily resolution for sharpe
    daily_equity = equity_curve.resample('1D').last().dropna()
    daily_returns = daily_equity.pct_change().dropna()
    
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        # Crypto is traded 365 days a year
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365)
    else:
        sharpe = 0.0
        
    # Max Drawdown
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_drawdown = abs(drawdown.min())
    
    return {
        'Total Trades': int(total_trades),
        'Win Rate': float(win_rate),
        'Profit Factor': float(profit_factor),
        'Sharpe Ratio': float(sharpe),
        'Max Drawdown': float(max_drawdown)
    }

def run_backtest(df, strategy_func, initial_capital=10000.0):
    """
    Executes a candle-by-candle backtest over a dataframe.
    """
    df = strategy_func(df)
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    trades = []
    in_position = False
    entry_price = 0.0
    sl_price = 0.0
    tp_price = 0.0
    position_dir = 0
    position_size = 0.0
    entry_time = None
    fee_rate = 0.001 # 0.1% per side
    current_capital = initial_capital
    
    equity_series = pd.Series(index=df['timestamp'], dtype=float)
    
    for i in range(1, len(df)):
        prev_row = df.iloc[i-1]
        curr_row = df.iloc[i]
        
        # 1. Check for entries if we are NOT in a position
        if not in_position:
            signal = prev_row['signal']
            if signal != 0:
                atr = prev_row['ATRr_14']
                if not pd.isna(atr):
                    position_dir = signal
                    entry_price = curr_row['open']
                    position_size = current_capital / entry_price
                    
                    if position_dir == 1:
                        sl_price = entry_price - (1.5 * atr)
                        tp_price = entry_price + (3.0 * atr)
                    else:
                        sl_price = entry_price + (1.5 * atr)
                        tp_price = entry_price - (3.0 * atr)
                        
                    in_position = True
                    entry_time = curr_row['timestamp']

        # 2. Check for exits if we ARE in a position (applies immediately upon entry too)
        if in_position:
            exit_price = None
            exit_reason = ""
            
            if position_dir == 1:
                # LONG checks
                if curr_row['low'] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                elif curr_row['high'] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
            else:
                # SHORT checks
                if curr_row['high'] >= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                elif curr_row['low'] <= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    
            if exit_price is not None:
                gross_pnl = (exit_price - entry_price) * position_size * position_dir
                entry_fee = entry_price * position_size * fee_rate
                exit_fee = exit_price * position_size * fee_rate
                net_pnl = gross_pnl - entry_fee - exit_fee
                current_capital += net_pnl
                
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': curr_row['timestamp'],
                    'direction': 'LONG' if position_dir == 1 else 'SHORT',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'sl': sl_price,
                    'tp': tp_price,
                    'pnl': net_pnl,
                    'result': 'WIN' if net_pnl > 0 else 'LOSS',
                    'reason': exit_reason
                })
                in_position = False
                
        equity_series.iloc[i] = current_capital
        
    equity_series = equity_series.ffill().fillna(initial_capital)
    trades_df = pd.DataFrame(trades)
    
    if trades_df.empty:
        trades_df = pd.DataFrame(columns=[
            'entry_time', 'exit_time', 'direction', 'entry_price', 
            'exit_price', 'sl', 'tp', 'pnl', 'result', 'reason'
        ])
        
    metrics = compute_metrics(trades_df, equity_series)
    return trades_df, metrics, equity_series

if __name__ == "__main__":
    from data import get_ohlcv
    
    print("Fetching data to test backtester...")
    # Fetching over a full year of hourly data (~416 days)
    df = get_ohlcv("BTCUSDT", "1h", limit=10000)
    
    strategies = [
        ("EMA Crossover", strategy_ema_crossover),
        ("RSI Mean Reversion", strategy_rsi_mean_reversion),
        ("Combined (EMA + RSI)", strategy_combined)
    ]
    
    for name, strat_func in strategies:
        print(f"\n{'='*40}")
        print(f"--- Running {name} Backtest ---")
        trades, metrics, equity = run_backtest(df.copy(), strat_func)
        
        print(f"Trades Executed: {len(trades)}")
        print("Metrics:")
        for k, v in metrics.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.4f}")
            else:
                print(f"  {k}: {v}")
