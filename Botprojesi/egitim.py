from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from veri_cek import borsa_verisi_cek, indikatorleri_ekle
from ortam import BorsaOrtami

print("--- YAPAY ZEKA EĞİTİM PROGRAMI ---")

print("\n1. Veriler borsadan çekiliyor...")
# Eğitim için botun daha çok tecrübe edinmesi lazım, bu yüzden 2000 saatlik veri çekiyoruz
ham_veri = borsa_verisi_cek(sembol='BTC/USDT', zaman_dilimi='1h', limit=3000)
islenmis_veri = indikatorleri_ekle(ham_veri)

print("\n2. Simülasyon ortamı hazırlanıyor...")
# Kendi yazdığımız ortamı, yapay zekanın içine girebileceği formata çeviriyoruz
ortam = DummyVecEnv([lambda: BorsaOrtami(islenmis_veri)])

print("\n3. Yapay Zeka (Beyin) oluşturuluyor...")
# PPO: Kullanacağımız öğrenme algoritması
# MlpPolicy: Botun beynindeki yapay sinir ağı (Standart bir beyin tipi)
# ent_coef=0.1 ayarı bota risk almayı ve yeni şeyler denemeyi zorunlu kılar (Cesaret Hapı)
model = PPO("MlpPolicy", ortam, verbose=1, ent_coef=0.1)

print("\n4. Eğitim başlıyor! Lütfen bekleyin...")
# Bot 10.000 defa piyasaya bakıp karar verme (alım/satım) antrenmanı yapacak
model.learn(total_timesteps=500000)

print("\n5. Eğitim tamamlandı! Öğrenen beyin kaydediliyor...")
# Öğrenmiş modeli bir dosya olarak kaydediyoruz ki daha sonra canlı işlemlerde kullanalım
model.save("ilk_bot_beyni")
print("Harika! 'ilk_bot_beyni.zip' dosyası başarıyla oluşturuldu.")