import ccxt
import pandas as pd
import ta
import numpy as np
from scipy.signal import hilbert

def borsa_verisi_cek(sembol='BTC/USDT', zaman_dilimi='1h', limit=5000):
    borsa = ccxt.binance()
    veriler = borsa.fetch_ohlcv(sembol, timeframe=zaman_dilimi, limit=limit)
    df = pd.DataFrame(veriler, columns=['Zaman', 'Acilis', 'En_Yuksek', 'En_Dusuk', 'Kapanis', 'Hacim'])
    df['Zaman'] = pd.to_datetime(df['Zaman'], unit='ms')
    return df

def get_hilbert_phase(series):
    analytic_signal = hilbert(series - series.mean())
    return np.angle(analytic_signal)

def indikatorleri_ekle(df):
    # Volatilite & Adaptif Risk
    df['ATR'] = ta.volatility.AverageTrueRange(df['En_Yuksek'], df['En_Dusuk'], df['Kapanis'], window=14).average_true_range()
    df['NATR'] = (df['ATR'] / df['Kapanis']) * 100
    
    # Hilbert Transform (Piyasa Döngü Fazı)
    df['Phase'] = get_hilbert_phase(df['Kapanis'].values)
    
    # Momentum & Diverjans Matrisi
    df['RSI'] = ta.momentum.RSIIndicator(df['Kapanis'], window=14).rsi()
    df['MFI'] = ta.volume.MFIIndicator(df['En_Yuksek'], df['En_Dusuk'], df['Kapanis'], df['Hacim'], window=14).money_flow_index()
    df['ROC'] = ta.momentum.ROCIndicator(df['Kapanis'], window=12).roc()
    df['Accel'] = df['ROC'] - df['ROC'].shift(1)
    
    # Trend & Kaos Filtreleri
    high_low_14 = df['En_Yuksek'].rolling(14).max() - df['En_Dusuk'].rolling(14).min()
    df['CHOP'] = 100 * np.log10(df['ATR'].rolling(14).sum() / (high_low_14 + 1e-10)) / np.log10(14)
    
    # KAMA & Efficiency
    df['KAMA'] = ta.momentum.KAMAIndicator(df['Kapanis'], window=10).kama()
    yol = (df['Kapanis'] - df['Kapanis'].shift(10)).abs()
    toplam_yol = (df['Kapanis'] - df['Kapanis'].shift(1)).abs().rolling(10).sum()
    df['Efficiency'] = yol / (toplam_yol + 1e-10)
    
    # Hacim & Spread Analizi (VSA)
    df['Spread'] = (df['En_Yuksek'] - df['En_Dusuk']) / (df['Kapanis'] + 1e-10)
    df['V_Spike'] = df['Hacim'] / (df['Hacim'].rolling(20).mean() + 1e-10)
    df['VSA_Signal'] = df['Spread'] * df['V_Spike'] # Yüksek spread + yüksek hacim = Karar noktası
    
    # Kurumsal Kanallar
    bb = ta.volatility.BollingerBands(df['Kapanis'], window=20, window_dev=2)
    df['BB_Width'] = bb.bollinger_wband()
    df['BB_High_Dist'] = (bb.bollinger_hband() - df['Kapanis']) / (df['Kapanis'] + 1e-10)
    
    # İstatistiksel Uç Değerler
    df['Z_Score'] = (df['Kapanis'] - df['Kapanis'].rolling(20).mean()) / (df['Kapanis'].rolling(20).std() + 1e-10)
    
    # Price Action (V2)
    df['Upper_Wick'] = df['En_Yuksek'] - df[['Acilis', 'Kapanis']].max(axis=1)
    df['Lower_Wick'] = df[['Acilis', 'Kapanis']].min(axis=1) - df['En_Dusuk']
    df['Body_Ratio'] = (df['Kapanis'] - df['Acilis']).abs() / (df['En_Yuksek'] - df['En_Dusuk'] + 1e-10)

    return df.dropna().reset_index(drop=True)