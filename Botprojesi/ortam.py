import gymnasium as gym
from gymnasium import spaces
import numpy as np

class BorsaOrtami(gym.Env):
    def __init__(self, veri_tablosu):
        super(BorsaOrtami, self).__init__()
        self.df_np = veri_tablosu.values
        self.kapanis_idx = veri_tablosu.columns.get_loc('Kapanis')
        self.atr_idx = veri_tablosu.columns.get_loc('ATR')
        
        cols = [c for c in veri_tablosu.columns if c != 'Zaman']
        df_num = veri_tablosu[cols]
        self.df_norm_np = ((df_num - df_num.min()) / (df_num.max() - df_num.min() + 1e-10)).values
        
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(self.df_norm_np.shape[1] + 4,), dtype=np.float32)
        self.max_adim = len(self.df_np) - 1

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.guncel_adim, self.bakiye, self.coin, self.maliyet = 0, 10000.0, 0.0, 0.0
        self.zirve_varlik, self.islem_zirve_fiyat, self.islem_adim_sayisi = 10000.0, 0.0, 0
        return self._sonraki_gozlem(), {}

    def _sonraki_gozlem(self):
        fiyat = self.df_np[self.guncel_adim, self.kapanis_idx]
        kar_oran = (fiyat - self.maliyet) / (self.maliyet + 1e-10) if self.maliyet > 0 else 0.0
        state = np.append(self.df_norm_np[self.guncel_adim], [self.bakiye/10000.0, self.coin, kar_oran, self.islem_adim_sayisi/100.0])
        return state.astype(np.float32)

    def step(self, action):
        karar = float(np.clip(np.squeeze(action), -1.0, 1.0))
        fiyat = self.df_np[self.guncel_adim, self.kapanis_idx]
        atr = self.df_np[self.guncel_adim, self.atr_idx]
        onceki_varlik = self.bakiye + (self.coin * fiyat)
        kesinti = 0.9985

        if self.coin > 0:
            self.islem_adim_sayisi += 1
            self.islem_zirve_fiyat = max(self.islem_zirve_fiyat, fiyat)
            # Fraktal Volatilite Stop (ATR temelli dinamik daralma)
            stop_fiyat = self.islem_zirve_fiyat - (atr * (2.2 if self.islem_adim_sayisi < 24 else 1.6))
            if fiyat <= stop_fiyat or self.islem_adim_sayisi > 72: karar = -1.0

        if karar > 0.25 and self.bakiye > 10:
            al_tutar = self.bakiye * karar * kesinti
            self.coin += al_tutar / fiyat
            self.bakiye -= (self.bakiye * karar)
            self.maliyet = (self.maliyet + fiyat) / 2 if self.maliyet > 0 else fiyat
            self.islem_zirve_fiyat, self.islem_adim_sayisi = fiyat, 0
        elif karar < -0.25 and self.coin > 0:
            sat_miktar = self.coin * abs(karar)
            self.bakiye += (sat_miktar * fiyat * kesinti)
            self.coin -= sat_miktar
            if self.coin < 1e-6: self.coin, self.maliyet, self.islem_zirve_fiyat, self.islem_adim_sayisi = 0, 0, 0, 0

        self.guncel_adim += 1
        bitti = self.guncel_adim >= self.max_adim
        yeni_varlik = self.bakiye + (self.coin * (self.df_np[self.guncel_adim, self.kapanis_idx] if not bitti else fiyat))
        self.zirve_varlik = max(self.zirve_varlik, yeni_varlik)
        
        # Keskinleştirilmiş Ödül Fonksiyonu (Sharpe Odaklı)
        reward = np.log(yeni_varlik / (onceki_varlik + 1e-10)) * 150
        drawdown = (self.zirve_varlik - yeni_varlik) / (self.zirve_varlik + 1e-10)
        reward -= (drawdown * 25) 
        if abs(karar) > 0.1: reward -= 0.05

        return self._sonraki_gozlem(), float(reward), bitti, False, {}