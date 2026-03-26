import optuna
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecFrameStack
from veri_cek import borsa_verisi_cek, indikatorleri_ekle
from ortam import BorsaOrtami

def objective(trial):
    # Botun kendi kendine deneyeceği parametre aralıkları
    lr = trial.suggest_float("lr", 1e-5, 1e-3, log=True)
    n_steps = trial.suggest_categorical("n_steps", [1024, 2048, 4096])
    batch_size = trial.suggest_categorical("batch_size", [64, 128, 256, 512])
    ent_coef = trial.suggest_float("ent_coef", 0.0001, 0.1, log=True)
    n_stack = trial.suggest_int("n_stack", 12, 48)

    df = indikatorleri_ekle(borsa_verisi_cek(limit=3000))
    train_df = df.iloc[:-500].reset_index(drop=True)
    
    env = DummyVecEnv([lambda: BorsaOrtami(train_df)])
    env = VecFrameStack(env, n_stack=n_stack)

    model = PPO("MlpPolicy", env, learning_rate=lr, n_steps=n_steps, 
                batch_size=batch_size, ent_coef=ent_coef, verbose=0)
    
    model.learn(total_timesteps=50000)
    
    # Performans Ölçümü (Son bakiyeye göre ödül)
    return env.envs[0].bakiye

if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=20)
    print("🏆 En iyi parametreler:", study.best_params)