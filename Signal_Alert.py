import requests
import pandas as pd
import time

# Binance API URLs
BINANCE_URL = "https://api.binance.com/api/v3/klines"
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = "7576276594:AAF8oLVL5ESIX1ItWAmh_bd0_Rma_W0b5Hg"
TELEGRAM_CHAT_ID = "1686678295"

# Function to send message to Telegram
def send_telegram_message(message):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(telegram_url, json=payload)
    if response.status_code == 200:
        print("✅ Signal sent to Telegram: ", message)
    else:
        print("❌ Failed to send message to Telegram")

# Function to get all trading pairs from Binance
def get_all_binance_symbols():
    response = requests.get(BINANCE_TICKER_URL)
    if response.status_code == 200:
        symbols = [item["symbol"] for item in response.json() if item["symbol"].endswith("USDT")]
        return symbols
    return []

# Function to fetch crypto data from Binance
def get_crypto_data(symbol, interval="5m", limit=50):
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(BINANCE_URL, params=params)
    if response.status_code != 200:
        print(f"Error fetching {symbol}: {response.text}")
        return None
    data = response.json()

    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base_vol", "taker_buy_quote_vol", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

# Function to calculate indicators
def calculate_indicators(df):
    df["MA_Short"] = df["close"].rolling(window=9).mean()
    df["MA_Long"] = df["close"].rolling(window=21).mean()
    
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    
    df = calculate_atr(df)
    return df

# Function to calculate ATR (Average True Range)
def calculate_atr(df, period=14):
    df["High-Low"] = df["high"] - df["low"]
    df["High-Close"] = abs(df["high"] - df["close"].shift(1))
    df["Low-Close"] = abs(df["low"] - df["close"].shift(1))
    df["True Range"] = df[["High-Low", "High-Close", "Low-Close"]].max(axis=1)
    df["ATR"] = df["True Range"].rolling(window=period).mean()
    return df

# Function to check trading signals with stronger confirmation
def check_signals(df, symbol):
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    atr = last_row["ATR"]
    price = last_row["close"]
    volume = last_row["volume"]

    # Avoid signals if ATR is too low (low volatility) or volume is too small
    if atr < price * 0.001 or volume < 10000:
        return

    # Strong LONG signal: RSI crosses above 50 & MA crossover
    if prev_row["RSI"] < 50 and last_row["RSI"] > 50 and prev_row["MA_Short"] < prev_row["MA_Long"] and last_row["MA_Short"] > last_row["MA_Long"]:
        tp = price + (atr * 3)  # Take Profit at 3x ATR
        sl = price - (atr * 2)  # Stop Loss at 2x ATR
        message = f"🚀 STRONG LONG for {symbol}\nPrice: {price}\nRSI: {last_row['RSI']:.2f}\n🎯 TP: {tp:.2f}\n🛑 SL: {sl:.2f}"
        send_telegram_message(message)

    # Strong SHORT signal: RSI crosses below 50 & MA crossover
    elif prev_row["RSI"] > 50 and last_row["RSI"] < 50 and prev_row["MA_Short"] > prev_row["MA_Long"] and last_row["MA_Short"] < last_row["MA_Long"]:
        tp = price - (atr * 3)  # Take Profit at 3x ATR
        sl = price + (atr * 2)  # Stop Loss at 2x ATR
        message = f"🔻 STRONG SHORT for {symbol}\nPrice: {price}\nRSI: {last_row['RSI']:.2f}\n🎯 TP: {tp:.2f}\n🛑 SL: {sl:.2f}"
        send_telegram_message(message)

# Main function
def run_bot():
    symbols = get_all_binance_symbols()
    if not symbols:
        print("Failed to retrieve Binance symbols!")
        return
    
    while True:
        for coin in symbols:
            df = get_crypto_data(symbol=coin, interval="5m", limit=50)
            if df is not None:
                df = calculate_indicators(df)
                check_signals(df, coin)
        time.sleep(300)  # Run every 5 minutes

if __name__ == "__main__":
    run_bot()
