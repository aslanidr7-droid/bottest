import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', 'test_key')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', 'test_secret')
    SYMBOL = os.getenv('SYMBOL', 'BTC/USDT')
    TIMEFRAME = os.getenv('TIMEFRAME', '1h')
    WAIT_TIME = int(os.getenv('WAIT_TIME', '3600'))
    INITIAL_BALANCE = float(os.getenv('INITIAL_BALANCE', '10000'))
    MIN_BALANCE_USDT = float(os.getenv('MIN_BALANCE_USDT', '10'))
    MIN_BALANCE_BTC = float(os.getenv('MIN_BALANCE_BTC', '0.0001'))
    USE_SANDBOX = os.getenv('USE_SANDBOX', 'True').lower() == 'true'
    TRAINING_TIMESTEPS = int(os.getenv('TRAINING_TIMESTEPS', '2000000'))
    DATA_LIMIT_HOURS = int(os.getenv('DATA_LIMIT_HOURS', '5000'))
    TRAIN_TEST_SPLIT = float(os.getenv('TRAIN_TEST_SPLIT', '0.85'))
    MODEL_DIR = os.getenv('MODEL_DIR', './nihai_model_merkezi/')
    MODEL_NAME = os.getenv('MODEL_NAME', 'best_model')
    BACKUP_MODEL_DIR = os.getenv('BACKUP_MODEL_DIR', './model_backups/')
    LOG_DIR = os.getenv('LOG_DIR', './logs/')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    BACKTEST_DATA_FILE = os.getenv('BACKTEST_DATA_FILE', './data/backtest_data.csv')

    @classmethod
    def validate(cls):
        if cls.USE_SANDBOX is False:
            if cls.BINANCE_API_KEY == 'test_key':
                raise ValueError('Gerçek işlem için geçerli API anahtarı gerekli!')
        print('Yapılandırma başarıyla doğrulandı')
        return True