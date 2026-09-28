import html
import os
import requests
import json # JSON formatında menü göndermek için eklendi
from dotenv import load_dotenv

load_dotenv()

def telegrama_haber_gonder(baslik, link, ozet, gonderilecek_kisi=None):
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    chat_id = gonderilecek_kisi if gonderilecek_kisi else os.getenv("TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    guvenli_baslik = html.escape(str(baslik))
    mesaj = f"<b>{guvenli_baslik}</b>\n\n{link}"

    sabit_menu = {
        "keyboard": [
            [{"text": "Son 24 Saat"}, {"text": "Son 3 Gün"}, {"text": "Son 1 Hafta"}],
            [{"text": "⭐ Favoriler"}, {"text": "Kaynaklar"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

    requests.post(url, data={
        "chat_id": chat_id,
        "text": mesaj,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": json.dumps(sabit_menu) # Arka plan mesajına menü dahil edildi
    })