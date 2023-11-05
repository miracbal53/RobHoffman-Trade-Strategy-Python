from binance.client import Client
import pandas as pd
import talib 
from datetime import datetime
import numpy as np

# symbol = str(input("İşlem yapmak istediğiniz coinin adını  giriniz (örn : BTCUSDT) : "))
# interval = int(input("Zaman dilimini seçiniz : 1- 5 dakika \n 2- 15 dakika \n 3- 30 dakika \n 4- 1 saat \n 5- 4 saat \n 6- 1 gün \n"))
# if interval == 1:
#     interval = Client.KLINE_INTERVAL_5MINUTE
# if interval == 2:
#     interval = Client.KLINE_INTERVAL_15MINUTE
# if interval == 3:
#     interval = Client.KLINE_INTERVAL_30MINUTE
# if interval == 4:
#     interval = Client.KLINE_INTERVAL_1HOUR
# if interval == 5:
#     interval = Client.KLINE_INTERVAL_4HOUR
# if interval == 6:
#     interval = Client.KLINE_INTERVAL_1DAY
# if interval == None:
#     interval == Client.KLINE_INTERVAL_15MINUTE


api_key = None
api_secret = None

client = Client(api_key, api_secret)
klines = client.futures_klines(symbol="BTCUSDT", interval=Client.KLINE_INTERVAL_15MINUTE)
    
df = pd.DataFrame(klines, columns=["timestamp", "open", "high", "low", "close", "volume", "close_time", "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"])

df["open"] = pd.to_numeric(df["open"])
df["high"] = pd.to_numeric(df["high"])
df["low"] = pd.to_numeric(df["low"])
df["close"] = pd.to_numeric(df["close"])
df["volume"] = pd.to_numeric(df["volume"])
df["timestamp"] = df["timestamp"].apply(lambda x: datetime.fromtimestamp(x / 1000).strftime('%Y-%m-%d %H:%M'))

# Mum Bilgileri
open = df["open"]
high = df["high"]
low = df["low"]
close = df["close"]
vol = df["volume"]
timestamp = df["timestamp"]

tr_values = []
rma_values = []
ku_values = []

cuzdan = 1000
long_position = False
short_position = False
long_entry_price = 0.0
short_entry_price = 0.0
long_sl_price = 0
long_tp_price = 0
short_tp_price = 0
short_sl_price = 0
successful_trades = 0
unsuccessful_trades = 0
long_condition_met = False


# Rob Hoffman Inventory Retracement Bar and Overlay Set 
for i in range(len(close)):
    
    z = 45  # yüzdelik geri çekilme

    # Candle Range
    a = np.abs(high - low)

    # Candle Body
    b = np.abs(close - open)

    # Percent to Decimal
    c = z / 100

    # Range Verification
    rv = b < c * a

    # Price Level for Retracement
    x = low + c * a
    y = high - c * a

    sl = (rv == 1) & (high > y) & (close < y) & (open < y) # long bar
    ss = (rv == 1) & (low < x) & (close > x) & (open > x) # short bar

    long_bar = sl
    short_bar = ss

    # Line Definition
    li = np.where(sl, y, np.where(ss, x, (x + y) / 2))

    # Rob Hoffman - Overlay Set

    # Dönemler
    sma_period = 5
    ema_period = 18
    sma_period_50 = 50
    sma_period_89 = 89
    ema_period_144 = 144
    ema_period_35 = 35

    # Hesaplamalar
    slow_speed_line = talib.SMA(close, timeperiod=sma_period)
    fast_primary_trend_line = talib.EMA(close, timeperiod=ema_period)
    trend_line_1 = talib.SMA(close, timeperiod=sma_period_50)
    trend_line_2 = talib.SMA(close, timeperiod=sma_period_89)
    trend_line_3 = talib.EMA(close, timeperiod=ema_period_144)
    no_trend_zone_midline = talib.EMA(close, timeperiod=ema_period_35)


    # Diğer hesaplamalar için gerekli verilerin temsili ve RMA Hesaplanması
    k = talib.EMA(close, timeperiod=35) # no trend zone mid line

    # tr hesaplama
    high_i = df['high'].iloc[i]
    low_i = df['low'].iloc[i]
    close_i = df['close'].iloc[i]
    close_i_minus_1 = df['close'].shift(1).iloc[i]
    tr_i = max(high_i - low_i, abs(high_i - close_i_minus_1), abs(low_i - close_i_minus_1))
    tr_values.append(tr_i)

    # rma hesaplama
    rma_length = 35
    if i < rma_length:
        rma_value = tr_i
    else:
        alpha = 2 / (rma_length + 1)
        previous_rma = rma_values[-1]
        rma_value = (1 - alpha) * previous_rma + alpha * tr_i
    rma_values.append(rma_value)

    # ku hesaplama
    ku_value = k[i] + rma_value * 0.5
    ku_values.append(ku_value)

    # Long işleme giriş şartları 

    long_condition_line_control = slow_speed_line[i] > fast_primary_trend_line[i] and fast_primary_trend_line[i] > trend_line_1[i] and fast_primary_trend_line[i] > trend_line_2[i] and fast_primary_trend_line[i] > trend_line_3[i] and fast_primary_trend_line[i] > no_trend_zone_midline[i] and fast_primary_trend_line[i] > ku_values[i] and close[i]>fast_primary_trend_line[i]
    long_condition = long_condition_line_control and long_bar[i]

    if (not long_position):
        if long_condition and not long_condition_met:
            long_condition_met = True  # Koşullar bir kere sağlandığında işaretle
            long_condition_bar_high = high[i]
            long_condition_bar_low = low[i]
            long_condition_bar_slow_speed_line = slow_speed_line[i]
            long_condition_bar_fast_primary_trend_line = fast_primary_trend_line[i]
            if long_condition_bar_low <= slow_speed_line[i]:
                long_sl_price = long_condition_bar_fast_primary_trend_line
                long_tp_price = long_condition_bar_high + (long_condition_bar_high - long_sl_price)
            else:
                long_sl_price = long_condition_bar_slow_speed_line
                long_tp_price = long_condition_bar_high + (long_condition_bar_high - long_sl_price)
            
            for j in range(i + 1, min(i + 4, len(close))):
                if close[j] > long_condition_bar_high:
                    long_position = True
                    long_entry_price = close[j]
                    print(timestamp[j], "tarihinde long girildi")
                    break
        
    long_tp_condition = close[i] >= long_tp_price
    long_sl_condition = close[i] <= long_sl_price

    # Long TP ve SL alma yeri            
    if long_position:
        if long_tp_condition:
            print(timestamp[i], "tarihinde long işlemin kar alındı")
            long_position = False
            long_condition_met = False  # İşlem tamamlandığında koşulu sıfırla
            successful_trades += 1
        if long_sl_condition:
            print(timestamp[i], "tarihinde long işlemin sl ile sonuçlandı")
            long_position = False
            long_condition_met = False  # İşlem tamamlandığında koşulu sıfırla

    # Short işleme giriş kuralları
    short_condition_line_control = slow_speed_line[i] < fast_primary_trend_line[i] and fast_primary_trend_line[i] < trend_line_1[i] and fast_primary_trend_line[i] < trend_line_2[i] and fast_primary_trend_line[i] < trend_line_3[i] and fast_primary_trend_line[i] < no_trend_zone_midline[i] and fast_primary_trend_line[i] < ku_values[i] and close[i]<fast_primary_trend_line[i]
    short_condition = short_condition_line_control and short_bar[i]

    # Short işleme girme yeri
    if (not short_position):
        if (short_condition):
            short_condition_bar_high = high[i]
            short_condition_bar_low = low[i]
            short_condition_bar_slow_speed_line = slow_speed_line[i]
            short_condition_bar_fast_primary_trend_line = fast_primary_trend_line[i]
            if short_condition_bar_high >= slow_speed_line[i]:
                short_sl_price = short_condition_bar_fast_primary_trend_line
                short_tp_price = short_condition_bar_low - (short_condition_bar_low + short_sl_price)
            else :
                short_sl_price = short_condition_bar_slow_speed_line
                short_tp_price = short_condition_bar_low - (short_condition_bar_low + short_sl_price)
            
            for j in range(i + 1, min(i + 4, len(close))):
                if close[j] <= short_condition_bar_low:
                    short_position = True
                    short_entry_price = close[j]
                    print(timestamp[j],"tarihinde short girildi")
                    break
    
    short_tp_condition = (close[i] <= short_tp_price)
    short_sl_condition = (close[i] >= short_sl_price)

    # Short TP ve SL alma yeri            
    if short_position:
        if short_tp_condition:
            print(timestamp[i], "tarihinde short işlemin kar alındı")
            short_position = False
            
        if short_sl_condition :
            print(timestamp[i], "tarihinde short işlemin sl ile sonuçlandı")
            short_position = False
            
    
        
    
        




