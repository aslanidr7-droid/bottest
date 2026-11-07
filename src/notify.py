"""P9 Telegram alerts. Without TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID it just prints."""
import os
import requests
from .broker import load_env


def send(text):
    load_env()
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    print(f"[alert] {text}")
    if not (tok and chat):
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                          json={"chat_id": chat, "text": text[:4000]}, timeout=20)
        return r.ok
    except Exception:
        return False


def find_chat_id():
    """After messaging your bot once: returns the chat id from getUpdates."""
    load_env()
    tok = os.environ["TELEGRAM_BOT_TOKEN"]
    upd = requests.get(f"https://api.telegram.org/bot{tok}/getUpdates", timeout=20).json()
    return sorted({u["message"]["chat"]["id"] for u in upd.get("result", []) if "message" in u})
