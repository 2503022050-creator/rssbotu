import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

# 2. API anahtarını alıp Gemini istemcisini (client) başlatıyoruz
api_key = os.getenv("GEMINI_API_KEY") #Düz bir yazı değişkeni
client = genai.Client(api_key=api_key)

def ozetle(metin):
    if not metin: #direkt metin boş olursa
        return None

    try:
        # Yapay zekaya verilecek talimat (prompt)
        prompt = (
            "Aşağıdaki haberi incele ve Telegram bildirimi için sadece 1-2 cümlelik, "
            "anlaşılır ve net bir Türkçe özet çıkar. Ekstra açıklama veya selamlama yazma:\n\n"
            f"{metin}"
        )

        # Gemini modelini çağırıyoruz
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        return response.text.strip()

    except Exception as e: #kod hatası gibileri için
        print(f"AI Özet üretilirken hata oluştu: {e}")
        return None