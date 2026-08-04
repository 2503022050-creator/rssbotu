import os
import requests
from dotenv import load_dotenv

load_dotenv()

def telegrama_haber_gonder(baslik, link):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    mesaj = f"{baslik}\n{link}"

    requests.post(url, data={"chat_id": chat_id, "text": mesaj})