import os #gizli şifreleri okumak için
import requests
from dotenv import load_dotenv

load_dotenv()#şifreleri gizli dosyadan güvenli okumak için


def telegrama_haber_gonder(baslik, link, gonderilecek_kisi=None):
    token = os.getenv("TELEGRAM_BOT_TOKEN")

#Gelen bir ID yoksa sistem aksamadan çalışsın diye haberleri yedek adres olarak .env dosyasına yollar
    chat_id = gonderilecek_kisi if gonderilecek_kisi else os.getenv("TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    mesaj = f"{baslik}\n{link}"

    requests.post(url, data={"chat_id": chat_id, "text": mesaj})