from sb3_contrib import RecurrentPPO
from stable_baselines3.common.vec_env import DummyVecEnv
from veri_cek import borsa_verisi_cek, indikatorleri_ekle
from ortam import BorsaOrtami

ham_veri = borsa_verisi_cek(limit=500)
islenmis_veri = indikatorleri_ekle(ham_veri)

ortam = DummyVecEnv([lambda: BorsaOrtami(islenmis_veri)])

try:
    model = RecurrentPPO.load("./en_iyi_model_lstm/best_model")
except Exception as e:
    print("Model bulunamadı!")
    exit()

gozlem = ortam.reset()
lstm_hafizasi = None
bitti_mi = [False]
adim_sayisi = 0
islem_gecmisi = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

while True:
    islem, lstm_hafizasi = model.predict(gozlem, state=lstm_hafizasi, episode_start=bitti_mi)
    alinan_karar = int(islem[0]) 
    
    gozlem, odul, bitti_mi, bilgi = ortam.step([alinan_karar])
    adim_sayisi += 1
    islem_gecmisi[alinan_karar] += 1
    
    if bitti_mi[0]:
        break

son_bakiye = ortam.envs[0].bakiye
son_coin = ortam.envs[0].elimizdeki_coin
son_fiyat = islenmis_veri.iloc[-1]['Kapanis']
toplam_varlik = son_bakiye + (son_coin * son_fiyat)

print("\n--- LSTM (DERİN ÖĞRENME) TEST SONUÇLARI ---")
print(f"İncelenen Süre: {adim_sayisi} Saat")
print(f"Bekleme: {islem_gecmisi[0]} | %50 Al: {islem_gecmisi[1]} | %100 Al: {islem_gecmisi[2]} | %50 Sat: {islem_gecmisi[3]} | %100 Sat: {islem_gecmisi[4]}")
print(f"Başlangıç Parası: 10000.00 Dolar")
print(f"Test Sonu Toplam Varlık: {toplam_varlik:.2f} Dolar")