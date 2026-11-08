import time
import os
import ccxt
import pandas as pd
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecFrameStack
from veri_cek import borsa_verisi_cek, indikatorleri_ekle
from ortam import BorsaOrtami
from config import Config

# Yapılandırma (API anahtarları .env dosyasından okunur, koda yazılmaz)
Config.validate()
API_KEY = Config.BINANCE_API_KEY
SECRET_KEY = Config.BINANCE_SECRET_KEY
MODEL_YOLU = os.path.join(Config.MODEL_DIR, Config.MODEL_NAME)
SEMBOL = Config.SYMBOL
ZAMAN_DILIMI = Config.TIMEFRAME
BEKLEME_SURESI = Config.WAIT_TIME  # 1 Saat (Mum kapanışı)

# Borsa Bağlantısı
borsa = ccxt.binance({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})
borsa.set_sandbox_mode(Config.USE_SANDBOX)

def modeli_yukle_ve_hazırla(df):
    env = DummyVecEnv([lambda: BorsaOrtami(df)])
    env = VecFrameStack(env, n_stack=24)
    if os.path.exists(MODEL_YOLU + ".zip"):
        model = PPO.load(MODEL_YOLU, env=env, device="auto")
        print("🏆 Şampiyon model başarıyla yüklendi.")
        return model, env
    else:
        print("⚠️ Model dosyası bulunamadı! Lütfen önce eğitimi tamamlayın.")
        return None, None

def canli_islem_yurut():
    print(f"🚀 {SEMBOL} Canlı İşlem Birimi Başlatıldı.")
    
    while True:
        try:
            # 1. Taze Veri Çek ve İndikatörleri Hesapla
            ham_veri = borsa_verisi_cek(sembol=SEMBOL, zaman_dilimi=ZAMAN_DILIMI, limit=2000)
            islenmis_veri = indikatorleri_ekle(ham_veri)
            
            # 2. Modeli ve Ortamı Canlı Veriye Göre Senkronize Et
            model, env = modeli_yukle_ve_hazırla(islenmis_veri)
            if model is None: break

            # 3. Güncel Cüzdan Durumunu Al
            bakiye = borsa.fetch_balance()
            usdt_bakiye = bakiye['USDT']['free']
            btc_bakiye = bakiye['BTC']['free']
            anlik_fiyat = islenmis_veri.iloc[-1]['Kapanis']
            
            # 4. Tahmin Yürüt
            obs = env.reset()
            action, _ = model.predict(obs, deterministic=True)
            karar = float(np.clip(action, -1.0, 1.0))
            
            print(f"🕒 {pd.Timestamp.now()} | Fiyat: {anlik_fiyat:.2f} $ | Model Kararı: {karar:.2f}")

            # 5. Emir İletimi (Güven Eşiği: 0.2)
            if karar > 0.2 and usdt_bakiye > 10:
                alinacak_tutar = usdt_bakiye * karar * 0.98
                miktar = alinacak_tutar / anlik_fiyat
                print(f"🟢 ALIM EMRİ: {miktar:.5f} BTC gönderiliyor...")
                borsa.create_market_buy_order(SEMBOL, miktar)
                
            elif karar < -0.2 and btc_bakiye > 0.0001:
                satilacak_miktar = btc_bakiye * abs(karar)
                print(f"🔴 SATIŞ EMRİ: {satilacak_miktar:.5f} BTC gönderiliyor...")
                borsa.create_market_sell_order(SEMBOL, satilacak_miktar)
            
            else:
                print("⚪ Karar eşiği aşılmadı. İzlemeye devam ediliyor.")

            # 6. Bir sonraki mum kapanışına kadar uyu
            print(f"💤 {ZAMAN_DILIMI} kapanışı bekleniyor...")
            time.sleep(BEKLEME_SURESI)

        except ccxt.NetworkError as e:
            print(f"🌐 Ağ Hatası: {e}. 30 saniye sonra tekrar denenecek...")
            time.sleep(30)
        except Exception as e:
            print(f"❌ Kritik Hata: {e}")
            time.sleep(60)

if __name__ == "__main__":
    canli_islem_yurut()