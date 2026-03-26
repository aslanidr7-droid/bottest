import os
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, VecFrameStack, VecMonitor
from stable_baselines3.common.callbacks import EvalCallback
from veri_cek import borsa_verisi_cek, indikatorleri_ekle
from ortam import BorsaOrtami

def ortam_yapilandir(df):
    def _init():
        return BorsaOrtami(df)
    return _init

if __name__ == '__main__':
    df = indikatorleri_ekle(borsa_verisi_cek(limit=5000))
    
    split = int(len(df) * 0.85)
    train_df = df.iloc[:split].reset_index(drop=True)
    test_df = df.iloc[split:].reset_index(drop=True)

    cekirdek = 4 
    env = VecFrameStack(VecMonitor(SubprocVecEnv([ortam_yapilandir(train_df) for _ in range(cekirdek)])), n_stack=24)
    eval_env = VecFrameStack(VecMonitor(SubprocVecEnv([ortam_yapilandir(test_df)])), n_stack=24)

    yol = "./nihai_model_merkezi/"
    os.makedirs(yol, exist_ok=True)

    callback = EvalCallback(
        eval_env, 
        best_model_save_path=yol,
        log_path=yol, 
        eval_freq=10000,
        deterministic=True
    )

    policy_kwargs = dict(
        activation_fn=torch.nn.ReLU,
        net_arch=dict(pi=[512, 512, 256], vf=[512, 512, 256])
    )

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=7e-5,
        n_steps=4096,
        batch_size=1024,
        n_epochs=15,
        gamma=0.995,
        gae_lambda=0.98,
        ent_coef=0.01,
        policy_kwargs=policy_kwargs,
        device="auto"
    )

    print("🚀 Savaş Başlıyor: 2 Milyon Adımlık Derin Eğitim Tetiklendi.")
    model.learn(total_timesteps=100000, callback=callback)
    model.save("borsa_canavari_final")