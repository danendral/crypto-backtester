import pandas as pd
import pandas_ta as ta
import requests
import sqlite3
import time

DB_NAME = "crypto_backtest.db"
BASE_URL = "https://data-api.binance.vision/api/v3/klines"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ohlcv_data (
            symbol TEXT,
            interval TEXT,
            open_time INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (symbol, interval, open_time)
        )
    ''')
    conn.commit()
    return conn

def fetch_binance_ohlcv(symbol, interval, limit=500):
    """Fetches OHLCV data from Binance with pagination to support huge limits."""
    all_data = []
    end_time = None
    remaining = limit
    
    while remaining > 0:
        batch_limit = min(remaining, 1000)
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': batch_limit
        }
        if end_time:
            params['endTime'] = int(end_time)
            
        print(f"Fetching {batch_limit} candles... (remaining: {remaining})")
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            break
            
        # Prepend the older data to our full list
        all_data = data + all_data
        
        # Binance open_time is the first element of each candle.
        # The next fetch should end 1 millisecond before the oldest candle in this batch.
        end_time = data[0][0] - 1
        remaining -= len(data)
        time.sleep(0.1) # Respect Binance rate limits
        
    df = pd.DataFrame(all_data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore'
    ])
    
    df = df[['open_time', 'open', 'high', 'low', 'close', 'volume']]
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
        
    df['open_time'] = pd.to_numeric(df['open_time'])
    return df

def get_ohlcv(symbol, interval, limit=500):
    """
    Retrieves OHLCV data. Loads from local SQLite cache if available,
    otherwise fetches from Binance, caches it, computes indicators and returns the DataFrame.
    """
    conn = init_db()
    
    # Check cache
    query = '''
        SELECT open_time, open, high, low, close, volume 
        FROM ohlcv_data 
        WHERE symbol = ? AND interval = ? 
        ORDER BY open_time DESC 
        LIMIT ?
    '''
    df_db = pd.read_sql_query(query, conn, params=(symbol, interval, limit))
    
    # If we have exactly the requested number of records or more, use the cached data
    if len(df_db) >= limit:
        print(f"Loaded {len(df_db)} rows from local SQLite cache for {symbol} {interval}.")
        # Data descending, so reverse it
        df_final = df_db.sort_values('open_time').reset_index(drop=True)
    else:
        print(f"Insufficient cache for {symbol} {interval}. Fetching {limit} latest rows from Binance...")
        df_final = fetch_binance_ohlcv(symbol, interval, limit)
        
        # Save to DB to cache future requests
        records = [(symbol, interval,
                    row['open_time'], row['open'], row['high'], row['low'], row['close'], row['volume'])
                   for _, row in df_final.iterrows()]
                   
        conn.executemany('''
            INSERT OR IGNORE INTO ohlcv_data (symbol, interval, open_time, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', records)
        conn.commit()
    
    conn.close()
    
    # Format times properly for human readability
    df_final['timestamp'] = pd.to_datetime(df_final['open_time'], unit='ms')
    
    # Compute indicators
    # pandas-ta computes standard names: EMA_20, EMA_50, RSI_14, ATRr_14
    df_final.ta.ema(length=20, append=True)
    df_final.ta.ema(length=50, append=True)
    df_final.ta.rsi(length=14, append=True)
    df_final.ta.atr(length=14, append=True)
    
    return df_final

if __name__ == "__main__":
    test_symbol = "BTCUSDT"
    test_interval = "1h"
    test_limit = 500
    
    print(f"=== Testing get_ohlcv for {test_symbol} on {test_interval} interval ===")
    df = get_ohlcv(test_symbol, test_interval, test_limit)
    
    print(f"\nDataframe shape: {df.shape}")
    print("\nTail of the dataframe:")
    print(df[['timestamp', 'close', 'EMA_20', 'EMA_50', 'RSI_14', 'ATRr_14']].tail())
